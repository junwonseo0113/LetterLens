"""Data-minimization rules and log-safe error descriptions.

See docs/PRIVACY.md for the full document lifecycle.
"""

from __future__ import annotations

# Fields kept after the user confirms a letter -- only what eligibility,
# reminders, the bill check or re-showing the letter actually use. Full OCR
# text is never kept; free-text summaries are dropped.
SAVED_FIELDS: dict[str, list[str]] = {
    "ssa_benefit_letter": ["gross_monthly_benefit", "part_b_deduction", "net_payment", "effective_date"],
    "bank_statement": ["ending_balance", "recurring_deposits"],
    "hra_renewal_notice": ["program", "deadline", "required_documents"],
    "medical_bill": ["provider", "line_items", "is_medicare_claim"],
    "medicare_notice": [],
    "other": [],
}

# Personal identifiers a letter can carry. Saved only when the user ticks
# "use for my application", and never sent to the explanation step.
IDENTIFIER_FIELDS: dict[str, list[str]] = {
    "ssa_benefit_letter": ["recipient_name", "recipient_address"],
}

# Facts the user can correct before saving, and how each is checked
# (kinds from app.apply.normalize, plus "bool" and "list").
EDITABLE_FIELDS: dict[str, dict[str, str]] = {
    "ssa_benefit_letter": {
        "gross_monthly_benefit": "money",
        "part_b_deduction": "money",
        "net_payment": "money",
        "effective_date": "date",
        "recipient_name": "text",
        "recipient_address": "text",
    },
    "bank_statement": {"ending_balance": "money"},
    "hra_renewal_notice": {"program": "text", "deadline": "date", "required_documents": "list"},
    "medical_bill": {"provider": "text", "is_medicare_claim": "bool"},
}


def without_identifiers(letter_type: str, fields: dict) -> dict:
    drop = set(IDENTIFIER_FIELDS.get(letter_type, []))
    return {k: v for k, v in fields.items() if k not in drop}


def minimize(letter_type: str, fields: dict, keep_identifiers: bool = False) -> dict:
    """The subset of a letter's fields that is saved."""
    keep = list(SAVED_FIELDS.get(letter_type, []))
    if keep_identifiers:
        keep += IDENTIFIER_FIELDS.get(letter_type, [])
    saved = {k: fields[k] for k in keep if fields.get(k) not in (None, "")}
    if "recurring_deposits" in saved:
        # The amount is what's used; bank descriptions can name people/payers.
        saved["recurring_deposits"] = [{"description": "", "amount": d["amount"]} for d in saved["recurring_deposits"]]
    return saved


def describe_failure(exc: BaseException) -> str:
    """Log-safe description of an error: its type and any OCI status/code,
    never its message -- validation errors and some service errors repeat
    the input, which here is someone's letter."""
    parts = [type(exc).__name__]
    for attr in ("status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, (int, str)) and value != "":
            parts.append(f"{attr}={value}")
    return " ".join(parts)
