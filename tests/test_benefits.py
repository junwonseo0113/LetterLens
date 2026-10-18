import io

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers
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
        data={"language": language},
        headers=auth_headers(user_id),
    )


def test_benefits_for_user_with_no_letters_returns_no_results():
    # A never-set income field and a confirmed $0 both collapse to 0.0
    # inside the rules engine, so without this guard a brand new user
    # would see "SNAP: likely qualify" before uploading anything --
    # indistinguishable from a verified zero-income household. Until
    # there's at least one letter, there's nothing to evaluate.
    response = client.get("/benefits", headers=auth_headers("nobody"))
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []


def test_benefits_reflects_uploaded_ssa_letter():
    _upload("ssa_sample.jpg")
    response = client.get("/benefits", headers=auth_headers("demo"))
    results = response.json()["results"]

    qmb = next(b for b in results if b["program"] == "QMB")
    extra_help = next(b for b in results if b["program"] == "Extra Help")

    assert qmb["status"] == "likely"
    assert extra_help["status"] == "likely"
    assert qmb["numbers_used"]["countable_income_monthly"] == 1680.0
    assert qmb["explanation"]


def test_benefits_language_param_passed_through():
    _upload("ssa_sample.jpg")
    response = client.get("/benefits", params={"language": "ko"}, headers=auth_headers("demo"))
    results = response.json()["results"]
    assert all("MOCK_MODE" in b["explanation"] for b in results)


def test_benefits_trace_shows_rules_engine_not_ai_for_eligibility():
    _upload("ssa_sample.jpg")
    response = client.get("/benefits", headers=auth_headers("demo"))
    trace = response.json()["trace"]

    step_names = [s["name"] for s in trace]
    assert "Checked eligibility" in step_names

    eligibility_step = next(s for s in trace if s["name"] == "Checked eligibility")
    assert eligibility_step["service"] == "Rules engine (no AI)"
    assert eligibility_step["success"] is True

    explain_step = next(s for s in trace if s["name"] == "Explained each result")
    assert "OCI Generative AI" in explain_step["service"]
