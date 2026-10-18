"""Phone one-time-code sign-in.

The point is trust: a user proves they hold the phone number before the
app will build or submit an application in their name. There is no SMS
provider wired up, so with DEMO_SHOW_OTP=true (the default) the code is
returned in the API response and shown on screen. Set DEMO_SHOW_OTP=false
once a real SMS sender is plugged in at send_code().
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import AuthSession, OtpChallenge

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5


class AuthError(Exception):
    pass


def show_code_in_response() -> bool:
    return os.getenv("DEMO_SHOW_OTP", "true").lower() not in ("0", "false", "no")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise AuthError("Enter a 10-digit US phone number.")
    return digits


def user_id_for_phone(phone: str) -> str:
    # Stable per phone number, without putting the number itself in URLs.
    return "u_" + hashlib.sha256(phone.encode()).hexdigest()[:12]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite hands datetimes back naive; they were written as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def send_code(session: Session, raw_phone: str) -> tuple[str, str]:
    """Create a fresh code for this phone. Returns (phone, code)."""
    phone = normalize_phone(raw_phone)
    code = f"{secrets.randbelow(1_000_000):06d}"
    session.add(OtpChallenge(phone=phone, code=code, expires_at=_utcnow() + CODE_TTL))
    session.commit()
    # Real deployment: hand (phone, code) to an SMS provider here.
    return phone, code


def verify_code(session: Session, raw_phone: str, code: str) -> AuthSession:
    phone = normalize_phone(raw_phone)
    challenge = session.exec(
        select(OtpChallenge)
        .where(OtpChallenge.phone == phone, OtpChallenge.used == False)  # noqa: E712
        .order_by(OtpChallenge.id.desc())
    ).first()
    if challenge is None or _aware(challenge.expires_at) < _utcnow():
        raise AuthError("This code has expired. Ask for a new one.")
    if challenge.attempts >= MAX_ATTEMPTS:
        raise AuthError("Too many tries. Ask for a new code.")

    challenge.attempts += 1
    if not secrets.compare_digest(challenge.code, (code or "").strip()):
        session.add(challenge)
        session.commit()
        raise AuthError("That code is not right. Please try again.")

    challenge.used = True
    auth = AuthSession(token=secrets.token_urlsafe(32), user_id=user_id_for_phone(phone), phone=phone)
    session.add(challenge)
    session.add(auth)
    session.commit()
    session.refresh(auth)
    return auth


def session_for_token(session: Session, token: str) -> AuthSession | None:
    return session.get(AuthSession, token) if token else None
