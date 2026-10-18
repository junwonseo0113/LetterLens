from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class PacketItem(BaseModel):
    item: str
    # Kept for backward compatibility: true for both "have" and "partial".
    satisfied: bool
    # "have" (a matching letter was uploaded) | "partial" (a bank statement
    # shows the payment, but not the actual bill/lease/receipt) | "missing"
    status: str = "missing"
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
