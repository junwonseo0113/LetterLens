"""OCI GenAI drafts the QMB dispute letter and its translation.

Same MOCK_MODE convention as app/docs and app/explain. Which charges get
disputed is decided by app.protect.bill_check (deterministic); GenAI only
ever drafts prose from the already-flagged facts, and every output is
checked against app.number_guard so dollar amounts can't drift between
the English draft and its translation.
"""

from __future__ import annotations

import json

from app.number_guard import assert_numbers_preserved
from app.oci_genai import genai_chat
from app.trace import call_with_fallback

from .schemas import DisputeLetter, FlaggedLineItem


def _mock_english_letter(provider: str, flagged_line_items: list[FlaggedLineItem]) -> str:
    lines = "\n".join(
        f"- {item.description}: ${item.amount:,.2f} ({item.category})" for item in flagged_line_items
    )
    total = sum(item.amount for item in flagged_line_items)
    return (
        f"To {provider},\n\n"
        "I am enrolled in the Qualified Medicare Beneficiary (QMB) program. Under federal law, "
        "QMB members cannot be billed for Medicare deductibles, coinsurance, or copays on "
        "Medicare-covered services. Please correct my bill and remove the following charges:\n\n"
        f"{lines}\n\n"
        f"Total disputed amount: ${total:,.2f}\n\n"
        "Please confirm in writing that these charges have been removed. Thank you."
    )


def _real_english_letter(provider: str, flagged_line_items: list[FlaggedLineItem]) -> str:
    source_text = provider + json.dumps([item.model_dump() for item in flagged_line_items])
    prompt = (
        "Draft a short, polite dispute letter (under 150 words) to this medical provider. "
        "The patient is enrolled in QMB (Qualified Medicare Beneficiary) and federal law bars "
        "billing QMB members for Medicare deductibles, coinsurance, or copays on Medicare-covered "
        "services. Ask the provider to remove exactly these charges and confirm in writing. "
        "Never invent amounts or line items beyond what's given, never change any number. "
        f"Provider: {provider}. Flagged charges: {source_text}"
    )
    output = genai_chat(prompt)
    assert_numbers_preserved(output, source_text)
    return output


def _mock_chinese_letter(provider: str, flagged_line_items: list[FlaggedLineItem]) -> str:
    # Hand-written Chinese template for the offline demo, mirroring the
    # English draft line for line so the user can compare side by side.
    lines = "\n".join(
        f"- {item.description}: ${item.amount:,.2f} ({item.category})" for item in flagged_line_items
    )
    total = sum(item.amount for item in flagged_line_items)
    return (
        f"致 {provider}：\n\n"
        "我已加入合格医疗保险受益人计划 (Qualified Medicare Beneficiary, QMB)。根据联邦法律，"
        "对于医疗保险承保的服务，不得向 QMB 会员收取医疗保险的自付额、共同保险或共付额。"
        "请更正我的账单，删除以下收费：\n\n"
        f"{lines}\n\n"
        f"争议总金额：${total:,.2f}\n\n"
        "请以书面形式确认这些收费已被删除。谢谢。"
    )


def _mock_translate(
    english: str, language: str, provider: str, flagged_line_items: list[FlaggedLineItem]
) -> str:
    if language.lower() in ("en", "english"):
        return english
    if language.lower() in ("zh", "chinese"):
        return _mock_chinese_letter(provider, flagged_line_items)
    return f"[MOCK_MODE: shown in English, not translated to {language}]\n\n{english}"


def _real_translate(english: str, language: str) -> str:
    prompt = (
        f"Translate this letter into {language}. Never change any number, date, or dollar amount -- "
        f"keep program names like QMB in parentheses in English.\n\n{english}"
    )
    translated = genai_chat(prompt)
    assert_numbers_preserved(translated, english)
    return translated


def draft_dispute_letter(provider: str, flagged_line_items: list[FlaggedLineItem], language: str) -> DisputeLetter:
    english = call_with_fallback(
        lambda: _real_english_letter(provider, flagged_line_items),
        lambda: _mock_english_letter(provider, flagged_line_items),
    )
    translated = call_with_fallback(
        lambda: _real_translate(english, language),
        lambda: _mock_translate(english, language, provider, flagged_line_items),
    )
    return DisputeLetter(english=english, translated=translated, language=language)
