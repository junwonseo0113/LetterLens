from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models import LetterRecord

from .pipeline import ExtractionError, process_letter
from .schemas import LetterSummary, LetterUploadResponse

router = APIRouter()


@router.get("/letters", response_model=list[LetterSummary])
def list_letters(user_id: str = Query("demo"), session: Session = Depends(get_session)) -> list[LetterSummary]:
    records = session.exec(
        select(LetterRecord).where(LetterRecord.user_id == user_id).order_by(LetterRecord.created_at.desc())
    ).all()
    return [
        LetterSummary(id=r.id, letter_type=r.letter_type, created_at=r.created_at) for r in records
    ]


@router.post("/letters", response_model=LetterUploadResponse)
async def upload_letter(
    file: UploadFile,
    language: str = Form(...),
    user_id: str = Form("demo"),
    session: Session = Depends(get_session),
) -> LetterUploadResponse:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    try:
        return process_letter(
            session=session,
            image_bytes=image_bytes,
            filename=file.filename or "upload",
            language=language,
            user_id=user_id,
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        # Hard rule: never persist raw uploaded images after extraction.
        del image_bytes
