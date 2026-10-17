"""Deterministic benefits rules engine.

This module decides eligibility. No LLM call ever enters this file -- the
LLM only extracts fields into a Profile and explains a ProgramResult after
the fact. Every result carries the numbers used, the rule applied, a
confidence label, and the standard decision-authority disclaimer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from . import limits
from .income import countable_income_msp, estimate_gross_from_deposit

FINAL_DECISION_DISCLAIMER = (
    "Final decision is made by NY State / HRA / SSA, not this app."
)
NEAR_LIMIT_PCT = 0.05


class Status(str, Enum):
    LIKELY = "likely"
    POSSIBLE = "possible"
    NOT_NOW = "not_now"
    ALREADY_ENROLLED = "already_enrolled"
    MISSING_INFO = "missing_info"


class Confidence(str, Enum):
    DOCUMENTED = "documented"
    ESTIMATED = "estimated"
    NEAR_LIMIT = "near_limit"


@dataclass
class Profile:
    nyc_resident: bool = True
    age: int = 0
    married: bool = False

    has_medicare: bool = False
    on_medicaid: bool = False
    on_ssi: bool = False
    disability: bool = False

    ss_gross_monthly: float | None = None
    ss_gross_monthly_spouse: float | None = None
    earned_income_monthly: float | None = None
    earned_income_monthly_spouse: float | None = None
    medigap_premium_monthly: float = 0.0
    medigap_premium_monthly_spouse: float = 0.0
    # Fallback when the only document seen is a bank statement.
    bank_deposit_monthly: float | None = None

    savings: float = 0.0
    household_size: int = 1
    owns_home: bool = False
    # Documented current enrollment -- distinct from this engine's computed
    # "likely eligible for QMB", used by the PROTECT illegal-billing check.
    on_qmb: bool = False


@dataclass
class ProgramResult:
    program: str
    status: Status
    monthly_value: float = 0.0
    annual_value: float = 0.0
    numbers_used: dict = field(default_factory=dict)
    rule_applied: str = ""
    confidence: Confidence = Confidence.DOCUMENTED
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    disclaimer: str = FINAL_DECISION_DISCLAIMER


def _near_limit(value: float, limit_value: float, pct: float = NEAR_LIMIT_PCT) -> bool:
    return limit_value * (1 - pct) <= value <= limit_value


def _gross_ss_income(profile: Profile) -> tuple[float, float, Confidence]:
    confidence = Confidence.DOCUMENTED
    ss_self = profile.ss_gross_monthly
    if ss_self is None and profile.bank_deposit_monthly is not None:
        ss_self = estimate_gross_from_deposit(profile.bank_deposit_monthly)
        confidence = Confidence.ESTIMATED
    ss_self = ss_self or 0.0
    ss_spouse = (profile.ss_gross_monthly_spouse or 0.0) if profile.married else 0.0
    return ss_self, ss_spouse, confidence


def _evaluate_msp(
    profile: Profile, countable: float, income_confidence: Confidence
) -> ProgramResult:
    if not profile.has_medicare:
        return ProgramResult(
            program="MSP",
            status=Status.NOT_NOW,
            rule_applied="Medicare Savings Program requires Medicare enrollment",
            missing_fields=["has_medicare"],
        )

    qmb_limit = (
        limits.QMB_INCOME_LIMIT_COUPLE_MONTHLY.value
        if profile.married
        else limits.QMB_INCOME_LIMIT_SINGLE_MONTHLY.value
    )
    qi_limit = (
        limits.QI_INCOME_LIMIT_COUPLE_MONTHLY.value
        if profile.married
        else limits.QI_INCOME_LIMIT_SINGLE_MONTHLY.value
    )
    household = "couple" if profile.married else "single"
    numbers_used = {
        "countable_income_monthly": round(countable, 2),
        "qmb_limit_monthly": qmb_limit,
        "qi_limit_monthly": qi_limit,
    }

    if countable <= qmb_limit:
        program, status = "QMB", Status.LIKELY
        rule = (
            f"Countable income ${countable:,.2f}/mo <= QMB limit "
            f"${qmb_limit:,.2f}/mo ({household}); NY MSP has no asset test"
        )
        confidence = (
            Confidence.NEAR_LIMIT
            if _near_limit(countable, qmb_limit)
            else income_confidence
        )
    elif countable <= qi_limit:
        program, status = "QI", Status.LIKELY
        rule = (
            f"Countable income ${countable:,.2f}/mo <= QI limit "
            f"${qi_limit:,.2f}/mo ({household}); NY MSP has no asset test"
        )
        confidence = (
            Confidence.NEAR_LIMIT
            if _near_limit(countable, qi_limit)
            else income_confidence
        )
    else:
        program, status = "MSP", Status.NOT_NOW
        gap = countable - qi_limit
        rule = (
            f"Countable income ${countable:,.2f}/mo exceeds QI limit "
            f"${qi_limit:,.2f}/mo ({household}) by ${gap:,.2f}/mo; "
            "income would need to drop by that amount to qualify"
        )
        confidence = income_confidence

    result = ProgramResult(
        program=program,
        status=status,
        monthly_value=limits.MEDICARE_PART_B_PREMIUM_MONTHLY.value if status == Status.LIKELY else 0.0,
        annual_value=(limits.MEDICARE_PART_B_PREMIUM_MONTHLY.value * 12) if status == Status.LIKELY else 0.0,
        numbers_used=numbers_used,
        rule_applied=rule,
        confidence=confidence,
    )
    if result.confidence == Confidence.NEAR_LIMIT:
        result.warnings.append(
            "Income is within 5% of the limit -- we recommend applying anyway."
        )
    return result


def _evaluate_extra_help(
    profile: Profile, msp: ProgramResult, countable: float, income_confidence: Confidence
) -> ProgramResult:
    if profile.on_medicaid or profile.on_ssi:
        return ProgramResult(
            program="Extra Help",
            status=Status.ALREADY_ENROLLED,
            rule_applied="Automatic via Medicaid/SSI enrollment",
        )

    if not profile.has_medicare:
        return ProgramResult(
            program="Extra Help",
            status=Status.NOT_NOW,
            rule_applied="Extra Help (Medicare Part D Low-Income Subsidy) requires Medicare",
            missing_fields=["has_medicare"],
        )

    if msp.status == Status.LIKELY:
        return ProgramResult(
            program="Extra Help",
            status=Status.LIKELY,
            rule_applied=f"Automatic via {msp.program} (Medicare Savings Program) enrollment",
            numbers_used=msp.numbers_used,
            confidence=msp.confidence,
            warnings=list(msp.warnings),
        )

    income_limit = (
        limits.EXTRA_HELP_INCOME_LIMIT_COUPLE_ANNUAL.value
        if profile.married
        else limits.EXTRA_HELP_INCOME_LIMIT_SINGLE_ANNUAL.value
    )
    resource_limit = (
        limits.EXTRA_HELP_RESOURCE_LIMIT_COUPLE.value
        if profile.married
        else limits.EXTRA_HELP_RESOURCE_LIMIT_SINGLE.value
    )
    annual_income = countable * 12
    numbers_used = {
        "annual_countable_income": round(annual_income, 2),
        "income_limit_annual": income_limit,
        "savings": profile.savings,
        "resource_limit": resource_limit,
    }
    if annual_income <= income_limit and profile.savings <= resource_limit:
        status = Status.LIKELY
        rule = (
            f"Annual countable income ${annual_income:,.2f} <= limit ${income_limit:,.2f} "
            f"and savings ${profile.savings:,.2f} <= resource limit ${resource_limit:,.2f}"
        )
    else:
        status = Status.NOT_NOW
        rule = (
            f"Annual countable income ${annual_income:,.2f} vs limit ${income_limit:,.2f}, "
            f"savings ${profile.savings:,.2f} vs resource limit ${resource_limit:,.2f}"
        )
    return ProgramResult(
        program="Extra Help",
        status=status,
        numbers_used=numbers_used,
        rule_applied=rule,
        confidence=income_confidence,
    )


def _evaluate_snap(
    profile: Profile, gross_self: float, gross_spouse: float, countable: float, income_confidence: Confidence
) -> ProgramResult:
    household_size = max(profile.household_size, 2 if profile.married else 1)
    fpl_annual = limits.FPL_100_SINGLE_ANNUAL.value + limits.FPL_INCREMENT_PER_ADDITIONAL_PERSON.value * (
        household_size - 1
    )
    fpl_100_monthly = fpl_annual / 12
    fpl_200_monthly = fpl_100_monthly * 2

    household_gross_monthly = gross_self + gross_spouse + (
        (profile.earned_income_monthly or 0.0)
        + ((profile.earned_income_monthly_spouse or 0.0) if profile.married else 0.0)
    )

    numbers_used = {
        "household_gross_monthly_income": round(household_gross_monthly, 2),
        "fpl_200_monthly": round(fpl_200_monthly, 2),
        "fpl_100_monthly": round(fpl_100_monthly, 2),
        "savings": profile.savings,
        "asset_limit": limits.SNAP_ASSET_LIMIT.value,
    }

    if household_gross_monthly <= fpl_200_monthly:
        status = Status.LIKELY
        rule = (
            f"Household gross income ${household_gross_monthly:,.2f}/mo <= 200% FPL "
            f"${fpl_200_monthly:,.2f}/mo; exact benefit amount set by HRA"
        )
    elif countable <= fpl_100_monthly and profile.savings <= limits.SNAP_ASSET_LIMIT.value:
        status = Status.POSSIBLE
        rule = (
            f"Household gross income ${household_gross_monthly:,.2f}/mo exceeds 200% FPL, "
            f"but net income ${countable:,.2f}/mo <= 100% FPL ${fpl_100_monthly:,.2f}/mo "
            f"and savings ${profile.savings:,.2f} <= asset limit ${limits.SNAP_ASSET_LIMIT.value:,.2f}"
        )
    else:
        status = Status.NOT_NOW
        rule = (
            f"Household gross income ${household_gross_monthly:,.2f}/mo exceeds 200% FPL "
            f"${fpl_200_monthly:,.2f}/mo and net/asset test also fails"
        )

    warnings = []
    if 60 <= profile.age <= 64 and not profile.disability and not profile.on_ssi:
        warnings.append(
            "SNAP work requirements may apply for adults age 60-64 unless disabled or exempt; confirm with HRA."
        )

    return ProgramResult(
        program="SNAP",
        status=status,
        numbers_used=numbers_used,
        rule_applied=rule,
        confidence=income_confidence,
        warnings=warnings,
    )


def evaluate(profile: Profile) -> list[ProgramResult]:
    if not profile.nyc_resident:
        return [
            ProgramResult(
                program=name,
                status=Status.NOT_NOW,
                rule_applied="Program requires NYC / NY State residency",
            )
            for name in ("MSP", "Extra Help", "SNAP")
        ]

    ss_self, ss_spouse, income_confidence = _gross_ss_income(profile)
    earned_self = profile.earned_income_monthly or 0.0
    earned_spouse = (profile.earned_income_monthly_spouse or 0.0) if profile.married else 0.0

    countable = countable_income_msp(
        unearned_self=ss_self,
        unearned_spouse=ss_spouse,
        earned_self=earned_self,
        earned_spouse=earned_spouse,
        medigap_self=profile.medigap_premium_monthly,
        medigap_spouse=profile.medigap_premium_monthly_spouse,
        married=profile.married,
    )

    msp = _evaluate_msp(profile, countable, income_confidence)
    extra_help = _evaluate_extra_help(profile, msp, countable, income_confidence)
    snap = _evaluate_snap(profile, ss_self, ss_spouse, countable, income_confidence)

    return [msp, extra_help, snap]
