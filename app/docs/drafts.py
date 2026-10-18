"""Signed, short-lived letter drafts.

Reading a letter saves nothing on the server: the extracted facts go back
to the user's browser inside a signed draft. The signature stops the draft
being altered (e.g. flipping "sample" to "real") or used by another
account; the user's corrections travel separately and are checked on
confirm. Drafts expire after DRAFT_TTL.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

DRAFT_TTL_SECONDS = 30 * 60

# Set LETTERLENS_SECRET to keep drafts valid across restarts / multiple
# server processes; otherwise a random per-process key is used.
_SECRET = (os.getenv("LETTERLENS_SECRET") or secrets.token_hex(32)).encode()


class DraftInvalid(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_draft(user_id: str, payload: dict) -> str:
    body = dict(payload, u=user_id, x=int(time.time()) + DRAFT_TTL_SECONDS)
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    mac = hmac.new(_SECRET, raw, hashlib.sha256).digest()
    return f"{_b64(raw)}.{_b64(mac)}"


def open_draft(user_id: str, token: str) -> dict:
    try:
        raw_part, mac_part = token.split(".")
        raw, mac = _unb64(raw_part), _unb64(mac_part)
    except (ValueError, AttributeError) as exc:
        raise DraftInvalid() from exc
    if not hmac.compare_digest(mac, hmac.new(_SECRET, raw, hashlib.sha256).digest()):
        raise DraftInvalid()
    body = json.loads(raw)
    if body.get("u") != user_id or body.get("x", 0) < time.time():
        raise DraftInvalid()
    return body
