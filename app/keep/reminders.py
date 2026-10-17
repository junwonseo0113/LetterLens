"""KEEP: renewal reminders with a countdown, created from hra_renewal_notice
letters. Pure bookkeeping -- no LLM, no eligibility decisions.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from app.models import Reminder

from .packet import check_packet_readiness
from .schemas import ReminderOut


def create_reminder(
    session: Session, *, user_id: str, letter_id: int, program: str, deadline: date, checklist: list[str]
) -> Reminder:
    reminder = Reminder(
        user_id=user_id, letter_id=letter_id, program=program, deadline=deadline, checklist=checklist
    )
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder


def to_reminder_out(session: Session, reminder: Reminder, today: date | None = None) -> ReminderOut:
    today = today or date.today()
    days_until = (reminder.deadline - today).days
    return ReminderOut(
        id=reminder.id,
        program=reminder.program,
        deadline=reminder.deadline,
        checklist=list(reminder.checklist),
        days_until_deadline=days_until,
        overdue=days_until < 0,
        packet=check_packet_readiness(session, reminder),
    )


def list_reminders(session: Session, user_id: str) -> list[ReminderOut]:
    reminders = session.exec(select(Reminder).where(Reminder.user_id == user_id)).all()
    reminders = sorted(reminders, key=lambda r: r.deadline)
    return [to_reminder_out(session, r) for r in reminders]
