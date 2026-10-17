"""PROTECT: deterministic QMB illegal-billing check.

Federal law (42 U.S.C. 1396a(n)) bars providers from billing QMB members
for Medicare Part A/B deductibles, coinsurance, or copays on
Medicare-covered services. This module only flags matching line items --
it never submits a dispute and never decides eligibility; app.rules.engine
is the only place that happens.
"""

from __future__ import annotations

from .schemas import BillCheckResult, FlaggedLineItem

BILLABLE_TO_QMB_CATEGORIES = {"deductible", "coinsurance", "copay"}


def check_qmb_bill(
    *, on_qmb: bool, provider: str, is_medicare_claim: bool, line_items: list[dict]
) -> BillCheckResult:
    flagged: list[FlaggedLineItem] = []
    if on_qmb and is_medicare_claim:
        for item in line_items:
            if item["category"] in BILLABLE_TO_QMB_CATEGORIES:
                flagged.append(
                    FlaggedLineItem(
                        description=item["description"],
                        amount=item["amount"],
                        category=item["category"],
                        reason=(
                            "QMB members cannot be billed for Medicare cost-sharing "
                            f"({item['category']}) on a Medicare-covered service."
                        ),
                    )
                )

    return BillCheckResult(
        provider=provider,
        is_medicare_claim=is_medicare_claim,
        on_qmb=on_qmb,
        flagged_line_items=flagged,
        has_flagged=len(flagged) > 0,
    )
