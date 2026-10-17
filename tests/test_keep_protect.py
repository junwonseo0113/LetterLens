import io
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.db import engine
from app.keep.reminders import create_reminder, list_reminders, to_reminder_out
from app.main import app
from app.models import ProfileRecord, Reminder
from app.protect.bill_check import check_qmb_bill

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


def _upload(filename: str, language: str = "en", user_id: str = "demo"):
    return client.post(
        "/letters",
        files={"file": (filename, io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        data={"language": language, "user_id": user_id},
    )


def _set_on_qmb(user_id: str, value: bool) -> None:
    with Session(engine) as session:
        profile = session.get(ProfileRecord, user_id)
        if profile is None:
            profile = ProfileRecord(user_id=user_id)
        profile.on_qmb = value
        session.add(profile)
        session.commit()


# --- KEEP: reminders -------------------------------------------------------


def test_create_and_list_reminder_computes_countdown():
    with Session(engine) as session:
        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 11, 15),
            checklist=["proof of income"],
        )
        out = to_reminder_out(reminder, today=date(2026, 10, 17))

    assert out.days_until_deadline == 29
    assert out.overdue is False


def test_overdue_reminder_flagged():
    with Session(engine) as session:
        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 1, 1),
            checklist=[],
        )
        out = to_reminder_out(reminder, today=date(2026, 10, 17))

    assert out.overdue is True
    assert out.days_until_deadline < 0


def test_list_reminders_sorted_by_deadline():
    with Session(engine) as session:
        create_reminder(
            session, user_id="demo", letter_id=1, program="SNAP", deadline=date(2026, 12, 1), checklist=[]
        )
        create_reminder(
            session, user_id="demo", letter_id=2, program="Extra Help", deadline=date(2026, 11, 1), checklist=[]
        )
        results = list_reminders(session, "demo")

    assert [r.program for r in results] == ["Extra Help", "SNAP"]


def test_hra_upload_creates_reminder_via_pipeline():
    response = _upload("hra_sample.jpg")
    body = response.json()

    assert body["reminder"] is not None
    assert body["reminder"]["program"] == "SNAP"
    assert body["reminder"]["deadline"] == "2026-11-15"
    assert body["reminder"]["checklist"] == ["proof of income", "proof of residence", "ID"]

    listed = client.get("/reminders", params={"user_id": "demo"}).json()
    assert len(listed) == 1
    assert listed[0]["program"] == "SNAP"


def test_non_renewal_upload_has_no_reminder():
    response = _upload("ssa_sample.jpg")
    assert response.json()["reminder"] is None


# --- PROTECT: QMB bill check ------------------------------------------------


def test_qmb_member_medicare_copay_is_flagged():
    result = check_qmb_bill(
        on_qmb=True,
        provider="Queens General Hospital",
        is_medicare_claim=True,
        line_items=[{"description": "Annual wellness visit copay", "amount": 20.0, "category": "copay"}],
    )
    assert result.has_flagged is True
    assert len(result.flagged_line_items) == 1
    assert "QMB" in result.flagged_line_items[0].reason


def test_non_qmb_member_not_flagged():
    result = check_qmb_bill(
        on_qmb=False,
        provider="Queens General Hospital",
        is_medicare_claim=True,
        line_items=[{"description": "Copay", "amount": 20.0, "category": "copay"}],
    )
    assert result.has_flagged is False


def test_non_medicare_claim_not_flagged_even_if_qmb():
    result = check_qmb_bill(
        on_qmb=True,
        provider="Queens General Hospital",
        is_medicare_claim=False,
        line_items=[{"description": "Copay", "amount": 20.0, "category": "copay"}],
    )
    assert result.has_flagged is False


def test_non_cost_sharing_category_not_flagged():
    result = check_qmb_bill(
        on_qmb=True,
        provider="Queens General Hospital",
        is_medicare_claim=True,
        line_items=[{"description": "Parking", "amount": 20.0, "category": "other"}],
    )
    assert result.has_flagged is False


def test_bill_upload_for_qmb_member_flags_and_drafts_dispute_letter():
    _set_on_qmb("demo", True)
    response = _upload("bill_sample.jpg")
    body = response.json()

    assert body["bill_check"]["has_flagged"] is True
    assert body["bill_check"]["flagged_line_items"][0]["amount"] == 20.0
    dispute = body["bill_check"]["dispute_letter"]
    assert dispute is not None
    assert "20.00" in dispute["english"] or "20" in dispute["english"]
    assert dispute["translated"]


def test_bill_upload_for_non_qmb_member_has_no_dispute_letter():
    response = _upload("bill_sample.jpg")
    body = response.json()

    assert body["bill_check"]["has_flagged"] is False
    assert body["bill_check"]["dispute_letter"] is None
