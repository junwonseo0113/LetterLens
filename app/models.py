"""Persisted state: a user's merged Profile and the letters that fed it.

No raw image bytes are ever stored here -- only OCR'd/extracted text and
structured fields, per the hard rule that uploaded images don't outlive
extraction.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint


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
    # Documented current SNAP enrollment (an HRA recertification notice
    # was uploaded) -- see app.rules.engine.Profile.on_snap.
    on_snap: bool = False
    # Income of other household members (not self/spouse); SNAP only.
    other_household_income_monthly: Optional[float] = None

    # field_name -> where the value came from: a letter id (int), "user"
    # (answered a question) or "application" (answered in the application).
    # A field with no entry here is UNKNOWN, whatever its default value is.
    field_sources: dict = Field(default_factory=dict, sa_column=Column(JSON))

    def set_provenance(self, field_name: str, source: int | str) -> None:
        sources = dict(self.field_sources or {})
        sources[field_name] = source
        self.field_sources = sources

    def is_known(self, field_name: str) -> bool:
        return field_name in (self.field_sources or {})


class LetterRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    letter_type: str
    extracted_fields: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # True when the values came from MOCK_MODE's canned sample data rather
    # than reading the uploaded photo. Shown as "Sample" everywhere.
    is_sample: Optional[bool] = None
    # The explanation shown at upload, so the letter can be reopened later.
    explanation: Optional[str] = None
    explanation_language: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    letter_id: int
    program: str
    deadline: date
    checklist: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OtpChallenge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(index=True)
    code: str
    expires_at: datetime
    attempts: int = 0
    used: bool = False


class AuthSession(SQLModel, table=True):
    token: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    phone: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApplicationRecord(SQLModel, table=True):
    """A benefits application the app fills in and the user signs.

    status: draft -> submitted | needs_review; a caseworker moves
    needs_review -> submitted | info_requested; the user can resubmit
    from info_requested. Submission is simulated -- no agency API exists
    -- and only ever happens after the user's signature and explicit yes.
    """

    # One application per program per user; also stops two concurrent
    # "start" requests from creating duplicates.
    __table_args__ = (UniqueConstraint("user_id", "program"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    program: str
    status: str = "draft"

    # field key -> {"value": str | None, "source": str | None}
    fields: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # Document keys the user photographed in-app. The photos themselves
    # are discarded on upload, same rule as letters.
    documents_provided: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # Document keys a caseworker confirmed by seeing the original. A photo
    # alone is only "uploaded" -- it's discarded, so nobody can check it later.
    documents_verified: Optional[list] = Field(default=None, sa_column=Column(JSON))

    signature_png: Optional[str] = None  # data: URL from the signature pad
    signed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    confirmation_number: Optional[str] = None
    review_reason: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    reviewer_note: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
