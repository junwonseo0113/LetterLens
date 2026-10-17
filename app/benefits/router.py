from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.explain import ExplainedProgramResult
from app.models import ProfileRecord

from .service import get_benefits

router = APIRouter()


@router.get("/benefits", response_model=list[ExplainedProgramResult])
def list_benefits(
    user_id: str = Query("demo"), language: str = Query("en"), session: Session = Depends(get_session)
) -> list[ExplainedProgramResult]:
    return get_benefits(session, user_id, language)


@router.post("/profile/on-qmb")
def set_on_qmb(
    on_qmb: bool, user_id: str = Query("demo"), session: Session = Depends(get_session)
) -> dict:
    """Mark whether the user is a documented, currently-enrolled QMB member.

    No letter type extracts this fact yet (no QMB-enrollment-letter
    schema exists), so this is the user's own self-report -- it only
    drives the PROTECT illegal-billing check, never eligibility.
    """
    profile = session.get(ProfileRecord, user_id)
    if profile is None:
        profile = ProfileRecord(user_id=user_id)
    profile.on_qmb = on_qmb
    session.add(profile)
    session.commit()
    return {"user_id": user_id, "on_qmb": on_qmb}
