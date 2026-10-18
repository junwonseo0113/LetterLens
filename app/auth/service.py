"""Phone one-time-code sign-in.

The point is trust: a user proves they hold the phone number before the
app will build or submit an application in their name. There is no SMS
provider wired up, so the code is returned in the API response and shown
on screen -- but only in explicit demo mode (DEMO_MODE=true, see
app/settings.py). Outside demo mode, asking for a code fails clearly until
a real SMS sender is plugged in at send_code().
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app import settings
from app.models import AuthSession, OtpChallenge

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
# At most this many codes per phone number per window, so the endpoint
# can't be used to spam someone's phone (or brute-force by re-requesting).
MAX_CODES_PER_WINDOW = 5
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)


class AuthError(Exception):
    def __init__(self, message_en: str, message_zh: str, status_code: int = 422):
        super().__init__(message_en)
        self.message_en = message_en
        self.message_zh = message_zh
        self.status_code = status_code


def show_code_in_response() -> bool:
    return settings.demo_mode()


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise AuthError("Enter a 10-digit US phone number.", "请输入10位数的美国电话号码。")
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
    if not settings.demo_mode() and not settings.sms_sender_configured():
        raise AuthError(
            "Sign-in by text message isn't set up on this server yet.",
            "此服务器尚未设置短信登录。",
            status_code=503,
        )
    # expires_at - CODE_TTL is when each code was issued.
    recent = session.exec(
        select(OtpChallenge).where(
            OtpChallenge.phone == phone, OtpChallenge.expires_at > _utcnow() + CODE_TTL - CODE_WINDOW
        )
    ).all()
    if len(recent) >= MAX_CODES_PER_WINDOW:
        raise AuthError(
            "Too many codes requested. Please wait 15 minutes.",
            "请求验证码次数太多，请等15分钟再试。",
            status_code=429,
        )
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
        raise AuthError("This code has expired. Ask for a new one.", "验证码已过期，请重新获取。")
    if challenge.attempts >= MAX_ATTEMPTS:
        raise AuthError("Too many tries. Ask for a new code.", "尝试次数太多，请重新获取验证码。")

    challenge.attempts += 1
    if not secrets.compare_digest(challenge.code, (code or "").strip()):
        session.add(challenge)
        session.commit()
        raise AuthError("That code is not right. Please try again.", "验证码不对，请再试一次。")

    challenge.used = True
    auth = AuthSession(token=secrets.token_urlsafe(32), user_id=user_id_for_phone(phone), phone=phone)
    session.add(challenge)
    session.add(auth)
    session.commit()
    session.refresh(auth)
    return auth


def session_for_token(session: Session, token: str) -> AuthSession | None:
    auth = session.get(AuthSession, token) if token else None
    if auth is None:
        return None
    if _aware(auth.created_at) + SESSION_TTL < _utcnow():
        session.delete(auth)
        session.commit()
        return None
    return auth


def sign_out(session: Session, auth: AuthSession) -> None:
    session.delete(auth)
    session.commit()
