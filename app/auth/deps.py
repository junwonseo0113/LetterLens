from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import AuthSession

from .service import session_for_token


def current_user(
    authorization: str = Header(default=""), session: Session = Depends(get_session)
) -> AuthSession:
    token = authorization.removeprefix("Bearer ").strip()
    auth = session_for_token(session, token)
    if auth is None:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    return auth
