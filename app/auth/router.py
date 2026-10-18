from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.models import AuthSession

from .deps import current_user
from .service import AuthError, send_code, show_code_in_response, sign_out, verify_code

router = APIRouter(prefix="/auth")


def _error(exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message_en, "detail_zh": exc.message_zh}
    )


class RequestCodeIn(BaseModel):
    phone: str


class RequestCodeOut(BaseModel):
    sent: bool
    # Only set in explicit demo mode (DEMO_MODE=true); there is no SMS sender yet.
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
def request_code(body: RequestCodeIn, session: Session = Depends(get_session)):
    try:
        _, code = send_code(session, body.phone)
    except AuthError as exc:
        return _error(exc)
    return RequestCodeOut(sent=True, demo_code=code if show_code_in_response() else None)


@router.post("/verify", response_model=SessionOut)
def verify(body: VerifyIn, session: Session = Depends(get_session)):
    try:
        auth = verify_code(session, body.phone, body.code)
    except AuthError as exc:
        return _error(exc)
    return SessionOut(token=auth.token, user_id=auth.user_id, phone=auth.phone)


@router.get("/me", response_model=MeOut)
def me(auth: AuthSession = Depends(current_user)) -> MeOut:
    return MeOut(user_id=auth.user_id, phone=auth.phone)


@router.post("/sign-out")
def sign_out_route(auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    sign_out(session, auth)
    return {"signed_out": True}
