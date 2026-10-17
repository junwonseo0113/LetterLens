"""2026 NYC / NY State benefit program limits.

VERIFY_BEFORE_DEMO: every figure below is this engine's best effort as of
2026-10-17. Re-check each one against the live SSA / NY State source linked
on its row before running the real demo -- these numbers change yearly and
the rules engine is only as trustworthy as this table.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limit:
    value: float
    year: int
    source_url: str
    note: str = "VERIFY_BEFORE_DEMO"


# --- Federal Poverty Level (used for SNAP) ---
FPL_100_SINGLE_ANNUAL = Limit(
    value=15960,
    year=2026,
    source_url="https://aspe.hhs.gov/poverty-guidelines",
)
FPL_INCREMENT_PER_ADDITIONAL_PERSON = Limit(
    value=5380,
    year=2026,
    source_url="https://aspe.hhs.gov/poverty-guidelines",
    note="VERIFY_BEFORE_DEMO - per-person add-on for household size > 1",
)

# --- Medicare Savings Program (MSP) - NY has no asset test ---
QMB_INCOME_LIMIT_SINGLE_MONTHLY = Limit(
    value=1836,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
)
QMB_INCOME_LIMIT_COUPLE_MONTHLY = Limit(
    value=2489,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
)
QI_INCOME_LIMIT_SINGLE_MONTHLY = Limit(
    value=2474,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
)
QI_INCOME_LIMIT_COUPLE_MONTHLY = Limit(
    value=3355,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
)

# --- Extra Help (Medicare Part D Low-Income Subsidy) ---
EXTRA_HELP_INCOME_LIMIT_SINGLE_ANNUAL = Limit(
    value=23940,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
)
EXTRA_HELP_INCOME_LIMIT_COUPLE_ANNUAL = Limit(
    value=32460,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
)
EXTRA_HELP_RESOURCE_LIMIT_SINGLE = Limit(
    value=18090,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
)
EXTRA_HELP_RESOURCE_LIMIT_COUPLE = Limit(
    value=36100,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
)

# --- SNAP (household with a member age 60+) ---
SNAP_GROSS_INCOME_PCT_FPL = Limit(
    value=200,
    year=2026,
    source_url="https://www.fns.usda.gov/snap/allotment/COLA",
    note="VERIFY_BEFORE_DEMO - percent of FPL, not a dollar limit",
)
SNAP_NET_INCOME_PCT_FPL = Limit(
    value=100,
    year=2026,
    source_url="https://www.fns.usda.gov/snap/allotment/COLA",
    note="VERIFY_BEFORE_DEMO - percent of FPL, not a dollar limit",
)
SNAP_ASSET_LIMIT = Limit(
    value=4500,
    year=2026,
    source_url="https://www.fns.usda.gov/snap/eligibility",
)

# --- Medicare ---
MEDICARE_PART_B_PREMIUM_MONTHLY = Limit(
    value=202.90,
    year=2026,
    source_url="https://www.medicare.gov/basics/costs/medicare-costs",
)
