from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.auth import current_user
from app.db import get_session
from app.models import AuthSession, LetterRecord

from . import pipeline
from .schemas import LetterSummary, LetterUploadResponse

router = APIRouter()


def _error(status: int, en: str, zh: str, retryable: bool = False) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": en, "detail_zh": zh, "retryable": retryable})


@router.get("/letters", response_model=list[LetterSummary])
def list_letters(
    auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
) -> list[LetterSummary]:
    records = session.exec(
        select(LetterRecord).where(LetterRecord.user_id == auth.user_id).order_by(LetterRecord.created_at.desc())
    ).all()
    return [
        LetterSummary(
            id=r.id,
            letter_type=r.letter_type,
            created_at=r.created_at,
            # Saved before this flag existed = MOCK_MODE sample (real OCI never ran).
            is_sample=r.is_sample is not False,
        )
        for r in records
    ]


@router.get("/letters/{letter_id}", response_model=LetterUploadResponse)
def get_letter(
    letter_id: int,
    language: str = Query("en"),
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    try:
        return pipeline.get_letter(session, auth.user_id, letter_id, language)
    except pipeline.LetterNotFound:
        return _error(404, "Letter not found.", "找不到这封信。")


@router.post("/letters", response_model=LetterUploadResponse)
async def upload_letter(
    file: UploadFile,
    language: str = Form(...),
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    image_bytes = await file.read()
    try:
        if not image_bytes:
            return _error(400, "The photo was empty. Please try again.", "照片是空的，请再试一次。", retryable=True)
        return pipeline.process_letter(
            session=session,
            image_bytes=image_bytes,
            filename=file.filename or "upload",
            language=language,
            user_id=auth.user_id,
        )
    except pipeline.LetterReadError as exc:
        return _error(502, exc.message_en, exc.message_zh, retryable=True)
    finally:
        # Hard rule: never persist raw uploaded images after extraction.
        del image_bytes
