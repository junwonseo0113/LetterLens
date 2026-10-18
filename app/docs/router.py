from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.auth import current_user
from app.db import get_session
from app.models import AuthSession, LetterRecord
from app.uploads import UploadTooLarge, read_and_close, wipe

from . import pipeline
from .drafts import DraftInvalid
from .schemas import ConfirmIn, LetterDraftOut, LetterSummary, LetterUploadResponse

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


@router.post("/letters/read", response_model=LetterDraftOut)
async def read_letter(
    file: UploadFile,
    language: str = Form(...),
    auth: AuthSession = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Read a letter photo and return a draft. Nothing is saved: the
    original is discarded when this request ends (success, failure or
    cancellation), and the facts are saved only via /letters/confirm."""
    image = None
    try:
        image = await read_and_close(file)
        if not image:
            return _error(400, "The photo was empty. Please try again.", "照片是空的，请再试一次。", retryable=True)
        # Blocking OCI calls run off the event loop. If the client goes away
        # the await is cancelled and the finally below still cleans up;
        # reading writes nothing, so there's nothing half-saved.
        return await run_in_threadpool(
            pipeline.read_letter,
            session=session,
            image=image,
            filename=file.filename or "upload",
            language=language,
            user_id=auth.user_id,
        )
    except UploadTooLarge:
        return _error(413, "That photo is too large (over 10 MB).", "照片太大（超过10MB）。", retryable=True)
    except pipeline.LetterReadError as exc:
        return _error(502, exc.message_en, exc.message_zh, retryable=True)
    finally:
        wipe(image)


@router.post("/letters/confirm", response_model=LetterUploadResponse)
def confirm_letter(
    body: ConfirmIn, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    """Save a draft after the user checked (and maybe corrected) the facts."""
    try:
        return pipeline.confirm_letter(
            session=session,
            user_id=auth.user_id,
            draft_token=body.draft_token,
            facts=body.facts,
            save_identifiers=body.save_identifiers,
            language=body.language,
        )
    except DraftInvalid:
        return _error(
            410,
            "This scan has expired and wasn't saved. Please scan the letter again.",
            "这次扫描已过期，没有保存。请重新扫描这封信。",
            retryable=False,
        )
    except pipeline.CorrectionError as exc:
        return _error(422, exc.message_en, exc.message_zh)
