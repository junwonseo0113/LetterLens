from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class PacketItem(BaseModel):
    item: str
    satisfied: bool
    matched_letter_id: Optional[int] = None
    matched_letter_type: Optional[str] = None


class PacketReadiness(BaseModel):
    reminder_id: int
    program: str
    items: list[PacketItem]
    satisfied_count: int
    total_count: int
    all_satisfied: bool


class ReminderOut(BaseModel):
    id: int
    program: str
    deadline: date
    checklist: list[str]
    days_until_deadline: int
    overdue: bool
    packet: PacketReadiness
