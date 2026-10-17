"""Document packet readiness.

Access NYC tells a user which documents a program needs. This checks
whether the user has actually shown us one yet -- deterministic keyword
matching against uploaded letter types, not an LLM call, since this is
"does a file exist" bookkeeping, not an eligibility decision.

Deliberately conservative: a false "satisfied" (telling someone they're
ready when they're not) is worse than a false "missing" (telling them to
bring a document they already have) -- missing just means bring it to the
interview anyway.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import LetterRecord, Reminder

from .schemas import PacketItem, PacketReadiness

# Checklist item text (lowercased, substring match) -> letter types that
# could plausibly satisfy it. hra_renewal_notice and medical_bill are
# intentionally absent -- neither proves income, residence, or identity.
SATISFYING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ssa_benefit_letter": ("income", "benefit", "social security", "ssa"),
    "bank_statement": ("income", "bank", "asset", "resource", "statement", "deposit"),
}


def _item_satisfied_by(item_text: str, letter_type: str) -> bool:
    keywords = SATISFYING_KEYWORDS.get(letter_type, ())
    item_lower = item_text.lower()
    return any(keyword in item_lower for keyword in keywords)


def check_packet_readiness(session: Session, reminder: Reminder) -> PacketReadiness:
    letters = session.exec(select(LetterRecord).where(LetterRecord.user_id == reminder.user_id)).all()

    items: list[PacketItem] = []
    for item_text in reminder.checklist:
        matched = next(
            (letter for letter in letters if _item_satisfied_by(item_text, letter.letter_type)),
            None,
        )
        items.append(
            PacketItem(
                item=item_text,
                satisfied=matched is not None,
                matched_letter_id=matched.id if matched else None,
                matched_letter_type=matched.letter_type if matched else None,
            )
        )

    satisfied_count = sum(1 for i in items if i.satisfied)
    return PacketReadiness(
        reminder_id=reminder.id,
        program=reminder.program,
        items=items,
        satisfied_count=satisfied_count,
        total_count=len(items),
        all_satisfied=len(items) > 0 and satisfied_count == len(items),
    )
