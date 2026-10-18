"""Typed shapes for each letter type the OCR/GenAI pipeline can produce.

Pydantic validates whatever OCI GenAI extracts before it ever touches a
Profile or the rules engine -- invalid JSON gets one retry, then fails
loudly rather than silently corrupting a user's data.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.keep.schemas import ReminderOut
from app.protect.schemas import BillCheckResult
from app.trace import TraceStepOut


class LetterType(str, Enum):
    SSA_BENEFIT_LETTER = "ssa_benefit_letter"
    BANK_STATEMENT = "bank_statement"
    MEDICARE_NOTICE = "medicare_notice"
    HRA_RENEWAL_NOTICE = "hra_renewal_notice"
    MEDICAL_BILL = "medical_bill"
    OTHER = "other"


class SsaBenefitLetterFields(BaseModel):
    gross_monthly_benefit: float
    part_b_deduction: float
    net_payment: float
    effective_date: date
    # Used only to pre-fill applications; the user confirms both on review.
    recipient_name: str | None = None
    recipient_address: str | None = None
    # When present, lets the app answer the "age" question itself instead
    # of asking -- see app.docs.profile_merge.
    date_of_birth: date | None = None


class RecurringDeposit(BaseModel):
    description: str
    amount: float


class BankStatementFields(BaseModel):
    ending_balance: float
    recurring_deposits: list[RecurringDeposit] = Field(default_factory=list)
    # Optional: lets the KEEP packet checklist mark proof-of-rent /
    # proof-of-utilities / proof-of-medical-expenses as PARTIAL (a payment
    # is visible on the statement) rather than MISSING, even though a bank
    # statement alone isn't the actual bill/lease/receipt.
    monthly_rent: float | None = None
    utility_expenses: list[RecurringDeposit] = Field(default_factory=list)
    medical_expenses: list[RecurringDeposit] = Field(default_factory=list)


class HraRenewalNoticeFields(BaseModel):
    program: str
    deadline: date
    required_documents: list[str] = Field(default_factory=list)
    notice_date: date | None = None
    certification_end_date: date | None = None
    # When present, lets the app answer the "household_size" question
    # itself instead of asking -- see app.docs.profile_merge.
    household_size: int | None = None
    simplified_form_eligible: bool = False
    simplified_form_id: str | None = None
    interview_required: str | None = None


class LineItemCategory(str, Enum):
    DEDUCTIBLE = "deductible"
    COINSURANCE = "coinsurance"
    COPAY = "copay"
    OTHER = "other"


class BillLineItem(BaseModel):
    description: str
    # The amount the patient is billed for this line -- what PROTECT acts
    # on. billed/medicare_approved/medicare_paid are optional context only.
    amount: float
    category: LineItemCategory
    service_date: date | None = None
    billed: float | None = None
    medicare_approved: float | None = None
    medicare_paid: float | None = None


class MedicalBillFields(BaseModel):
    provider: str
    line_items: list[BillLineItem] = Field(default_factory=list)
    is_medicare_claim: bool


class OtherFields(BaseModel):
    summary: str = ""


SCHEMA_BY_TYPE: dict[LetterType, type[BaseModel]] = {
    LetterType.SSA_BENEFIT_LETTER: SsaBenefitLetterFields,
    LetterType.BANK_STATEMENT: BankStatementFields,
    LetterType.HRA_RENEWAL_NOTICE: HraRenewalNoticeFields,
    LetterType.MEDICAL_BILL: MedicalBillFields,
    LetterType.MEDICARE_NOTICE: OtherFields,
    LetterType.OTHER: OtherFields,
}


class LetterUploadResponse(BaseModel):
    letter_id: int
    letter_type: LetterType
    extracted_fields: dict
    explanation: str
    action_items: list[str]
    deadline: date | None = None
    profile_fields_updated: list[str]
    reminder: ReminderOut | None = None
    bill_check: BillCheckResult | None = None
    trace: list[TraceStepOut] = []
    # True when these values are MOCK_MODE sample data, not read from the photo.
    is_sample: bool = False
    created_at: datetime | None = None


class LetterSummary(BaseModel):
    id: int
    letter_type: LetterType
    created_at: datetime
    is_sample: bool = False
