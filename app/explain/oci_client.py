"""OCI GenAI call that explains a ProgramResult in the user's language.

Same MOCK_MODE convention as app/docs/oci_client.py: mock is the default
and only tested path. The LLM is handed the already-decided status,
numbers_used, and rule_applied -- it writes prose, it never re-derives or
overrides the decision. Real-mode output is checked against
app.number_guard before being returned.
"""

from __future__ import annotations

import json

from app.number_guard import assert_numbers_preserved
from app.oci_genai import genai_chat
from app.rules.engine import ProgramResult
from app.trace import call_with_fallback

STATUS_PHRASES = {
    "likely": "you likely qualify for",
    "possible": "you might qualify for",
    "not_now": "you don't qualify right now for",
    "already_enrolled": "you're already enrolled in",
    "missing_info": "we need more information to check",
}


def _status_value(result: ProgramResult) -> str:
    return result.status.value if hasattr(result.status, "value") else result.status


def _source_text(result: ProgramResult) -> str:
    return json.dumps(
        {
            "program": result.program,
            "status": _status_value(result),
            "monthly_value": result.monthly_value,
            "annual_value": result.annual_value,
            "numbers_used": result.numbers_used,
            "rule_applied": result.rule_applied,
        }
    )


STATUS_PHRASES_ZH = {
    "likely": "您很可能符合",
    "possible": "您也许符合",
    "not_now": "您目前不符合",
    "already_enrolled": "您已经加入了",
    "missing_info": "我们需要更多信息才能判断您是否符合",
}


def _mock_explain_zh(result: ProgramResult) -> str:
    # Hand-written Chinese template for the offline demo; program names and
    # dollar amounts stay exactly as the rules engine produced them.
    phrase = STATUS_PHRASES_ZH.get(_status_value(result), "以下是")
    sentence = f"根据您信件上的数字，{phrase} {result.program} 的条件。"
    if result.monthly_value:
        sentence += f"每月大约可以帮您省下 ${result.monthly_value:,.2f}。"
    sentence += f"（{result.rule_applied_zh}）"
    return sentence


def _mock_explain(result: ProgramResult, language: str) -> str:
    if language.lower() in ("zh", "chinese"):
        return _mock_explain_zh(result)
    note = (
        ""
        if language.lower() in ("en", "english")
        else f" [MOCK_MODE: shown in English, not translated to {language}]"
    )
    phrase = STATUS_PHRASES.get(_status_value(result), "the result for")
    sentence = f"Based on the numbers on your letters, {phrase} {result.program}."
    if result.monthly_value:
        sentence += f" That could be worth about ${result.monthly_value:,.2f} a month."
    sentence += f" {result.rule_applied}."
    return sentence + note


def _real_explain(result: ProgramResult, language: str) -> str:
    source_text = _source_text(result)
    prompt = (
        f"Explain this benefits result to someone reading at a 6th-grade level, in {language}, "
        "in 2-4 short sentences. Never change any number, date, dollar amount, or program name -- "
        f"keep official English program names in parentheses. Data: {source_text}"
    )
    output = genai_chat(prompt)
    assert_numbers_preserved(output, source_text)
    return output


def explain_program_result(result: ProgramResult, language: str) -> str:
    """OCI GenAI: plain-language explanation of one ProgramResult."""
    return call_with_fallback(
        lambda: _real_explain(result, language),
        lambda: _mock_explain(result, language),
    )
