from __future__ import annotations

from pydantic import BaseModel


class FlaggedLineItem(BaseModel):
    description: str
    amount: float
    category: str
    reason: str


class DisputeLetter(BaseModel):
    english: str
    translated: str
    language: str


class BillCheckResult(BaseModel):
    provider: str
    is_medicare_claim: bool
    on_qmb: bool
    flagged_line_items: list[FlaggedLineItem] = []
    has_flagged: bool = False
    dispute_letter: DisputeLetter | None = None
