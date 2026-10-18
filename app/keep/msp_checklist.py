"""MSP application document checklist.

Sourced from the official DOH-4328 instructions and the Medicare Rights
Center's MSP application coversheet -- both read directly, not guessed.
Unlike app.keep.packet (which checks a checklist *extracted from* an HRA
renewal letter), this list is fixed: applying for MSP always needs the
same documents, there is no letter that states it.

Deliberately conservative about what counts as "already have," same
principle as app.keep.packet: a false "missing" just means bring the
document anyway; a false "already have" would send someone to an
interview unprepared. Most of these items genuinely can't be satisfied
by any of this app's four letter types (a benefit letter is not a copy
of the physical Medicare card, a bank statement is not a birth
certificate) -- that's reported honestly as "missing," not papered over.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import LetterRecord
from pydantic import BaseModel

MSP_DECISION_NOTICE_DAYS = 45

_ITEMS = [
    {
        "key": "signed_application",
        "label_en": "Signed MSP application (DOH-4328)",
        "label_ko": "서명된 MSP 신청서 (DOH-4328)",
        "satisfied_by": frozenset(),
    },
    {
        "key": "medicare_card",
        "label_en": "Medicare card, front and back",
        "label_ko": "메디케어 카드 앞뒤 사본 (Medicare card)",
        "satisfied_by": frozenset(),
    },
    {
        "key": "proof_of_identity_dob",
        "label_en": "Proof of identity / date of birth",
        "label_ko": "신분증 / 생년월일 증명 (Proof of Identity/Date of Birth)",
        "satisfied_by": frozenset(),
    },
    {
        "key": "proof_of_residence",
        "label_en": "Proof of residence, dated within 6 months",
        "label_ko": "거주 증명, 6개월 이내 발급 (Proof of Residence)",
        "satisfied_by": frozenset(),
    },
    {
        "key": "proof_of_income",
        "label_en": "Proof of income",
        "label_ko": "소득 증명 (Proof of Income)",
        "satisfied_by": frozenset({"ssa_benefit_letter", "bank_statement"}),
    },
    {
        "key": "social_security_card",
        "label_en": "Social Security card",
        "label_ko": "소셜시큐리티 카드 (Social Security card)",
        "satisfied_by": frozenset(),
    },
]


class MspChecklistItemOut(BaseModel):
    key: str
    label_en: str
    label_ko: str
    status: str  # "already_have" | "missing"


class MspChecklistOut(BaseModel):
    items: list[MspChecklistItemOut]
    decision_notice_days: int = MSP_DECISION_NOTICE_DAYS


def check_msp_checklist(session: Session, user_id: str) -> MspChecklistOut:
    letters = session.exec(select(LetterRecord).where(LetterRecord.user_id == user_id)).all()
    uploaded_types = {letter.letter_type for letter in letters}

    items = []
    for item in _ITEMS:
        has_match = bool(item["satisfied_by"] & uploaded_types)
        items.append(
            MspChecklistItemOut(
                key=item["key"],
                label_en=item["label_en"],
                label_ko=item["label_ko"],
                status="already_have" if has_match else "missing",
            )
        )
    return MspChecklistOut(items=items)
