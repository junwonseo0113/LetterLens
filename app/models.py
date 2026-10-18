"""Persisted state: a user's merged Profile and the letters that fed it.

No raw image bytes are ever stored here -- only OCR'd/extracted text and
structured fields, per the hard rule that uploaded images don't outlive
extraction.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class ProfileRecord(SQLModel, table=True):
    """Mirrors app.rules.engine.Profile, plus per-field provenance."""

    user_id: str = Field(primary_key=True)

    nyc_resident: bool = True
    age: int = 0
    married: bool = False
    # Only relevant when married=True: spouse income/limits combine only
    # if living together (verified against the 2026 NY MSP training deck).
    living_with_spouse: bool = True
    has_medicare: bool = False
    on_medicaid: bool = False
    on_ssi: bool = False
    disability: bool = False

    ss_gross_monthly: Optional[float] = None
    ss_gross_monthly_spouse: Optional[float] = None
    earned_income_monthly: Optional[float] = None
    earned_income_monthly_spouse: Optional[float] = None
    medigap_premium_monthly: float = 0.0
    medigap_premium_monthly_spouse: float = 0.0
    bank_deposit_monthly: Optional[float] = None

    savings: float = 0.0
    household_size: int = 1
    owns_home: bool = False
    # Documented current enrollment -- distinct from the rules engine's
    # computed "likely eligible for QMB", which is a separate question.
    on_qmb: bool = False

    # field_name -> letter_id that most recently set it
    field_sources: dict = Field(default_factory=dict, sa_column=Column(JSON))

    def set_provenance(self, field_name: str, letter_id: int) -> None:
        sources = dict(self.field_sources or {})
        sources[field_name] = letter_id
        self.field_sources = sources


class LetterRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    letter_type: str
    extracted_fields: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    letter_id: int
    program: str
    deadline: date
    checklist: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
