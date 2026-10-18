"""Turn a typed or spoken answer into a clean field value.

Deterministic, no LLM: voice input arrives as whatever the browser's
speech recognizer produced ("1952年3月5日", "没有", "two"), and this either
normalizes it or rejects it so the interview asks again. The user still
sees and confirms every value on the review screen.
"""

from __future__ import annotations

import re
from datetime import date

_CN_DIGITS = {"零": 0, "〇": 0, "○": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}
_CN_NUM_RUN = re.compile(r"[零〇○一二两三四五六七八九十百千万]+")

_EN_NUMBERS = {"zero": 0, "none": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
               "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_NONE_WORDS = ("没有", "无", "沒有", "none", "nothing", "no income", "zero")


class FieldValueError(ValueError):
    def __init__(self, message_en: str, message_zh: str):
        super().__init__(message_en)
        self.message_en = message_en
        self.message_zh = message_zh


def _cn_to_int(text: str) -> int:
    """Chinese numeral run -> int. 一九五二 -> 1952, 二十五 -> 25, 一千七百 -> 1700."""
    if not any(ch in _CN_UNITS or ch == "万" for ch in text):
        return int("".join(str(_CN_DIGITS[ch]) for ch in text))

    total, section, digit = 0, 0, 0
    for ch in text:
        if ch in _CN_DIGITS:
            digit = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            section += (digit or 1) * _CN_UNITS[ch]
            digit = 0
        elif ch == "万":
            total += (section + digit) * 10_000
            section, digit = 0, 0
    return total + section + digit


def cn_numerals_to_digits(text: str) -> str:
    return _CN_NUM_RUN.sub(lambda m: str(_cn_to_int(m.group())), text)


def normalize_date(raw: str) -> str:
    text = cn_numerals_to_digits(raw.strip())
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if match:
        year, month, day = (int(g) for g in match.groups())
    else:
        match = re.search(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", text)
        if not match:
            raise FieldValueError("Please say the year, month and day.", "请说出年、月、日。")
        month, day, year = (int(g) for g in match.groups())
    try:
        value = date(year, month, day)
    except ValueError as exc:
        raise FieldValueError("That date doesn't exist.", "这个日期不存在。") from exc
    if not 1900 <= value.year <= date.today().year:
        raise FieldValueError("Please check the year.", "请检查年份。")
    return value.isoformat()


def normalize_number(raw: str) -> str:
    text = raw.strip().lower()
    if any(word in text for word in _NONE_WORDS):
        return "0"
    text = cn_numerals_to_digits(text)
    for word, value in _EN_NUMBERS.items():
        text = re.sub(rf"\b{word}\b", str(value), text)
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        raise FieldValueError("Please say a number.", "请说一个数字。")
    value = float(match.group().replace(",", ""))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def normalize_yes_no(raw: str) -> str:
    text = raw.strip().lower()
    # Negatives first: "没有结婚" contains "结婚".
    if re.search(r"\b(no|not|nope|single|widowed|divorced)\b", text) or any(
        word in text for word in ("不", "没", "否", "单身", "未婚", "丧偶", "离婚")
    ):
        return "no"
    if re.search(r"\b(yes|yeah|yep|married)\b", text) or any(
        word in text for word in ("是", "对", "有", "已婚", "结婚", "嗯")
    ):
        return "yes"
    raise FieldValueError("Please answer yes or no.", "请回答“是”或“不是”。")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", cn_numerals_to_digits(raw))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise FieldValueError("Please say a 10-digit phone number.", "请说10位数的电话号码。")
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def normalize_medicare_number(raw: str) -> str:
    # Medicare Beneficiary Identifiers are 11 characters, letters and digits.
    value = re.sub(r"[^0-9A-Za-z]", "", cn_numerals_to_digits(raw)).upper()
    if len(value) != 11:
        raise FieldValueError(
            "A Medicare number has 11 letters and numbers -- it's on the red, white and blue card.",
            "医疗保险号码共11位字母和数字，印在红白蓝色的医疗保险卡上。",
        )
    return value


def normalize_text(raw: str) -> str:
    value = " ".join(raw.split())
    if not value:
        raise FieldValueError("Please give an answer.", "请回答这个问题。")
    return value


NORMALIZERS = {
    "date": normalize_date,
    "number": normalize_number,
    "yesno": normalize_yes_no,
    "phone": normalize_phone,
    "medicare_number": normalize_medicare_number,
    "text": normalize_text,
}


def normalize(kind: str, raw: str) -> str:
    return NORMALIZERS[kind](raw or "")
