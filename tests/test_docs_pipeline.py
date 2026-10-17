import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.db import engine
from app.main import app

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


def test_ssa_benefit_letter_extraction_and_profile_merge():
    response = _upload("ssa_sample.jpg")
    assert response.status_code == 200
    body = response.json()

    assert body["letter_type"] == "ssa_benefit_letter"
    assert body["extracted_fields"]["gross_monthly_benefit"] == 1700.0
    assert body["extracted_fields"]["part_b_deduction"] == 202.9
    assert "ss_gross_monthly" in body["profile_fields_updated"]
    assert body["deadline"] is None
    assert body["explanation"]


def test_bank_statement_sets_savings():
    response = _upload("bank_sample.jpg")
    body = response.json()

    assert body["letter_type"] == "bank_statement"
    assert body["extracted_fields"]["ending_balance"] == 40000.0
    assert "savings" in body["profile_fields_updated"]


def test_hra_renewal_notice_has_deadline_and_action_item():
    response = _upload("hra_sample.jpg")
    body = response.json()

    assert body["letter_type"] == "hra_renewal_notice"
    assert body["deadline"] == "2026-11-15"
    assert any("2026-11-15" in item for item in body["action_items"])


def test_medical_bill_line_items():
    response = _upload("bill_sample.jpg")
    body = response.json()

    assert body["letter_type"] == "medical_bill"
    assert body["extracted_fields"]["is_medicare_claim"] is True
    assert body["extracted_fields"]["line_items"][0]["category"] == "copay"


def test_unknown_document_falls_back_to_other():
    response = _upload("mystery_sample.jpg")
    body = response.json()

    assert body["letter_type"] == "other"
    assert body["profile_fields_updated"] == []


def test_bank_deposit_does_not_override_documented_ss_income():
    _upload("ssa_sample.jpg")
    response = _upload("bank_sample.jpg")
    body = response.json()

    assert "bank_deposit_monthly" not in body["profile_fields_updated"]


def test_no_raw_image_bytes_persisted():
    response = _upload("ssa_sample.jpg")
    body = response.json()

    assert "fake-image-bytes" not in str(body["extracted_fields"])


def test_list_letters_returns_uploads_newest_first():
    _upload("ssa_sample.jpg")
    _upload("bank_sample.jpg")

    response = client.get("/letters", params={"user_id": "demo"})
    body = response.json()

    assert len(body) == 2
    assert body[0]["letter_type"] == "bank_statement"
    assert body[1]["letter_type"] == "ssa_benefit_letter"


def test_list_letters_scoped_to_user():
    _upload("ssa_sample.jpg", user_id="alice")
    _upload("bank_sample.jpg", user_id="bob")

    response = client.get("/letters", params={"user_id": "alice"})
    body = response.json()

    assert len(body) == 1
    assert body[0]["letter_type"] == "ssa_benefit_letter"
