"""OCI Document Understanding + GenAI calls, with an offline MOCK_MODE.

MOCK_MODE=true is the default and the only path exercised by the test
suite -- zero network calls, fully deterministic. When MOCK_MODE=false,
every call below attempts real OCI first; mock is only ever reached as a
fallback if that fails (see app.trace.call_with_fallback), and that
fallback is recorded on the request's trace so the UI can show it was
used, not hide it. The real-mode functions follow the OCI Python SDK's
documented shapes but are unverified against a live tenancy -- treat
them as a skeleton to wire up with real OCI credentials, not a tested
path.

The LLM is only ever asked to classify, extract, or explain -- never to
decide eligibility. See app/rules/engine.py for the decision logic.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from app.i18n import document_name_zh
from app.number_guard import assert_numbers_preserved
from app.oci_genai import genai_chat, oci_config
from app.trace import call_with_fallback

from .schemas import SCHEMA_BY_TYPE, LetterType


@dataclass
class OcrResult:
    raw_text: str
    key_values: dict


# ---------------------------------------------------------------------------
# Mock mode: deterministic canned responses so the demo works offline.
# ---------------------------------------------------------------------------

_MOCK_TEXT_BY_FILENAME_KEYWORD = {
    "ssa": (
        "Social Security Administration\n"
        "Chen, Yu-lan\n"
        "123 Northern Blvd, Apt 4B, Flushing, NY 11354\n"
        "Your monthly benefit amount is $1,700.00.\n"
        "Medicare Part B premium deduction: $202.90.\n"
        "Your net payment is $1,497.10.\n"
        "This change is effective 2026-01-01."
    ),
    "bank": (
        "Chase Checking Statement\n"
        "Ending balance: $40,000.00\n"
        "Recurring deposit: SSA TREAS 310 $1,700.00"
    ),
    "hra": (
        "HRA Human Resources Administration\n"
        "SNAP Recertification Notice\n"
        "Your SNAP case must be recertified by 2026-11-15.\n"
        "Please submit: proof of income, proof of residence, ID."
    ),
    "bill": (
        "Queens General Medical Billing\n"
        "Provider: Queens General Hospital\n"
        "Line item: Annual wellness visit copay $20.00 (copay)\n"
        "This is a Medicare claim."
    ),
}


def _mock_ocr(filename: str) -> OcrResult:
    key = filename.lower()
    for keyword, text in _MOCK_TEXT_BY_FILENAME_KEYWORD.items():
        if keyword in key:
            return OcrResult(raw_text=text, key_values={})
    return OcrResult(raw_text="(unrecognized sample document)", key_values={})


def _mock_classify(raw_text: str) -> LetterType:
    text = raw_text.lower()
    if "social security administration" in text or "benefit amount" in text:
        return LetterType.SSA_BENEFIT_LETTER
    if "ending balance" in text:
        return LetterType.BANK_STATEMENT
    if "recertif" in text or "snap" in text:
        return LetterType.HRA_RENEWAL_NOTICE
    if "medicare claim" in text or "provider:" in text:
        return LetterType.MEDICAL_BILL
    if "medicare" in text and "notice" in text:
        return LetterType.MEDICARE_NOTICE
    return LetterType.OTHER


def _mock_extract(letter_type: LetterType, raw_text: str) -> dict:
    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        return {
            "gross_monthly_benefit": 1700.00,
            "part_b_deduction": 202.90,
            "net_payment": 1497.10,
            "effective_date": "2026-01-01",
            "recipient_name": "Chen, Yu-lan",
            "recipient_address": "123 Northern Blvd, Apt 4B, Flushing, NY 11354",
        }
    if letter_type == LetterType.BANK_STATEMENT:
        return {
            "ending_balance": 40000.00,
            "recurring_deposits": [{"description": "SSA TREAS 310", "amount": 1700.00}],
        }
    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        return {
            "program": "SNAP",
            "deadline": "2026-11-15",
            "required_documents": ["proof of income", "proof of residence", "ID"],
        }
    if letter_type == LetterType.MEDICAL_BILL:
        return {
            "provider": "Queens General Hospital",
            "line_items": [
                {"description": "Annual wellness visit copay", "amount": 20.00, "category": "copay"}
            ],
            "is_medicare_claim": True,
        }
    return {"summary": raw_text[:200]}


def _mock_explain_zh(letter_type: LetterType, fields: dict) -> str:
    # Hand-written Chinese templates for the offline demo; every number is
    # copied from the extracted fields, never retyped.
    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        return (
            f"社会安全局 (Social Security) 每月给您 ${fields['gross_monthly_benefit']:,.2f}。"
            f"其中 ${fields['part_b_deduction']:,.2f} 被扣去交医疗保险 B 部分 (Medicare Part B) 的保费。"
            f"从 {fields['effective_date']} 起，您实际到账 ${fields['net_payment']:,.2f}。"
        )
    if letter_type == LetterType.BANK_STATEMENT:
        return (
            f"您的账户余额是 ${fields['ending_balance']:,.2f}。"
            "在纽约州，这些存款不会影响您申请医疗保险储蓄计划 (Medicare Savings Program, MSP)。"
        )
    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        docs = "、".join(document_name_zh(d) for d in fields.get("required_documents", []))
        return f"您的 {fields['program']} 福利需要在 {fields['deadline']} 之前续期。请提交：{docs}。"
    if letter_type == LetterType.MEDICAL_BILL:
        return (
            f"{fields['provider']} 给您寄来了一张账单。"
            "如果这是医疗保险 (Medicare) 的收费，而您有 QMB，您可能依法不用付这笔钱。"
        )
    return "这封信的类型我们还不认识。请拿给社工看看。"


def _mock_explain(letter_type: LetterType, fields: dict, language: str) -> str:
    if language.lower() in ("zh", "chinese"):
        return _mock_explain_zh(letter_type, fields)
    note = (
        ""
        if language.lower() in ("en", "english")
        else f" [MOCK_MODE: shown in English, not translated to {language}]"
    )
    if letter_type == LetterType.SSA_BENEFIT_LETTER:
        return (
            f"Your Social Security gives you ${fields['gross_monthly_benefit']:,.2f} a month. "
            f"Medicare takes ${fields['part_b_deduction']:,.2f} for Part B. "
            f"You get ${fields['net_payment']:,.2f} deposited, starting {fields['effective_date']}."
            + note
        )
    if letter_type == LetterType.BANK_STATEMENT:
        return (
            f"Your account balance is ${fields['ending_balance']:,.2f}. "
            "In New York, savings like this don't count for the Medicare Savings Program (MSP)."
            + note
        )
    if letter_type == LetterType.HRA_RENEWAL_NOTICE:
        docs = ", ".join(fields.get("required_documents", []))
        return (
            f"Your {fields['program']} benefits need to be renewed by {fields['deadline']}. "
            f"Please send: {docs}."
            + note
        )
    if letter_type == LetterType.MEDICAL_BILL:
        return (
            f"{fields['provider']} sent you a bill. "
            "If this is a Medicare charge and you have QMB, you may not legally owe it -- "
            "check the Protect tab."
            + note
        )
    return "This letter doesn't match a known type yet. Please show it to a caseworker." + note


# ---------------------------------------------------------------------------
# Real mode: OCI Document Understanding + Generative AI (untested skeleton).
# ---------------------------------------------------------------------------


def _real_ocr(image_bytes: bytes) -> OcrResult:
    import base64

    import oci
    from oci.ai_document.models import (
        AnalyzeDocumentDetails,
        DocumentKeyValueExtractionFeature,
        DocumentTextExtractionFeature,
        InlineDocumentDetails,
    )

    config = oci_config()
    client = oci.ai_document.AIServiceDocumentClient(config)
    details = AnalyzeDocumentDetails(
        document=InlineDocumentDetails(data=base64.b64encode(image_bytes).decode("utf-8")),
        compartment_id=os.environ["OCI_COMPARTMENT_ID"],
        features=[DocumentTextExtractionFeature(), DocumentKeyValueExtractionFeature()],
    )
    response = client.analyze_document(analyze_document_details=details)
    pages = response.data.pages or []
    raw_text = "\n".join(line.text for page in pages for line in (page.lines or []))
    key_values = {
        field.field_label.name: field.field_value.value
        for page in pages
        for field in (page.document_fields or [])
        if field.field_label and field.field_value
    }
    return OcrResult(raw_text=raw_text, key_values=key_values)


def _real_classify(raw_text: str) -> LetterType:
    prompt = (
        "Classify this letter into exactly one label: ssa_benefit_letter, "
        "bank_statement, medicare_notice, hra_renewal_notice, medical_bill, other. "
        "Reply with only the label.\n\nLetter text:\n" + raw_text
    )
    label = genai_chat(prompt).strip().lower()
    try:
        return LetterType(label)
    except ValueError:
        return LetterType.OTHER


def _real_extract(letter_type: LetterType, raw_text: str, key_values: dict, retry_after_invalid: bool) -> dict:
    schema = SCHEMA_BY_TYPE[letter_type]
    instruction = (
        "Your previous answer was not valid JSON for this schema -- reply with ONLY corrected JSON. "
        if retry_after_invalid
        else ""
    )
    prompt = (
        f"{instruction}Extract fields as JSON only, matching this schema: "
        f"{schema.model_json_schema()}. Do not invent values not present in the text. "
        f"Letter text:\n{raw_text}\n\nKey-values already extracted: {key_values}"
    )
    output = genai_chat(prompt)
    return json.loads(output)


def _real_explain(letter_type: LetterType, fields: dict, language: str) -> str:
    source_text = json.dumps(fields)
    prompt = (
        f"Explain this {letter_type.value} to someone reading at a 6th-grade level, in {language}, "
        "in 2-4 short sentences. Never change any number, date, dollar amount, or program name -- "
        f"keep official English program names in parentheses. Data: {source_text}"
    )
    output = genai_chat(prompt)
    assert_numbers_preserved(output, source_text)
    return output


# ---------------------------------------------------------------------------
# Public dispatch -- callers never branch on MOCK_MODE themselves. Real OCI
# is attempted whenever MOCK_MODE=false; mock is only ever reached as the
# deliberate default (MOCK_MODE=true) or as a fallback when real fails.
# ---------------------------------------------------------------------------


def ocr_document(image_bytes: bytes, filename: str) -> OcrResult:
    """OCI Document Understanding: OCR + key-value extraction."""
    return call_with_fallback(lambda: _real_ocr(image_bytes), lambda: _mock_ocr(filename))


def classify_letter(raw_text: str) -> LetterType:
    """OCI GenAI: classify the letter type from its OCR'd text."""
    return call_with_fallback(lambda: _real_classify(raw_text), lambda: _mock_classify(raw_text))


def extract_fields(
    letter_type: LetterType, raw_text: str, key_values: dict, retry_after_invalid: bool = False
) -> dict:
    """OCI GenAI: extract typed fields for the given letter type."""
    return call_with_fallback(
        lambda: _real_extract(letter_type, raw_text, key_values, retry_after_invalid),
        lambda: _mock_extract(letter_type, raw_text),
    )


def explain_letter(letter_type: LetterType, fields: dict, language: str) -> str:
    """OCI GenAI: plain-language explanation of this letter in the user's language."""
    return call_with_fallback(
        lambda: _real_explain(letter_type, fields, language),
        lambda: _mock_explain(letter_type, fields, language),
    )
