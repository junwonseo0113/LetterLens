"""Bridges the persisted ProfileRecord to the pure rules engine + explain
layer. Nothing here decides eligibility or writes explanations -- it only
converts the storage shape and calls app.rules.engine.evaluate /
app.explain.explain_results.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session

from app.explain import ExplainedProgramResult, explain_results
from app.models import ProfileRecord
from app.rules.engine import Profile, evaluate
from app.trace import Trace, mock_suffix, trace_to_out, TraceStepOut


def profile_record_to_profile(record: ProfileRecord) -> Profile:
    return Profile(
        nyc_resident=record.nyc_resident,
        age=record.age,
        married=record.married,
        living_with_spouse=record.living_with_spouse,
        has_medicare=record.has_medicare,
        on_medicaid=record.on_medicaid,
        on_ssi=record.on_ssi,
        disability=record.disability,
        ss_gross_monthly=record.ss_gross_monthly,
        ss_gross_monthly_spouse=record.ss_gross_monthly_spouse,
        earned_income_monthly=record.earned_income_monthly,
        earned_income_monthly_spouse=record.earned_income_monthly_spouse,
        medigap_premium_monthly=record.medigap_premium_monthly,
        medigap_premium_monthly_spouse=record.medigap_premium_monthly_spouse,
        bank_deposit_monthly=record.bank_deposit_monthly,
        savings=record.savings,
        household_size=record.household_size,
        owns_home=record.owns_home,
        on_qmb=record.on_qmb,
    )


@dataclass
class BenefitsResult:
    results: list[ExplainedProgramResult]
    trace: list[TraceStepOut]


def get_benefits(session: Session, user_id: str, language: str) -> BenefitsResult:
    trace = Trace()
    record = session.get(ProfileRecord, user_id)
    profile = profile_record_to_profile(record) if record else Profile()

    with trace.step("Checked eligibility", "Rules engine (no AI)"):
        results = evaluate(profile)

    with trace.step("Explained each result", f"OCI Generative AI{mock_suffix()}"):
        explained = explain_results(results, profile, language)

    return BenefitsResult(results=explained, trace=trace_to_out(trace))
