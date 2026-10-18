from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.models import AuthSession

from .deps import current_user
from .service import AuthError, send_code, show_code_in_response, verify_code

router = APIRouter(prefix="/auth")


class RequestCodeIn(BaseModel):
    phone: str


class RequestCodeOut(BaseModel):
    sent: bool
    # Only set while no SMS provider is configured (DEMO_SHOW_OTP=true).
    demo_code: str | None = None


class VerifyIn(BaseModel):
    phone: str
    code: str


class SessionOut(BaseModel):
    token: str
    user_id: str
    phone: str


class MeOut(BaseModel):
    user_id: str
    phone: str


@router.post("/request-code", response_model=RequestCodeOut)
def request_code(body: RequestCodeIn, session: Session = Depends(get_session)) -> RequestCodeOut:
    try:
        _, code = send_code(session, body.phone)
    except AuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RequestCodeOut(sent=True, demo_code=code if show_code_in_response() else None)


@router.post("/verify", response_model=SessionOut)
def verify(body: VerifyIn, session: Session = Depends(get_session)) -> SessionOut:
    try:
        auth = verify_code(session, body.phone, body.code)
    except AuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SessionOut(token=auth.token, user_id=auth.user_id, phone=auth.phone)


@router.get("/me", response_model=MeOut)
def me(auth: AuthSession = Depends(current_user)) -> MeOut:
    return MeOut(user_id=auth.user_id, phone=auth.phone)
