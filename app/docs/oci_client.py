"""OCI Document Understanding + GenAI calls, with an offline MOCK_MODE.

MOCK_MODE is the default and the only path exercised by the test suite --
the demo must run with no OCI credentials. Set MOCK_MODE=false (and the
OCI_* env vars) to use the real services. The real-mode functions follow
the OCI Python SDK's documented shapes but are unverified against a live
tenancy -- treat them as a skeleton to wire up with real OCI credentials,
not a tested path.

The LLM is only ever asked to classify, extract, or explain -- never to
decide eligibility. See app/rules/engine.py for the decision logic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .schemas import SCHEMA_BY_TYPE, LetterType

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")


def _mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() not in ("0", "false", "no")


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


def _mock_explain(letter_type: LetterType, fields: dict, language: str) -> str:
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


def _oci_config():
    import oci

    config_path = os.environ.get("OCI_CONFIG_PATH", "~/.oci/config")
    profile = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")
    return oci.config.from_file(file_location=config_path, profile_name=profile)


def _real_ocr(image_bytes: bytes) -> OcrResult:
    import base64

    import oci
    from oci.ai_document.models import (
        AnalyzeDocumentDetails,
        DocumentKeyValueExtractionFeature,
        DocumentTextExtractionFeature,
        InlineDocumentDetails,
    )

    config = _oci_config()
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


def _genai_chat(prompt: str) -> str:
    import oci
    from oci.generative_ai_inference.models import ChatDetails, CohereChatRequest, OnDemandServingMode

    config = _oci_config()
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(config)
    chat_request = CohereChatRequest(message=prompt, max_tokens=600, temperature=0.2)
    details = ChatDetails(
        compartment_id=os.environ["OCI_COMPARTMENT_ID"],
        serving_mode=OnDemandServingMode(model_id=os.environ["OCI_GENAI_MODEL_ID"]),
        chat_request=chat_request,
    )
    response = client.chat(details)
    return response.data.chat_response.text


def _real_classify(raw_text: str) -> LetterType:
    prompt = (
        "Classify this letter into exactly one label: ssa_benefit_letter, "
        "bank_statement, medicare_notice, hra_renewal_notice, medical_bill, other. "
        "Reply with only the label.\n\nLetter text:\n" + raw_text
    )
    label = _genai_chat(prompt).strip().lower()
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
    output = _genai_chat(prompt)
    return json.loads(output)


def _numbers_in(text: str) -> set[str]:
    return {m.replace(",", "") for m in _NUMBER_RE.findall(text)}


def _assert_numbers_preserved(output_text: str, source_text: str) -> None:
    unknown = _numbers_in(output_text) - _numbers_in(source_text)
    if unknown:
        raise ValueError(f"GenAI explanation introduced numbers not present in source data: {unknown}")


def _real_explain(letter_type: LetterType, fields: dict, language: str) -> str:
    source_text = json.dumps(fields)
    prompt = (
        f"Explain this {letter_type.value} to someone reading at a 6th-grade level, in {language}, "
        "in 2-4 short sentences. Never change any number, date, dollar amount, or program name -- "
        f"keep official English program names in parentheses. Data: {source_text}"
    )
    output = _genai_chat(prompt)
    _assert_numbers_preserved(output, source_text)
    return output


# ---------------------------------------------------------------------------
# Public dispatch -- callers never branch on MOCK_MODE themselves.
# ---------------------------------------------------------------------------


def ocr_document(image_bytes: bytes, filename: str) -> OcrResult:
    """OCI Document Understanding: OCR + key-value extraction."""
    if _mock_mode():
        return _mock_ocr(filename)
    return _real_ocr(image_bytes)


def classify_letter(raw_text: str) -> LetterType:
    """OCI GenAI: classify the letter type from its OCR'd text."""
    if _mock_mode():
        return _mock_classify(raw_text)
    return _real_classify(raw_text)


def extract_fields(
    letter_type: LetterType, raw_text: str, key_values: dict, retry_after_invalid: bool = False
) -> dict:
    """OCI GenAI: extract typed fields for the given letter type."""
    if _mock_mode():
        return _mock_extract(letter_type, raw_text)
    return _real_extract(letter_type, raw_text, key_values, retry_after_invalid)


def explain_letter(letter_type: LetterType, fields: dict, language: str) -> str:
    """OCI GenAI: plain-language explanation of this letter in the user's language."""
    if _mock_mode():
        return _mock_explain(letter_type, fields, language)
    return _real_explain(letter_type, fields, language)
