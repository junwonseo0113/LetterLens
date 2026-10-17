from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.explain import ExplainedProgramResult

from .service import get_benefits

router = APIRouter()


@router.get("/benefits", response_model=list[ExplainedProgramResult])
def list_benefits(
    user_id: str = Query("demo"), language: str = Query("en"), session: Session = Depends(get_session)
) -> list[ExplainedProgramResult]:
    return get_benefits(session, user_id, language)
