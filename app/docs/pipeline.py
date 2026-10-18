"""Orchestrates the four document-pipeline steps for one uploaded letter.

OCR -> classify -> extract (validate, retry once) -> merge into Profile.
Raw image bytes are read into memory by the caller and never written to
disk or to the database -- this module never sees a file path.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlmodel import Session, select

from app.i18n import document_name_zh, is_zh
from app.keep.reminders import create_reminder, to_reminder_out
from app.models import LetterRecord, ProfileRecord, Reminder
from app.protect.bill_check import check_qmb_bill
from app.protect.oci_client import draft_dispute_letter
from app.trace import Trace, is_mock_mode, mock_suffix, trace_to_out

from . import oci_client
from .profile_merge import merge_fields_into_profile
from .schemas import SCHEMA_BY_TYPE, LetterType, LetterUploadResponse


log = logging.getLogger("letterlens.oci")


class ExtractionError(Exception):
    pass


class LetterReadError(Exception):
    """The letter couldn't be read. Nothing was saved; the user can retry."""

    message_en = "We couldn't read this letter. Nothing was saved. Please try again with a clear, flat photo."
    message_zh = "我们没能读懂这封信，没有保存任何内容。请拍一张清楚、平整的照片再试一次。"


def _get_or_create_profile(session: Session, user_id: str) -> ProfileRecord:
    profile = session.get(ProfileRecord, user_id)
    if profile is None:
        profile = ProfileRecord(user_id=user_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _action_items_and_deadline(
    letter_type: LetterType, fields: dict, language: str = "en"
) -> tuple[list[str], date | None]:
    zh = is_zh(language)
    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        if zh:
            return (["这封信请留好备查，目前不需要做什么。", "请保存好——社工可能会问您每月福利（扣除前）的金额。"], None)
        return (
            [
                "This letter is for your records. No action needed right now.",
                "Keep it -- caseworkers may ask for your gross monthly benefit amount.",
            ],
            None,
        )
    if letter_type == LetterType.BANK_STATEMENT:
        if zh:
            return (["不需要做什么。我们用它来估算您的收入。"], None)
        return (["No action needed. We used this to estimate your income."], None)
    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        deadline = fields.get("deadline")
        required = fields.get("required_documents", [])
        if zh:
            docs = "、".join(document_name_zh(d) for d in required) or "通知里列出的文件"
            return ([f"请在 {deadline} 之前提交：{docs}"], deadline)
        docs = ", ".join(required) or "the documents listed in the notice"
        return ([f"Submit by {deadline}: {docs}"], deadline)
    if letter_type == LetterType.MEDICAL_BILL:
        if zh:
            return (
                ["付款前，请先对照您的医疗保险 (Medicare) 承保范围检查这张账单。", "如果您有 QMB，您可能依法不用付这笔钱——请按“检查这张账单”。"],
                None,
            )
        return (
            [
                "Check this bill against your Medicare coverage before paying.",
                "If you have QMB, you may not legally owe this -- tap \"Check this bill.\"",
            ],
            None,
        )
    if zh:
        return (["如果有不清楚的地方，请拿这封信给社工看看。"], None)
    return (["Review this letter with a caseworker if anything is unclear."], None)


def process_letter(
    *, session: Session, image_bytes: bytes, filename: str, language: str, user_id: str
) -> LetterUploadResponse:
    trace = Trace()
    doc_service = f"OCI Document Understanding{mock_suffix()}"
    genai_service = f"OCI Generative AI{mock_suffix()}"

    try:
        letter_type, validated = _read_letter(trace, image_bytes, filename, doc_service, genai_service)
    except Exception as exc:
        # Real OCI failed (MOCK_MODE never gets here): fail loudly instead
        # of saving canned sample values into this person's profile.
        log.warning("Reading an uploaded letter failed; nothing saved", exc_info=True)
        raise LetterReadError(str(exc)) from exc

    fields = validated.model_dump(mode="json")
    action_items, deadline = _action_items_and_deadline(letter_type, fields, language)

    with trace.step("Explained it in your language", genai_service):
        explanation = oci_client.explain_letter(letter_type, fields, language)

    letter_record = LetterRecord(
        user_id=user_id,
        letter_type=letter_type.value,
        extracted_fields=fields,
        is_sample=is_mock_mode(),
        explanation=explanation,
        explanation_language=language,
    )
    return _save_and_respond(session, trace, letter_record, letter_type, validated, fields, action_items, deadline, language)


def _read_letter(trace: Trace, image_bytes: bytes, filename: str, doc_service: str, genai_service: str):
    with trace.step("Read the letter", doc_service):
        ocr = oci_client.ocr_document(image_bytes, filename)

    with trace.step("Identified the letter type", genai_service):
        letter_type = oci_client.classify_letter(ocr.raw_text)
    schema = SCHEMA_BY_TYPE[letter_type]

    with trace.step("Extracted the details", genai_service):
        raw_fields = oci_client.extract_fields(letter_type, ocr.raw_text, ocr.key_values)
        try:
            validated = schema.model_validate(raw_fields)
        except Exception:
            raw_fields = oci_client.extract_fields(
                letter_type, ocr.raw_text, ocr.key_values, retry_after_invalid=True
            )
            try:
                validated = schema.model_validate(raw_fields)
            except Exception as exc:
                raise ExtractionError(
                    f"Could not extract valid {letter_type.value} fields after retry"
                ) from exc
    return letter_type, validated


def _save_and_respond(
    session: Session,
    trace: Trace,
    letter_record: LetterRecord,
    letter_type: LetterType,
    validated,
    fields: dict,
    action_items: list[str],
    deadline,
    language: str,
) -> LetterUploadResponse:
    user_id = letter_record.user_id
    explanation = letter_record.explanation
    session.add(letter_record)
    session.commit()
    session.refresh(letter_record)

    profile = _get_or_create_profile(session, user_id)
    updated_fields = merge_fields_into_profile(profile, letter_type, fields, letter_record.id)
    session.add(profile)
    session.commit()

    reminder_out = None
    bill_check_out = None

    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        reminder_row = create_reminder(
            session,
            user_id=user_id,
            letter_id=letter_record.id,
            program=fields["program"],
            deadline=validated.deadline,
            checklist=fields.get("required_documents", []),
        )
        reminder_out = to_reminder_out(session, reminder_row)

    if letter_type == LetterType.MEDICAL_BILL:
        bill_check_out = _bill_check(profile, fields, language)

    return LetterUploadResponse(
        letter_id=letter_record.id,
        letter_type=letter_type,
        extracted_fields=fields,
        explanation=explanation,
        action_items=action_items,
        deadline=deadline,
        profile_fields_updated=updated_fields,
        reminder=reminder_out,
        bill_check=bill_check_out,
        trace=trace_to_out(trace),
        is_sample=bool(letter_record.is_sample),
        created_at=letter_record.created_at,
    )


def _bill_check(profile: ProfileRecord, fields: dict, language: str):
    result = check_qmb_bill(
        on_qmb=profile.on_qmb,
        provider=fields["provider"],
        is_medicare_claim=fields["is_medicare_claim"],
        line_items=fields.get("line_items", []),
    )
    if result.has_flagged:
        result.dispute_letter = draft_dispute_letter(fields["provider"], result.flagged_line_items, language)
    return result


class LetterNotFound(Exception):
    pass


def get_letter(session: Session, user_id: str, letter_id: int, language: str) -> LetterUploadResponse:
    """Reopen a saved letter -- only its owner can. Another user's letter
    is reported as not found, so ids can't be probed."""
    record = session.get(LetterRecord, letter_id)
    if record is None or record.user_id != user_id:
        raise LetterNotFound()

    letter_type = LetterType(record.letter_type)
    fields = record.extracted_fields or {}
    action_items, deadline = _action_items_and_deadline(letter_type, fields, language)

    explanation = record.explanation
    if not explanation or record.explanation_language != language:
        # Saved in another language (or saved before explanations were kept).
        explanation = oci_client.explain_letter(letter_type, fields, language)

    reminder = session.exec(select(Reminder).where(Reminder.letter_id == record.id)).first()
    bill_check = None
    if letter_type == LetterType.MEDICAL_BILL:
        bill_check = _bill_check(_get_or_create_profile(session, user_id), fields, language)

    return LetterUploadResponse(
        letter_id=record.id,
        letter_type=letter_type,
        extracted_fields=fields,
        explanation=explanation,
        action_items=action_items,
        deadline=deadline,
        profile_fields_updated=[],
        reminder=to_reminder_out(session, reminder) if reminder else None,
        bill_check=bill_check,
        # Saved before this flag existed = MOCK_MODE sample (real OCI never ran).
        is_sample=record.is_sample is not False,
        created_at=record.created_at,
    )
