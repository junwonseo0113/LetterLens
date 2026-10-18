"""Orchestrates the four document-pipeline steps for one uploaded letter.

OCR -> classify -> extract (validate, retry once) -> merge into Profile.
Raw image bytes are read into memory by the caller and never written to
disk or to the database -- this module never sees a file path.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.i18n import document_name_zh, is_zh
from app.keep.reminders import create_reminder, to_reminder_out
from app.models import LetterRecord, ProfileRecord
from app.protect.bill_check import check_qmb_bill
from app.protect.oci_client import draft_dispute_letter
from app.trace import Trace, mock_suffix, trace_to_out

from . import oci_client
from .profile_merge import merge_fields_into_profile
from .schemas import SCHEMA_BY_TYPE, LetterType, LetterUploadResponse


class ExtractionError(Exception):
    pass


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

    fields = validated.model_dump(mode="json")

    action_items, deadline = _action_items_and_deadline(letter_type, fields, language)

    with trace.step("Explained it in your language", genai_service):
        explanation = oci_client.explain_letter(letter_type, fields, language)

    letter_record = LetterRecord(user_id=user_id, letter_type=letter_type.value, extracted_fields=fields)
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
        bill_check_out = check_qmb_bill(
            on_qmb=profile.on_qmb,
            provider=fields["provider"],
            is_medicare_claim=fields["is_medicare_claim"],
            line_items=fields.get("line_items", []),
        )
        if bill_check_out.has_flagged:
            bill_check_out.dispute_letter = draft_dispute_letter(
                fields["provider"], bill_check_out.flagged_line_items, language
            )

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
    )
