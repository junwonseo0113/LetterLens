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
    PAY_STUB = "pay_stub"
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
    # When present, lets the app answer the "on_ssi" fact without asking.
    receives_ssi: bool | None = None


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


class HouseholdMember(BaseModel):
    name: str
    age: int | None = None
    relationship: str = "head_of_household"


class HraRenewalNoticeFields(BaseModel):
    program: str
    deadline: date
    required_documents: list[str] = Field(default_factory=list)
    notice_date: date | None = None
    certification_end_date: date | None = None
    # When present, lets the app answer the "household_size" question
    # itself instead of asking -- see app.docs.profile_merge.
    household_size: int | None = None
    # A named household-members list, when the notice lists one: if it has
    # exactly one person, that answers "married and living with spouse"
    # (= no) without ever asking or stating a marital status directly.
    household_members: list[HouseholdMember] | None = None
    # Which programs this case is already open for -- if listed and
    # Medicaid isn't among them, that answers "on Medicaid" (= no).
    programs_on_case: list[str] | None = None
    # Some notices state this outright (it's the eligibility condition for
    # the simplified senior/disabled form) -- when present, answers
    # "earned_income_monthly" (= 0) without asking or needing a pay stub.
    household_has_earned_income: bool | None = None
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


class PayStubFields(BaseModel):
    # Read but not kept (see app.privacy.SAVED_FIELDS), so optional here.
    employer: str | None = None
    # Gross pay for the stub's own period (weekly/biweekly/monthly) --
    # normalized to a monthly figure in app.docs.profile_merge, the same
    # way the rules engine expects ss_gross_monthly.
    gross_pay: float
    pay_period: str  # "weekly" | "biweekly" | "semimonthly" | "monthly"
    pay_date: date | None = None


class OtherFields(BaseModel):
    summary: str = ""


SCHEMA_BY_TYPE: dict[LetterType, type[BaseModel]] = {
    LetterType.SSA_BENEFIT_LETTER: SsaBenefitLetterFields,
    LetterType.BANK_STATEMENT: BankStatementFields,
    LetterType.HRA_RENEWAL_NOTICE: HraRenewalNoticeFields,
    LetterType.MEDICAL_BILL: MedicalBillFields,
    LetterType.PAY_STUB: PayStubFields,
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
    # Facts the user changed before saving.
    corrected_fields: list[str] = []


class LetterDraftOut(BaseModel):
    """What was read from a photo. Nothing is saved until the user confirms."""

    draft_token: str
    letter_type: LetterType
    # Facts that will be saved on confirm (the user can correct the editable ones).
    facts: dict
    # Personal identifiers found (e.g. name/address); saved only if the user opts in.
    identifiers: dict
    # field -> kind ("money" | "date" | "text" | "bool") for correctable facts.
    editable: dict
    explanation: str
    action_items: list[str]
    deadline: date | None = None
    bill_check: BillCheckResult | None = None
    is_sample: bool = False
    trace: list[TraceStepOut] = []


class ConfirmIn(BaseModel):
    draft_token: str
    # The user's version of the editable facts (and identifiers, if kept).
    facts: dict = {}
    save_identifiers: bool = False
    language: str = "en"


class LetterSummary(BaseModel):
    id: int
    letter_type: LetterType
    created_at: datetime
    is_sample: bool = False
