"""Orchestrates the four document-pipeline steps for one uploaded letter.

OCR -> classify -> extract (validate, retry once) -> merge into Profile.
Raw image bytes are read into memory by the caller and never written to
disk or to the database -- this module never sees a file path.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models import LetterRecord, ProfileRecord

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


def _action_items_and_deadline(letter_type: LetterType, fields: dict) -> tuple[list[str], date | None]:
    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        return (
            [
                "This letter is for your records. No action needed right now.",
                "Keep it -- caseworkers may ask for your gross monthly benefit amount.",
            ],
            None,
        )
    if letter_type == LetterType.BANK_STATEMENT:
        return (["No action needed. We used this to estimate your income."], None)
    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        docs = ", ".join(fields.get("required_documents", [])) or "the documents listed in the notice"
        deadline = fields.get("deadline")
        return ([f"Submit by {deadline}: {docs}"], deadline)
    if letter_type == LetterType.MEDICAL_BILL:
        return (
            [
                "Check this bill against your Medicare coverage before paying.",
                "If you have QMB, you may not legally owe this -- see the Protect tab.",
            ],
            None,
        )
    return (["Review this letter with a caseworker if anything is unclear."], None)


def process_letter(
    *, session: Session, image_bytes: bytes, filename: str, language: str, user_id: str
) -> LetterUploadResponse:
    ocr = oci_client.ocr_document(image_bytes, filename)
    letter_type = oci_client.classify_letter(ocr.raw_text)
    schema = SCHEMA_BY_TYPE[letter_type]

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

    action_items, deadline = _action_items_and_deadline(letter_type, fields)
    explanation = oci_client.explain_letter(letter_type, fields, language)

    letter_record = LetterRecord(user_id=user_id, letter_type=letter_type.value, extracted_fields=fields)
    session.add(letter_record)
    session.commit()
    session.refresh(letter_record)

    profile = _get_or_create_profile(session, user_id)
    updated_fields = merge_fields_into_profile(profile, letter_type, fields, letter_record.id)
    session.add(profile)
    session.commit()

    return LetterUploadResponse(
        letter_id=letter_record.id,
        letter_type=letter_type,
        extracted_fields=fields,
        explanation=explanation,
        action_items=action_items,
        deadline=deadline,
        profile_fields_updated=updated_fields,
    )
