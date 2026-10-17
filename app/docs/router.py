from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.db import get_session

from .pipeline import ExtractionError, process_letter
from .schemas import LetterUploadResponse

router = APIRouter()


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
