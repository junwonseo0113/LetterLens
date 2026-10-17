"""Countable-income math shared by the MSP/Extra Help rules.

Mirrors the SSI-style income counting NY State uses for the Medicare
Savings Program: one $20 general disregard per household (unearned income
first, spillover to earned), then the $65 + half earned-income disregard,
then Medigap premiums are subtracted because they are a MSP-specific
deduction, not an SSI one.
"""

from . import limits

GENERAL_INCOME_DISREGARD = 20.0
EARNED_INCOME_FLAT_DISREGARD = 65.0


def countable_income_msp(
    *,
    unearned_self: float = 0.0,
    unearned_spouse: float = 0.0,
    earned_self: float = 0.0,
    earned_spouse: float = 0.0,
    medigap_self: float = 0.0,
    medigap_spouse: float = 0.0,
    married: bool = False,
) -> float:
    """Countable monthly income for MSP/Extra Help eligibility.

    Order of operations: combine household income -> apply the $20 general
    disregard to unearned income first (spilling into earned if unearned is
    too small) -> apply the $65-then-halve earned income disregard ->
    subtract Medigap premiums.
    """
    total_unearned = unearned_self + (unearned_spouse if married else 0.0)
    total_earned = earned_self + (earned_spouse if married else 0.0)

    if total_unearned >= GENERAL_INCOME_DISREGARD:
        unearned_after_disregard = total_unearned - GENERAL_INCOME_DISREGARD
        earned_after_general_disregard = total_earned
    else:
        remainder = GENERAL_INCOME_DISREGARD - total_unearned
        unearned_after_disregard = 0.0
        earned_after_general_disregard = max(0.0, total_earned - remainder)

    if earned_after_general_disregard > EARNED_INCOME_FLAT_DISREGARD:
        earned_countable = (earned_after_general_disregard - EARNED_INCOME_FLAT_DISREGARD) / 2
    else:
        earned_countable = 0.0

    total_medigap = medigap_self + (medigap_spouse if married else 0.0)

    countable = unearned_after_disregard + earned_countable - total_medigap
    return max(0.0, countable)


def estimate_gross_from_deposit(deposit_monthly: float) -> float:
    """When only a bank deposit is known, approximate gross SS benefit.

    Most seniors' deposits are net of the Part B premium, which Medicare
    withholds before deposit. Adding it back approximates the gross amount
    SSA actually reports -- this is a documented estimate, never treated as
    documented-confidence income.
    """
    return deposit_monthly + limits.MEDICARE_PART_B_PREMIUM_MONTHLY.value
