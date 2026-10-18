"""Fixed Chinese wording for short terms that come from letters.

Only exact, known phrases -- anything unrecognized is shown as written on
the letter rather than guessed at.
"""

from __future__ import annotations

DOCUMENT_NAMES_ZH = {
    "proof of income": "收入证明",
    "proof of residence": "居住证明",
    "proof of address": "地址证明",
    "id": "身份证明",
    "photo id": "带照片的身份证明",
    "proof of identity": "身份证明",
    "social security card": "社会安全卡",
    "medicare card": "医疗保险卡",
    "bank statement": "银行对账单",
}

COST_SHARING_ZH = {
    "deductible": "自付额",
    "coinsurance": "共同保险",
    "copay": "共付额",
    "other": "其他",
}


def is_zh(language: str) -> bool:
    return (language or "").lower() in ("zh", "chinese")


def document_name_zh(name: str) -> str:
    return DOCUMENT_NAMES_ZH.get(name.strip().lower(), name)
