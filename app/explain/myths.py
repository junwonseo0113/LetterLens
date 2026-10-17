"""Deterministic myth-busting lines attached to a ProgramResult.

These are plain facts about the rules, not LLM output -- the LLM never
decides which myth applies, it only ever receives these lines as material
to weave into the explanation (or they're shown as-is).
"""

from __future__ import annotations

from app.rules.engine import Profile, ProgramResult, Status

# NY State does not apply an asset/resource test to these programs.
RESOURCE_FREE_MSP_PROGRAMS = {"QMB", "QI", "MSP"}


def myth_busting_lines(result: ProgramResult, profile: Profile) -> list[str]:
    lines: list[str] = []

    if profile.savings > 0 and result.program in RESOURCE_FREE_MSP_PROGRAMS:
        lines.append("In New York, savings don't count for the Medicare Savings Program (MSP).")

    if profile.owns_home:
        lines.append("Your home doesn't count as a resource for any of these programs.")

    if (
        result.program == "Extra Help"
        and result.status == Status.LIKELY
        and "Automatic via" in result.rule_applied
    ):
        lines.append(
            "You can still get Extra Help (Low-Income Subsidy) through MSP (Medicare Savings "
            "Program), even if your income looks too high to qualify on its own."
        )

    return lines
