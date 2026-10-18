import io
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, upload_letter
from sqlmodel import Session, SQLModel

from app.db import engine
from app.keep.packet import check_packet_readiness
from app.keep.reminders import create_reminder, list_reminders, to_reminder_out
from app.main import app
from app.models import LetterRecord, ProfileRecord, Reminder
from app.protect.bill_check import check_qmb_bill

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


def _upload(filename: str, language: str = "en", user_id: str = "demo"):
    return upload_letter(client, filename, auth_headers(user_id), language)


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
        out = to_reminder_out(session, reminder, today=date(2026, 10, 17))

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
        out = to_reminder_out(session, reminder, today=date(2026, 10, 17))

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

    listed = client.get("/reminders", headers=auth_headers("demo")).json()
    assert len(listed) == 1
    assert listed[0]["program"] == "SNAP"


def test_non_renewal_upload_has_no_reminder():
    response = _upload("ssa_sample.jpg")
    assert response.json()["reminder"] is None


# --- KEEP: document packet readiness ---------------------------------------


def test_packet_readiness_no_letters_uploaded_everything_missing():
    with Session(engine) as session:
        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 11, 15),
            checklist=["proof of income", "proof of residence", "ID"],
        )
        readiness = check_packet_readiness(session, reminder)

    assert readiness.satisfied_count == 0
    assert readiness.total_count == 3
    assert readiness.all_satisfied is False
    assert all(not item.satisfied for item in readiness.items)


def test_packet_readiness_ssa_letter_satisfies_proof_of_income():
    with Session(engine) as session:
        letter = LetterRecord(user_id="demo", letter_type="ssa_benefit_letter", extracted_fields={})
        session.add(letter)
        session.commit()
        session.refresh(letter)

        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 11, 15),
            checklist=["proof of income", "proof of residence", "ID"],
        )
        readiness = check_packet_readiness(session, reminder)

    income_item = next(i for i in readiness.items if i.item == "proof of income")
    residence_item = next(i for i in readiness.items if i.item == "proof of residence")

    assert income_item.satisfied is True
    assert income_item.matched_letter_id == letter.id
    assert income_item.matched_letter_type == "ssa_benefit_letter"
    assert residence_item.satisfied is False
    assert readiness.satisfied_count == 1
    assert readiness.all_satisfied is False


def test_packet_readiness_bank_statement_also_satisfies_income():
    with Session(engine) as session:
        session.add(LetterRecord(user_id="demo", letter_type="bank_statement", extracted_fields={}))
        session.commit()

        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 11, 15),
            checklist=["proof of income"],
        )
        readiness = check_packet_readiness(session, reminder)

    assert readiness.items[0].satisfied is True
    assert readiness.items[0].matched_letter_type == "bank_statement"


def test_packet_readiness_medical_bill_does_not_satisfy_anything():
    with Session(engine) as session:
        session.add(LetterRecord(user_id="demo", letter_type="medical_bill", extracted_fields={}))
        session.commit()

        reminder = create_reminder(
            session,
            user_id="demo",
            letter_id=1,
            program="SNAP",
            deadline=date(2026, 11, 15),
            checklist=["proof of income", "ID"],
        )
        readiness = check_packet_readiness(session, reminder)

    assert readiness.satisfied_count == 0


def test_packet_readiness_via_letters_endpoint():
    _upload("ssa_sample.jpg")
    _upload("hra_sample.jpg")

    listed = client.get("/reminders", headers=auth_headers("demo")).json()
    packet = listed[0]["packet"]

    assert packet["satisfied_count"] == 1
    assert packet["total_count"] == 3
    assert packet["all_satisfied"] is False
    income_item = next(i for i in packet["items"] if i["item"] == "proof of income")
    assert income_item["satisfied"] is True


# --- KEEP: MSP application checklist ----------------------------------------


def test_msp_checklist_no_letters_everything_missing():
    response = client.get("/msp-checklist", headers=auth_headers("demo"))
    body = response.json()

    assert body["decision_notice_days"] == 45
    assert len(body["items"]) == 6
    assert all(item["status"] == "missing" for item in body["items"])


def test_msp_checklist_ssa_letter_satisfies_proof_of_income_only():
    _upload("ssa_sample.jpg")
    response = client.get("/msp-checklist", headers=auth_headers("demo"))
    items = {item["key"]: item["status"] for item in response.json()["items"]}

    assert items["proof_of_income"] == "already_have"
    # Everything else genuinely can't be satisfied by any of this app's
    # letter types -- an SSA benefit letter isn't a Medicare card copy,
    # a birth certificate, or a Social Security card.
    assert items["medicare_card"] == "missing"
    assert items["proof_of_identity_dob"] == "missing"
    assert items["proof_of_residence"] == "missing"
    assert items["social_security_card"] == "missing"
    assert items["signed_application"] == "missing"


def test_msp_checklist_labels_carry_official_english_term_in_korean():
    response = client.get("/msp-checklist", headers=auth_headers("demo"))
    income_item = next(i for i in response.json()["items"] if i["key"] == "proof_of_income")

    assert "소득 증명" in income_item["label_ko"]
    assert "Proof of Income" in income_item["label_ko"]


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


def test_on_qmb_toggle_endpoint_drives_the_bill_flag_live():
    # This is the actual live-demo path: no DB hacking, just the toggle
    # a presenter can hit from the UI before uploading the bill.
    toggle = client.post("/profile/on-qmb", params={"on_qmb": True}, headers=auth_headers("demo"))
    assert toggle.status_code == 200
    assert toggle.json() == {"user_id": "demo", "on_qmb": True}

    response = _upload("bill_sample.jpg")
    assert response.json()["bill_check"]["has_flagged"] is True

    # Toggling back off should stop future bills from being flagged.
    client.post("/profile/on-qmb", params={"on_qmb": False}, headers=auth_headers("demo"))
    response2 = _upload("bill_sample.jpg")
    assert response2.json()["bill_check"]["has_flagged"] is False
