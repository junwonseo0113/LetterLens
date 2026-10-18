"""Deterministic myth-busting lines attached to a ProgramResult.

These are plain facts about the rules, not LLM output -- the LLM never
decides which myth applies, it only ever receives these lines as material
to weave into the explanation (or they're shown as-is).
"""

from __future__ import annotations

from app.rules.engine import Profile, ProgramResult, Status

# NY State does not apply an asset/resource test to these programs.
RESOURCE_FREE_MSP_PROGRAMS = {"QMB", "QI", "MSP"}


_LINES = {
    "savings_msp": {
        "en": "In New York, savings don't count for the Medicare Savings Program (MSP).",
        "zh": "在纽约州，存款不会影响医疗保险储蓄计划 (Medicare Savings Program, MSP)。",
    },
    "home": {
        "en": "Your home doesn't count as a resource for any of these programs.",
        "zh": "您的房子不算作这些计划审查的资产。",
    },
    "extra_help_via_msp": {
        "en": (
            "You can still get Extra Help (Low-Income Subsidy) through MSP (Medicare Savings "
            "Program), even if your income looks too high to qualify on its own."
        ),
        "zh": (
            "即使您的收入看起来太高、单独申请不符合条件，您仍然可以通过 MSP（医疗保险储蓄计划）"
            "获得 Extra Help（低收入补助）。"
        ),
    },
}


def myth_busting_lines(result: ProgramResult, profile: Profile, language: str = "en") -> list[str]:
    lang = "zh" if language.lower() in ("zh", "chinese") else "en"
    lines: list[str] = []

    if profile.savings > 0 and result.program in RESOURCE_FREE_MSP_PROGRAMS:
        lines.append(_LINES["savings_msp"][lang])

    if profile.owns_home:
        lines.append(_LINES["home"][lang])

    if (
        result.program == "Extra Help"
        and result.status == Status.LIKELY
        and "Comes automatically once enrolled" in result.rule_applied
    ):
        lines.append(_LINES["extra_help_via_msp"][lang])

    return lines
