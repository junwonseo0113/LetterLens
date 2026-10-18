"""Privacy info and "Delete my saved information".

Original photos are never saved, so there is nothing of them to delete;
this deletes the information LetterLens saved from them and from the
user's answers. See docs/PRIVACY.md.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, delete, select

from app.auth import current_user
from app.db import get_session
from app.models import ApplicationRecord, AuthSession, LetterRecord, OtpChallenge, ProfileRecord, Reminder
from app.trace import is_mock_mode

router = APIRouter()


class PrivacyInfo(BaseModel):
    # True: letters aren't sent anywhere -- canned sample results are used.
    sample_mode: bool
    oci_region: str | None
    original_photos_stored: bool = False


@router.get("/privacy/info", response_model=PrivacyInfo)
def privacy_info() -> PrivacyInfo:
    """Which processors handle an upload right now (no sign-in needed)."""
    sample = is_mock_mode()
    return PrivacyInfo(sample_mode=sample, oci_region=None if sample else os.getenv("OCI_REGION") or None)


class DeleteIn(BaseModel):
    # Must be true: a deliberate confirmation, not an accidental call.
    confirm: bool


class DeletedOut(BaseModel):
    letters: int
    reminders: int
    profile: int
    applications: int
    sessions: int


@router.post("/me/delete-data", response_model=DeletedOut)
def delete_my_data(
    body: DeleteIn, auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
):
    """Delete everything saved for the signed-in user (and only them):
    letters' saved facts, the profile built from letters and answers,
    reminders, applications (drafts and sent, including signatures), and
    sign-in sessions/codes. Backups made outside the app aren't reached."""
    if body.confirm is not True:
        return JSONResponse(
            status_code=422, content={"detail": "Please confirm.", "detail_zh": "请先确认。"}
        )

    user_id, phone = auth.user_id, auth.phone

    def count_and_delete(model, condition) -> int:
        n = len(session.exec(select(model).where(condition)).all())
        session.exec(delete(model).where(condition))
        return n

    result = DeletedOut(
        reminders=count_and_delete(Reminder, Reminder.user_id == user_id),
        letters=count_and_delete(LetterRecord, LetterRecord.user_id == user_id),
        profile=count_and_delete(ProfileRecord, ProfileRecord.user_id == user_id),
        applications=count_and_delete(ApplicationRecord, ApplicationRecord.user_id == user_id),
        sessions=count_and_delete(AuthSession, AuthSession.user_id == user_id),
    )
    count_and_delete(OtpChallenge, OtpChallenge.phone == phone)
    session.commit()
    return result
