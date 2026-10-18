from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

from app import settings
from app.auth import current_user
from app.db import get_session
from app.models import AuthSession

from . import service
from .service import ApplicationOut, ApplyError

router = APIRouter()


class StartIn(BaseModel):
    program: str = "MSP"


class AnswerIn(BaseModel):
    value: str


class SubmitIn(BaseModel):
    signature_png: str
    confirmed: bool


class ReviewIn(BaseModel):
    note: str | None = None
    # Approve only: documents whose originals the caseworker checked.
    verified_documents: list[str] = []


def _error(exc: ApplyError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message_en, "detail_zh": exc.message_zh}
    )


def require_caseworker(x_caseworker_key: str = Header(default="")) -> None:
    # One shared key; a real deployment needs caseworker accounts. The
    # built-in "demo-caseworker" key only works in DEMO_MODE.
    expected = settings.caseworker_key()
    if expected is None:
        raise HTTPException(status_code=503, detail="Caseworker access isn't configured (set CASEWORKER_KEY).")
    if not secrets.compare_digest(x_caseworker_key, expected):
        raise HTTPException(status_code=401, detail="Caseworker key required.")


# --- applicant ---------------------------------------------------------------


@router.post("/applications", response_model=ApplicationOut)
def start_application(
    body: StartIn, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    try:
        app = service.get_or_start(session, auth, body.program)
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)


@router.get("/applications/current", response_model=ApplicationOut | None)
def current_application(
    program: str = "MSP", auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    """The user's application, or null if they haven't started one."""
    app = service.find_current(session, auth, program)
    return service.to_out(session, app) if app else None


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    try:
        app = service.get_owned(session, auth, application_id)
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)


@router.put("/applications/{application_id}/fields/{key}", response_model=ApplicationOut)
def answer_field(
    application_id: int,
    key: str,
    body: AnswerIn,
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    try:
        app = service.get_owned(session, auth, application_id)
        app = service.answer_field(session, app, key, body.value)
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)


@router.post("/applications/{application_id}/documents/{key}", response_model=ApplicationOut)
async def add_document(
    application_id: int,
    key: str,
    file: UploadFile,
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    image_bytes = await file.read()
    try:
        if not image_bytes:
            raise ApplyError("Empty photo.", "照片是空的。")
        app = service.get_owned(session, auth, application_id)
        app = service.add_document(session, app, key)
    except ApplyError as exc:
        return _error(exc)
    finally:
        # Same hard rule as letters: the photo itself is never stored.
        del image_bytes
    return service.to_out(session, app)


@router.post("/applications/{application_id}/submit", response_model=ApplicationOut)
def submit_application(
    application_id: int,
    body: SubmitIn,
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    try:
        app = service.get_owned(session, auth, application_id)
        app = service.submit(session, app, body.signature_png, body.confirmed)
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)


# --- caseworker --------------------------------------------------------------


@router.get(
    "/review-queue", response_model=list[ApplicationOut], dependencies=[Depends(require_caseworker)]
)
def get_review_queue(session: Session = Depends(get_session)):
    return [service.to_out(session, app) for app in service.review_queue(session)]


@router.post(
    "/review-queue/{application_id}/approve",
    response_model=ApplicationOut,
    dependencies=[Depends(require_caseworker)],
)
def approve(application_id: int, body: ReviewIn, session: Session = Depends(get_session)):
    try:
        app = service.approve(session, application_id, body.note, body.verified_documents)
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)


@router.post(
    "/review-queue/{application_id}/request-info",
    response_model=ApplicationOut,
    dependencies=[Depends(require_caseworker)],
)
def request_info(application_id: int, body: ReviewIn, session: Session = Depends(get_session)):
    try:
        app = service.request_info(session, application_id, body.note or "")
    except ApplyError as exc:
        return _error(exc)
    return service.to_out(session, app)
