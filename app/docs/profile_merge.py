"""Merge validated letter fields into a user's ProfileRecord.

Deterministic field-by-field logic, no LLM involved. A bank statement's
recurring deposit is only used as an income fallback when no documented
SSA benefit letter has already supplied ss_gross_monthly -- documented
numbers always win over estimated ones.
"""

from __future__ import annotations

from app.models import ProfileRecord

from .schemas import LetterType


def merge_fields_into_profile(
    profile: ProfileRecord, letter_type: LetterType, fields: dict, letter_id: int
) -> list[str]:
    updated: list[str] = []

    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        profile.ss_gross_monthly = fields["gross_monthly_benefit"]
        profile.has_medicare = True
        profile.set_provenance("ss_gross_monthly", letter_id)
        profile.set_provenance("has_medicare", letter_id)
        updated += ["ss_gross_monthly", "has_medicare"]

    elif letter_type == LetterType.BANK_STATEMENT:
        profile.savings = fields["ending_balance"]
        profile.set_provenance("savings", letter_id)
        updated.append("savings")

        if profile.ss_gross_monthly is None:
            deposits = fields.get("recurring_deposits") or []
            if deposits:
                profile.bank_deposit_monthly = max(d["amount"] for d in deposits)
                profile.set_provenance("bank_deposit_monthly", letter_id)
                updated.append("bank_deposit_monthly")

    # hra_renewal_notice and medical_bill don't update numeric Profile
    # fields -- they drive Reminders and the QMB bill check (M5) instead.

    return updated
