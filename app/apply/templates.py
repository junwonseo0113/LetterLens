"""What each application asks for, in the order the interview asks it.

MSP is modeled on the NY DOH-4328 application. Applying for MSP also
gets the user Extra Help automatically, so one application covers both.
`prefill` names where a value can come from before the user is asked:
  ("letter", letter_type, extracted_field) -- latest letter of that type
  ("profile", profile_field)                -- merged ProfileRecord
  ("sign_in", "phone")                      -- the verified phone number
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    key: str
    kind: str  # see app.apply.normalize.NORMALIZERS
    label_en: str
    label_zh: str
    question_en: str
    question_zh: str
    prefill: tuple | None = None


MSP_FIELDS: list[FieldSpec] = [
    FieldSpec(
        "full_name", "text", "Full name", "姓名",
        "What is your full name, as it appears on your Medicare card?",
        "您的全名是什么？请按医疗保险卡上的写法说。",
        ("letter", "ssa_benefit_letter", "recipient_name"),
    ),
    FieldSpec(
        "date_of_birth", "date", "Date of birth", "出生日期",
        "What is your date of birth?",
        "您的出生日期是哪年哪月哪日？",
    ),
    FieldSpec(
        "home_address", "text", "Home address", "家庭住址",
        "What is your home address?",
        "您的家庭住址是什么？",
        ("letter", "ssa_benefit_letter", "recipient_address"),
    ),
    FieldSpec(
        "phone", "phone", "Phone number", "电话号码",
        "What phone number can the agency call you at?",
        "政府部门可以打哪个电话号码联系您？",
        ("sign_in", "phone"),
    ),
    FieldSpec(
        "medicare_number", "medicare_number", "Medicare number", "医疗保险号码",
        "What is your Medicare number? It's on your red, white and blue Medicare card.",
        "您的医疗保险号码是什么？它印在红白蓝色的医疗保险卡上。",
    ),
    FieldSpec(
        "married", "yesno", "Married and living with spouse", "已婚并与配偶同住",
        "Are you married and living with your spouse?",
        "您是否已婚并且和配偶住在一起？",
        ("profile", "married"),
    ),
    FieldSpec(
        "household_size", "count", "People in household", "家庭人数",
        "How many people live in your home, including you?",
        "包括您自己，您家里一共住几个人？",
        ("profile", "household_size"),
    ),
    FieldSpec(
        "monthly_social_security", "money", "Social Security per month (before deductions)",
        "每月社会安全福利（扣除前）",
        "How much Social Security do you get each month, before deductions?",
        "您每个月的社会安全福利（扣除前）是多少钱？",
        ("profile", "ss_gross_monthly"),
    ),
    FieldSpec(
        "monthly_work_income", "money", "Work income per month", "每月工作收入",
        "Do you earn any money from work each month? If not, say 'none'.",
        "您每个月有工作收入吗？如果没有，请说“没有”。",
        ("profile", "earned_income_monthly"),
    ),
]

TEMPLATES: dict[str, list[FieldSpec]] = {"MSP": MSP_FIELDS}

# Which programs this application covers, for display.
COVERS: dict[str, list[str]] = {"MSP": ["MSP", "Extra Help"]}


def field_spec(program: str, key: str) -> FieldSpec | None:
    return next((f for f in TEMPLATES[program] if f.key == key), None)
