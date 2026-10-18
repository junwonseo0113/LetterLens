"""Fill in, review, sign and submit a benefits application.

The app does the work, the user only says yes: fields are pre-filled from
uploaded letters and the verified phone number, the interview asks only
for what's still missing, and nothing leaves the "draft" state until the
user has signed and explicitly confirmed. If any required document is
missing, submission routes to a caseworker instead of going straight out.

Submission is simulated -- no NY State / HRA / SSA API accepts third-party
filings -- and every response says so (`simulated=True`).
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlmodel import Session, select

from app.keep.msp_checklist import MSP_DECISION_NOTICE_DAYS, MSP_DOCUMENTS
from app.models import ApplicationRecord, AuthSession, LetterRecord, ProfileRecord

from .normalize import normalize
from .templates import COVERS, TEMPLATES, field_spec

EDITABLE_STATUSES = {"draft", "info_requested"}


class ApplyError(Exception):
    def __init__(self, message_en: str, message_zh: str = "", status_code: int = 422):
        super().__init__(message_en)
        self.message_en = message_en
        self.message_zh = message_zh or message_en
        self.status_code = status_code


class FieldOut(BaseModel):
    key: str
    kind: str
    label_en: str
    label_zh: str
    question_en: str
    question_zh: str
    value: str | None
    # "you" | "sign_in" | a letter type like "ssa_benefit_letter"
    source: str | None


class DocumentOut(BaseModel):
    key: str
    label_en: str
    label_zh: str
    # "from_letter" | "photographed" | "signed" | "missing"
    status: str


class ApplicationOut(BaseModel):
    id: int
    program: str
    covers: list[str]
    status: str
    fields: list[FieldOut]
    next_question: str | None
    documents: list[DocumentOut]
    missing_documents: list[str]
    signed: bool
    submitted_at: datetime | None
    confirmation_number: str | None
    review_reason: list[str]
    reviewer_note: str | None
    decision_notice_days: int = MSP_DECISION_NOTICE_DAYS
    simulated: bool = True


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- pre-fill ----------------------------------------------------------------


def _latest_letter(session: Session, user_id: str, letter_type: str) -> LetterRecord | None:
    return session.exec(
        select(LetterRecord)
        .where(LetterRecord.user_id == user_id, LetterRecord.letter_type == letter_type)
        .order_by(LetterRecord.id.desc())
    ).first()


def _format_prefill(kind: str, value) -> str | None:
    if value is None or value == "":
        return None
    try:
        return normalize(kind, str(value))
    except ValueError:
        return None  # leave it for the interview to ask


def _prefill_value(session: Session, app: ApplicationRecord, phone: str, spec) -> tuple[str | None, str | None]:
    if spec.prefill is None:
        return None, None
    origin = spec.prefill[0]

    if origin == "sign_in":
        return _format_prefill(spec.kind, phone), "sign_in"

    if origin == "letter":
        _, letter_type, field_name = spec.prefill
        letter = _latest_letter(session, app.user_id, letter_type)
        if letter is None:
            return None, None
        return _format_prefill(spec.kind, letter.extracted_fields.get(field_name)), letter_type

    if origin == "profile":
        profile = session.get(ProfileRecord, app.user_id)
        if profile is None:
            return None, None
        field_name = spec.prefill[1]
        letter_id = (profile.field_sources or {}).get(field_name)
        letter = session.get(LetterRecord, letter_id) if letter_id else None
        if letter is None:
            return None, None  # only pre-fill documented numbers, never defaults
        return _format_prefill(spec.kind, getattr(profile, field_name)), letter.letter_type

    return None, None


def refresh_prefill(session: Session, app: ApplicationRecord, phone: str) -> None:
    """Fill any still-empty field from letters uploaded since the last look.
    Never overwrites something the user already answered."""
    fields = dict(app.fields or {})
    for spec in TEMPLATES[app.program]:
        current = fields.get(spec.key) or {}
        if current.get("value") is not None:
            continue
        value, source = _prefill_value(session, app, phone, spec)
        fields[spec.key] = {"value": value, "source": source if value is not None else None}
    app.fields = fields


# --- documents -----------------------------------------------------------------


def _uploaded_letter_types(session: Session, user_id: str) -> set[str]:
    letters = session.exec(select(LetterRecord).where(LetterRecord.user_id == user_id)).all()
    return {letter.letter_type for letter in letters}


def _documents(session: Session, app: ApplicationRecord) -> list[DocumentOut]:
    letter_types = _uploaded_letter_types(session, app.user_id)
    out = []
    for item in MSP_DOCUMENTS:
        if item["key"] == "signed_application":
            status = "signed" if app.signature_png else "missing"
        elif item["satisfied_by"] & letter_types:
            status = "from_letter"
        elif item["key"] in (app.documents_provided or []):
            status = "photographed"
        else:
            status = "missing"
        out.append(
            DocumentOut(key=item["key"], label_en=item["label_en"], label_zh=item["label_zh"], status=status)
        )
    return out


# --- read ------------------------------------------------------------------------


def to_out(session: Session, app: ApplicationRecord) -> ApplicationOut:
    fields = []
    for spec in TEMPLATES[app.program]:
        state = (app.fields or {}).get(spec.key) or {}
        fields.append(
            FieldOut(
                key=spec.key,
                kind=spec.kind,
                label_en=spec.label_en,
                label_zh=spec.label_zh,
                question_en=spec.question_en,
                question_zh=spec.question_zh,
                value=state.get("value"),
                source=state.get("source"),
            )
        )
    documents = _documents(session, app)
    return ApplicationOut(
        id=app.id,
        program=app.program,
        covers=COVERS[app.program],
        status=app.status,
        fields=fields,
        next_question=next((f.key for f in fields if f.value is None), None),
        documents=documents,
        # The signature comes with the submit itself, so it's never "missing" there.
        missing_documents=[d.key for d in documents if d.status == "missing" and d.key != "signed_application"],
        signed=bool(app.signature_png),
        submitted_at=app.submitted_at,
        confirmation_number=app.confirmation_number,
        review_reason=list(app.review_reason or []),
        reviewer_note=app.reviewer_note,
    )


def get_or_start(session: Session, auth: AuthSession, program: str) -> ApplicationRecord:
    if program not in TEMPLATES:
        raise ApplyError(f"No application form for {program} yet.", status_code=404)
    app = session.exec(
        select(ApplicationRecord)
        .where(ApplicationRecord.user_id == auth.user_id, ApplicationRecord.program == program)
        .order_by(ApplicationRecord.id.desc())
    ).first()
    if app is None:
        app = ApplicationRecord(user_id=auth.user_id, program=program)
    if app.status in EDITABLE_STATUSES:
        refresh_prefill(session, app, auth.phone)
    _save(session, app)
    return app


def get_owned(session: Session, auth: AuthSession, application_id: int) -> ApplicationRecord:
    app = session.get(ApplicationRecord, application_id)
    if app is None or app.user_id != auth.user_id:
        raise ApplyError("Application not found.", "找不到这份申请。", status_code=404)
    return app


def _save(session: Session, app: ApplicationRecord) -> None:
    app.updated_at = _utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)


def _require_editable(app: ApplicationRecord) -> None:
    if app.status not in EDITABLE_STATUSES:
        raise ApplyError(
            "This application was already sent and can't be changed.",
            "这份申请已经提交，无法修改。",
            status_code=409,
        )


# --- write -------------------------------------------------------------------------


def answer_field(session: Session, app: ApplicationRecord, key: str, raw: str) -> ApplicationRecord:
    _require_editable(app)
    spec = field_spec(app.program, key)
    if spec is None:
        raise ApplyError(f"Unknown field {key}.", status_code=404)
    try:
        value = normalize(spec.kind, raw)
    except ValueError as exc:
        raise ApplyError(getattr(exc, "message_en", str(exc)), getattr(exc, "message_zh", "")) from exc
    fields = dict(app.fields or {})
    fields[key] = {"value": value, "source": "you"}
    app.fields = fields
    _save(session, app)
    return app


def add_document(session: Session, app: ApplicationRecord, key: str) -> ApplicationRecord:
    _require_editable(app)
    if key == "signed_application" or key not in {item["key"] for item in MSP_DOCUMENTS}:
        raise ApplyError(f"Unknown document {key}.", status_code=404)
    provided = list(app.documents_provided or [])
    if key not in provided:
        provided.append(key)
    app.documents_provided = provided
    _save(session, app)
    return app


def _confirmation_number(program: str) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return f"{program}-" + "".join(secrets.choice(alphabet) for _ in range(8))


def submit(session: Session, app: ApplicationRecord, signature_png: str, confirmed: bool) -> ApplicationRecord:
    _require_editable(app)
    if not confirmed:
        raise ApplyError("Please confirm before sending.", "发送前请确认。")
    if not (signature_png or "").startswith("data:image/"):
        raise ApplyError("Please sign before sending.", "发送前请签名。")

    out = to_out(session, app)
    unanswered = [f.label_en for f in out.fields if f.value is None]
    if unanswered:
        raise ApplyError(
            "Some answers are still missing: " + ", ".join(unanswered),
            "还有问题没有回答：" + "、".join(f.label_zh for f in out.fields if f.value is None),
        )

    app.signature_png = signature_png
    app.signed_at = _utcnow()
    app.reviewer_note = None

    missing = out.missing_documents
    if missing:
        # Not enough documents to send on its own -- a person checks first.
        app.status = "needs_review"
        app.review_reason = missing
    else:
        app.status = "submitted"
        app.review_reason = []
        app.submitted_at = _utcnow()
        app.confirmation_number = _confirmation_number(app.program)
    _save(session, app)
    return app


# --- caseworker ----------------------------------------------------------------------


def review_queue(session: Session) -> list[ApplicationRecord]:
    return list(
        session.exec(
            select(ApplicationRecord)
            .where(ApplicationRecord.status == "needs_review")
            .order_by(ApplicationRecord.updated_at)
        ).all()
    )


def _require_in_review(session: Session, application_id: int) -> ApplicationRecord:
    app = session.get(ApplicationRecord, application_id)
    if app is None:
        raise ApplyError("Application not found.", status_code=404)
    if app.status != "needs_review":
        raise ApplyError("This application isn't waiting for review.", status_code=409)
    return app


def approve(session: Session, application_id: int, note: str | None) -> ApplicationRecord:
    app = _require_in_review(session, application_id)
    app.status = "submitted"
    app.reviewer_note = note or None
    app.submitted_at = _utcnow()
    app.confirmation_number = _confirmation_number(app.program)
    _save(session, app)
    return app


def request_info(session: Session, application_id: int, note: str) -> ApplicationRecord:
    if not (note or "").strip():
        raise ApplyError("Tell the applicant what's needed.")
    app = _require_in_review(session, application_id)
    app.status = "info_requested"
    app.reviewer_note = note.strip()
    _save(session, app)
    return app
