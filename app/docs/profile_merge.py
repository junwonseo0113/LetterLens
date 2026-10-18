"""Merge validated letter fields into a user's ProfileRecord.

Deterministic field-by-field logic, no LLM involved. A bank statement's
recurring deposit is only used as an income fallback when no documented
SSA benefit letter has already supplied ss_gross_monthly -- documented
numbers always win over estimated ones.
"""

from __future__ import annotations

from datetime import date

from app.models import ProfileRecord

from .schemas import LetterType


def _age_from_dob(dob: str, today: date | None = None) -> int:
    today = today or date.today()
    year, month, day = (int(p) for p in dob.split("-"))
    age = today.year - year
    if (today.month, today.day) < (month, day):
        age -= 1
    return age


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

        # An SSA letter's date of birth answers the "age" question itself
        # -- one less thing to ask about.
        if fields.get("date_of_birth"):
            profile.age = _age_from_dob(str(fields["date_of_birth"]))
            profile.set_provenance("age", letter_id)
            updated.append("age")

    elif letter_type == LetterType.HRA_RENEWAL_NOTICE:
        if fields.get("program") == "SNAP":
            profile.on_snap = True
            profile.set_provenance("on_snap", letter_id)
            updated.append("on_snap")
        if fields.get("household_size"):
            profile.household_size = fields["household_size"]
            profile.set_provenance("household_size", letter_id)
            updated.append("household_size")

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

    elif letter_type == LetterType.MEDICARE_NOTICE:
        # A Medicare notice addressed to them documents Medicare enrollment.
        profile.has_medicare = True
        profile.set_provenance("has_medicare", letter_id)
        updated.append("has_medicare")

    # medical_bill doesn't update Profile fields -- it drives the QMB
    # bill check (PROTECT) instead.

    return updated
