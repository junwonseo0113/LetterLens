"""2026 NYC / NY State benefit program limits.

Verified 2026-10-17 against primary/authoritative sources (see each row's
source_url): HHS ASPE (poverty guidelines), SSA POMS HI 03020.055 / HI
03030.025 (Extra Help), CMS/RRB (Medicare Part B premium), USDA FNS FY26
COLA memo (SNAP asset limit), and NY Health Access -- the Evelyn Frank
Legal Resources Program's MSP fact sheet, cross-checked against the NY
State Office for the Aging's 2026 HIICAP notebook. One error was found and
fixed: FPL_INCREMENT_PER_ADDITIONAL_PERSON was $5,380, ASPE's actual 2026
figure is $5,680.

SNAP_GROSS_INCOME_PCT_FPL / SNAP_NET_INCOME_PCT_FPL could only be
corroborated via secondary sources (fns.usda.gov blocked automated
fetches) -- still marked VERIFY_BEFORE_DEMO. Everything else below was
confirmed directly; re-check all of it again closer to the actual demo
date since NY's MSP levels are reset annually each February.
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
    note="Verified 2026-10-17 directly against aspe.hhs.gov",
)
FPL_INCREMENT_PER_ADDITIONAL_PERSON = Limit(
    value=5680,
    year=2026,
    source_url="https://aspe.hhs.gov/poverty-guidelines",
    note="Verified 2026-10-17 directly against aspe.hhs.gov (was $5,380, corrected to $5,680)",
)

# --- Medicare Savings Program (MSP) - NY has no asset test ---
# NOTE: these are the raw/"Table" limits (138% FPL for QMB, 186% FPL for
# QI) BEFORE the $20 general income disregard. app/rules/income.py already
# subtracts that $20 from gross income before comparing to these limits --
# do not add $20 here, or the disregard will be double-counted. Some NY
# fact sheets instead publish "limit + $20" as a gross-income shortcut;
# that is a different, equally valid convention, just not this codebase's.
_MSP_VERIFIED_NOTE = (
    "Verified 2026-10-17 via nyhealthaccess.org/entry/99 (Evelyn Frank Legal "
    "Resources Program), cross-checked against the NYSOFA 2026 HIICAP notebook"
)
QMB_INCOME_LIMIT_SINGLE_MONTHLY = Limit(
    value=1836,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
    note=_MSP_VERIFIED_NOTE,
)
QMB_INCOME_LIMIT_COUPLE_MONTHLY = Limit(
    value=2489,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
    note=_MSP_VERIFIED_NOTE,
)
QI_INCOME_LIMIT_SINGLE_MONTHLY = Limit(
    value=2474,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
    note=_MSP_VERIFIED_NOTE,
)
QI_INCOME_LIMIT_COUPLE_MONTHLY = Limit(
    value=3355,
    year=2026,
    source_url="https://www.health.ny.gov/health_care/medicaid/program/medicaid_buy-in.htm",
    note=_MSP_VERIFIED_NOTE,
)

# --- Extra Help (Medicare Part D Low-Income Subsidy) ---
EXTRA_HELP_INCOME_LIMIT_SINGLE_ANNUAL = Limit(
    value=23940,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
    note="Verified 2026-10-17 via SSA POMS HI 03020.055 -- equals 150% of the 1-person FPL",
)
EXTRA_HELP_INCOME_LIMIT_COUPLE_ANNUAL = Limit(
    value=32460,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
    note="Verified 2026-10-17 via SSA POMS HI 03020.055 -- equals 150% of the 2-person FPL",
)
EXTRA_HELP_RESOURCE_LIMIT_SINGLE = Limit(
    value=18090,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
    note="Verified 2026-10-17 via SSA POMS HI 03030.025 (includes the $1,500/person burial allowance)",
)
EXTRA_HELP_RESOURCE_LIMIT_COUPLE = Limit(
    value=36100,
    year=2026,
    source_url="https://www.ssa.gov/medicare/part-d-extra-help",
    note="Verified 2026-10-17 via SSA POMS HI 03030.025 (includes the $1,500/person burial allowance)",
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
    note="Verified 2026-10-17 via USDA FNS FY26 COLA memo (household with a member 60+ or disabled)",
)

# --- Medicare ---
MEDICARE_PART_B_PREMIUM_MONTHLY = Limit(
    value=202.90,
    year=2026,
    source_url="https://www.medicare.gov/basics/costs/medicare-costs",
    note="Verified 2026-10-17 via CMS/RRB 2026 Medicare Part B premium announcement",
)
