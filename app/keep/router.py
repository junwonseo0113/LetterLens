from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import current_user
from app.db import get_session
from app.models import AuthSession

from .msp_checklist import MspChecklistOut, check_msp_checklist
from .reminders import list_reminders
from .schemas import ReminderOut

router = APIRouter()


@router.get("/reminders", response_model=list[ReminderOut])
def get_reminders(
    auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
) -> list[ReminderOut]:
    return list_reminders(session, auth.user_id)


@router.get("/msp-checklist", response_model=MspChecklistOut)
def get_msp_checklist(
    auth: AuthSession = Depends(current_user), session: Session = Depends(get_session)
) -> MspChecklistOut:
    return check_msp_checklist(session, auth.user_id)
