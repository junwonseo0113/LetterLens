"""Demo vs. production switches.

DEMO_MODE=true is an explicit opt-in for hackathon demos. Only in demo mode:
- the sign-in code is returned in the API response and shown on screen
  (there is no SMS sender yet), and
- the caseworker queue accepts the built-in key "demo-caseworker".

Outside demo mode the server refuses to start until the production
settings below are provided, instead of quietly running with demo
shortcuts. MOCK_MODE (canned AI responses) is a separate switch.
"""

from __future__ import annotations

import os

DEMO_CASEWORKER_KEY = "demo-caseworker"


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def demo_mode() -> bool:
    return _flag("DEMO_MODE")


def caseworker_key() -> str | None:
    key = os.getenv("CASEWORKER_KEY", "").strip()
    if key:
        return key
    return DEMO_CASEWORKER_KEY if demo_mode() else None


def sms_sender_configured() -> bool:
    # No SMS provider is implemented yet; see app/auth/service.py send_code().
    return False


def production_config_problems() -> list[str]:
    """What's missing to run safely outside demo mode (empty in demo mode)."""
    if demo_mode():
        return []
    problems = []
    key = os.getenv("CASEWORKER_KEY", "").strip()
    if not key:
        problems.append("CASEWORKER_KEY is not set (the caseworker queue has no default key outside demo mode).")
    elif key == DEMO_CASEWORKER_KEY:
        problems.append("CASEWORKER_KEY is the public demo key; choose a private one.")
    if not sms_sender_configured():
        problems.append(
            "No SMS sender is configured, so sign-in codes can't be delivered. "
            "None is implemented yet -- run with DEMO_MODE=true for demos."
        )
    return problems


def assert_production_ready() -> None:
    problems = production_config_problems()
    if problems:
        raise RuntimeError(
            "LetterLens is not in demo mode (DEMO_MODE is not true) and is missing required settings:\n- "
            + "\n- ".join(problems)
        )
