from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ReminderOut(BaseModel):
    id: int
    program: str
    deadline: date
    checklist: list[str]
    days_until_deadline: int
    overdue: bool
