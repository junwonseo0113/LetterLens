from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session

from .reminders import list_reminders
from .schemas import ReminderOut

router = APIRouter()


@router.get("/reminders", response_model=list[ReminderOut])
def get_reminders(user_id: str = Query("demo"), session: Session = Depends(get_session)) -> list[ReminderOut]:
    return list_reminders(session, user_id)
