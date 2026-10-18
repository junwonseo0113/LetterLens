from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import current_user
from app.db import get_session
from app.models import AuthSession, ProfileRecord

from .service import AnswerError, BenefitsResult, get_benefits, save_answer

router = APIRouter()


@router.get("/benefits", response_model=BenefitsResult)
def list_benefits(
    language: str = Query("en"),
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
) -> BenefitsResult:
    return get_benefits(session, auth.user_id, language)


class AnswerIn(BaseModel):
    key: str
    value: str


@router.post("/profile/answers")
def answer_question(
    body: AnswerIn, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    """Answer one fact the benefits check is missing (see BenefitsResult.questions)."""
    try:
        value = save_answer(session, auth.user_id, body.key, body.value)
    except AnswerError as exc:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message_en, "detail_zh": exc.message_zh}
        )
    return {"key": body.key, "value": value}


@router.get("/profile/on-qmb")
def get_on_qmb(auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    """Current on_qmb value, so the UI toggle can reflect real state on
    load instead of always starting unchecked regardless of what was
    saved on a previous visit."""
    profile = session.get(ProfileRecord, auth.user_id)
    return {"user_id": auth.user_id, "on_qmb": bool(profile.on_qmb) if profile else False}


@router.post("/profile/on-qmb")
def set_on_qmb(
    on_qmb: bool, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    """Mark whether the user is a documented, currently-enrolled QMB member.

    No letter type extracts this fact yet (no QMB-enrollment-letter
    schema exists), so this is the user's own self-report -- it only
    drives the PROTECT illegal-billing check, never eligibility.
    """
    profile = session.get(ProfileRecord, auth.user_id)
    if profile is None:
        profile = ProfileRecord(user_id=auth.user_id)
    profile.on_qmb = on_qmb
    session.add(profile)
    session.commit()
    return {"user_id": auth.user_id, "on_qmb": on_qmb}
