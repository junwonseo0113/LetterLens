import io

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from sqlmodel import Session, SQLModel

from app.db import engine
from app.main import app
from app.models import ProfileRecord

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
        data={"language": language},
        headers=auth_headers(user_id),
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


def test_upload_trace_shows_ocr_and_genai_steps_in_order():
    response = _upload("ssa_sample.jpg")
    trace = response.json()["trace"]

    assert [s["name"] for s in trace] == [
        "Read the letter",
        "Identified the letter type",
        "Extracted the details",
        "Explained it in your language",
    ]
    assert trace[0]["service"] == "OCI Document Understanding (mock)"
    assert all(s["service"] == "OCI Generative AI (mock)" for s in trace[1:])
    assert all(s["success"] is True for s in trace)
    assert all(s["duration_ms"] >= 0 for s in trace)
    assert all(s["offline"] is True for s in trace)


def test_real_read_failure_saves_nothing_and_offers_retry(monkeypatch):
    # Outside MOCK_MODE a failed OCR must NOT fall back to the canned
    # sample letter (whose $1,700 would be saved into a real profile).
    from app.docs import oci_client

    def ocr_down(image_bytes):
        raise RuntimeError("OCI Document Understanding unreachable")

    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setattr(oci_client, "_real_ocr", ocr_down)
    response = _upload("ssa_sample.jpg")

    assert response.status_code == 502
    body = response.json()
    assert body["retryable"] is True
    assert "Nothing was saved" in body["detail"]
    assert body["detail_zh"]

    monkeypatch.setenv("MOCK_MODE", "true")
    assert client.get("/letters", headers=auth_headers("demo")).json() == []
    with Session(engine) as session:
        profile = session.get(ProfileRecord, "demo")
        assert profile is None or profile.ss_gross_monthly is None


def test_real_letter_is_not_sample_and_explanation_may_use_template(monkeypatch):
    from app.docs import oci_client

    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setattr(oci_client, "_real_ocr", lambda b: oci_client._mock_ocr("ssa.jpg"))
    monkeypatch.setattr(oci_client, "_real_classify", oci_client._mock_classify)
    monkeypatch.setattr(oci_client, "_real_extract", lambda t, text, kv, retry: oci_client._mock_extract(t, text))

    def explain_down(*args):
        raise RuntimeError("GenAI down")

    monkeypatch.setattr(oci_client, "_real_explain", explain_down)
    body = _upload("photo.jpg").json()

    assert body["is_sample"] is False
    assert body["extracted_fields"]["gross_monthly_benefit"] == 1700.0
    steps = {s["name"]: s for s in body["trace"]}
    assert steps["Read the letter"]["offline"] is False
    assert steps["Explained it in your language"]["offline"] is True  # template from the real fields


def test_mock_mode_letters_are_labeled_sample():
    body = _upload("ssa_sample.jpg").json()
    assert body["is_sample"] is True
    assert client.get("/letters", headers=auth_headers("demo")).json()[0]["is_sample"] is True

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

    response = client.get("/letters", headers=auth_headers("demo"))
    body = response.json()

    assert len(body) == 2
    assert body[0]["letter_type"] == "bank_statement"
    assert body[1]["letter_type"] == "ssa_benefit_letter"


def test_list_letters_scoped_to_user():
    _upload("ssa_sample.jpg", user_id="alice")
    _upload("bank_sample.jpg", user_id="bob")

    response = client.get("/letters", headers=auth_headers("alice"))
    body = response.json()

    assert len(body) == 1
    assert body[0]["letter_type"] == "ssa_benefit_letter"


# --- reopening saved letters ------------------------------------------------


def test_owner_can_reopen_a_letter_with_everything_shown_at_upload():
    uploaded = _upload("hra_sample.jpg", user_id="alice").json()
    reopened = client.get(f"/letters/{uploaded['letter_id']}", headers=auth_headers("alice")).json()

    assert reopened["letter_type"] == "hra_renewal_notice"
    assert reopened["explanation"] == uploaded["explanation"]
    assert reopened["action_items"] == uploaded["action_items"]
    assert reopened["deadline"] == "2026-11-15"
    assert reopened["reminder"]["deadline"] == "2026-11-15"
    assert reopened["extracted_fields"]["required_documents"] == ["proof of income", "proof of residence", "ID"]
    assert reopened["is_sample"] is True


def test_reopening_in_another_language_rebuilds_the_text():
    uploaded = _upload("hra_sample.jpg", language="en", user_id="alice").json()
    zh = client.get(
        f"/letters/{uploaded['letter_id']}", params={"language": "zh"}, headers=auth_headers("alice")
    ).json()
    assert "续期" in zh["explanation"]
    assert zh["action_items"] == ["请在 2026-11-15 之前提交：收入证明、居住证明、身份证明"]


def test_users_cannot_open_each_others_letters():
    letter_id = _upload("ssa_sample.jpg", user_id="alice").json()["letter_id"]
    assert client.get(f"/letters/{letter_id}", headers=auth_headers("bob")).status_code == 404
    assert client.get(f"/letters/{letter_id}").status_code == 401
    assert client.get("/letters/99999", headers=auth_headers("alice")).status_code == 404
