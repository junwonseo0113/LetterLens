import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.apply.normalize import FieldValueError, normalize
from app.db import engine
from app.main import app

client = TestClient(app)

SIGNATURE = "data:image/png;base64,iVBORw0KGgo="
CASEWORKER = {"X-Caseworker-Key": "demo-caseworker"}
OTHER_DOCS = ["medicare_card", "proof_of_identity_dob", "proof_of_residence", "social_security_card"]


@pytest.fixture(autouse=True)
def _reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


def _sign_in(phone: str = "718-555-0142") -> tuple[dict, str]:
    code = client.post("/auth/request-code", json={"phone": phone}).json()["demo_code"]
    body = client.post("/auth/verify", json={"phone": phone, "code": code}).json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user_id"]


def _upload(filename: str, user_id: str):
    response = client.post(
        "/letters",
        files={"file": (filename, io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        data={"language": "zh", "user_id": user_id},
    )
    assert response.status_code == 200
    return response


def _answer_remaining(headers: dict, app_id: int) -> dict:
    answers = {
        "date_of_birth": "一九五二年三月五日",
        "medicare_number": "1EG4-TE5-MK73",
        "married": "没有结婚",
        "household_size": "一个人",
        "monthly_work_income": "没有",
    }
    body = None
    for key, value in answers.items():
        response = client.put(f"/applications/{app_id}/fields/{key}", json={"value": value}, headers=headers)
        assert response.status_code == 200, response.json()
        body = response.json()
    return body


# --- sign-in -----------------------------------------------------------------


def test_sign_in_with_code_and_me():
    headers, user_id = _sign_in()
    me = client.get("/auth/me", headers=headers).json()
    assert me == {"user_id": user_id, "phone": "7185550142"}


def test_wrong_code_is_rejected_and_unauthenticated_calls_fail():
    client.post("/auth/request-code", json={"phone": "7185550142"})
    response = client.post("/auth/verify", json={"phone": "7185550142", "code": "000000x"})
    assert response.status_code == 422
    assert client.post("/applications", json={"program": "MSP"}).status_code == 401


def test_bad_phone_number_is_rejected():
    assert client.post("/auth/request-code", json={"phone": "12345"}).status_code == 422


# --- pre-fill + interview ----------------------------------------------------


def test_application_prefills_from_letters_and_sign_in():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)

    body = client.post("/applications", json={"program": "MSP"}, headers=headers).json()
    fields = {f["key"]: f for f in body["fields"]}

    assert body["covers"] == ["MSP", "Extra Help"]
    assert fields["full_name"]["value"] == "Chen, Yu-lan"
    assert fields["full_name"]["source"] == "ssa_benefit_letter"
    assert fields["monthly_social_security"]["value"] == "1700"
    assert fields["phone"]["value"] == "(718) 555-0142"
    assert fields["phone"]["source"] == "sign_in"
    # Not on any letter -- the interview asks for it first.
    assert body["next_question"] == "date_of_birth"


def test_letter_uploaded_after_starting_fills_empty_fields_only():
    headers, user_id = _sign_in()
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    client.put(f"/applications/{app_id}/fields/full_name", json={"value": "陈玉兰"}, headers=headers)

    _upload("ssa_benefit_letter_sample.jpg", user_id)
    body = client.post("/applications", json={"program": "MSP"}, headers=headers).json()
    fields = {f["key"]: f for f in body["fields"]}

    assert body["id"] == app_id
    assert fields["full_name"]["value"] == "陈玉兰"  # the user's answer wins
    assert fields["home_address"]["source"] == "ssa_benefit_letter"


def test_spoken_chinese_answers_are_normalized():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]

    body = _answer_remaining(headers, app_id)
    fields = {f["key"]: f["value"] for f in body["fields"]}

    assert fields["date_of_birth"] == "1952-03-05"
    assert fields["medicare_number"] == "1EG4TE5MK73"
    assert fields["married"] == "no"
    assert fields["household_size"] == "1"
    assert fields["monthly_work_income"] == "0"
    assert body["next_question"] is None


def test_unparseable_answer_returns_bilingual_error():
    headers, _ = _sign_in()
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    response = client.put(
        f"/applications/{app_id}/fields/date_of_birth", json={"value": "我不知道"}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["detail_zh"] == "请说出年、月、日。"


def test_other_users_cannot_read_an_application():
    headers, _ = _sign_in("7185550142")
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    other, _ = _sign_in("6465550199")
    assert client.get(f"/applications/{app_id}", headers=other).status_code == 404


@pytest.mark.parametrize(
    "kind,raw,expected",
    [
        ("date", "03/05/1952", "1952-03-05"),
        ("date", "1952年3月15日", "1952-03-15"),
        ("date", "一九五二年三月十五日", "1952-03-15"),
        ("number", "$1,700.00", "1700"),
        ("number", "一千七百块", "1700"),
        ("number", "两个人", "2"),
        ("yesno", "是的", "yes"),
        ("yesno", "不是", "no"),
        ("yesno", "Yes, married", "yes"),
        ("phone", "1 (718) 555-0142", "(718) 555-0142"),
    ],
)
def test_normalize(kind, raw, expected):
    assert normalize(kind, raw) == expected


def test_normalize_rejects_impossible_date():
    with pytest.raises(FieldValueError):
        normalize("date", "1952年2月30日")


# --- review, sign, submit ----------------------------------------------------


def test_submit_requires_signature_confirmation_and_all_answers():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    url = f"/applications/{app_id}/submit"

    no_answers = client.post(url, json={"signature_png": SIGNATURE, "confirmed": True}, headers=headers)
    assert no_answers.status_code == 422
    assert "Date of birth" in no_answers.json()["detail"]

    _answer_remaining(headers, app_id)
    assert client.post(url, json={"signature_png": SIGNATURE, "confirmed": False}, headers=headers).status_code == 422
    assert client.post(url, json={"signature_png": "", "confirmed": True}, headers=headers).status_code == 422
    status = client.get(f"/applications/{app_id}", headers=headers).json()["status"]
    assert status == "draft"


def test_missing_documents_route_to_caseworker_who_can_approve():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)

    body = client.post(
        f"/applications/{app_id}/submit", json={"signature_png": SIGNATURE, "confirmed": True}, headers=headers
    ).json()
    assert body["status"] == "needs_review"
    assert set(body["review_reason"]) == set(OTHER_DOCS)  # income came from the SSA letter
    assert body["confirmation_number"] is None

    assert client.get("/review-queue").status_code == 401
    queue = client.get("/review-queue", headers=CASEWORKER).json()
    assert [a["id"] for a in queue] == [app_id]

    approved = client.post(f"/review-queue/{app_id}/approve", json={"note": "Saw documents in person"}, headers=CASEWORKER).json()
    assert approved["status"] == "submitted"
    assert approved["confirmation_number"].startswith("MSP-")
    assert client.get("/review-queue", headers=CASEWORKER).json() == []


def test_caseworker_request_info_lets_user_fix_and_resubmit():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)
    submit = {"signature_png": SIGNATURE, "confirmed": True}
    client.post(f"/applications/{app_id}/submit", json=submit, headers=headers)

    body = client.post(
        f"/review-queue/{app_id}/request-info", json={"note": "Please photograph your Medicare card"}, headers=CASEWORKER
    ).json()
    assert body["status"] == "info_requested"
    assert body["reviewer_note"] == "Please photograph your Medicare card"

    for key in OTHER_DOCS:
        response = client.post(
            f"/applications/{app_id}/documents/{key}",
            files={"file": ("card.jpg", io.BytesIO(b"img"), "image/jpeg")},
            headers=headers,
        )
        assert response.status_code == 200

    resubmitted = client.post(f"/applications/{app_id}/submit", json=submit, headers=headers).json()
    assert resubmitted["status"] == "submitted"
    assert resubmitted["simulated"] is True
    assert resubmitted["missing_documents"] == []


def test_submitted_application_is_locked():
    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", user_id)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)
    for key in OTHER_DOCS:
        client.post(
            f"/applications/{app_id}/documents/{key}",
            files={"file": ("doc.jpg", io.BytesIO(b"img"), "image/jpeg")},
            headers=headers,
        )
    body = client.post(
        f"/applications/{app_id}/submit", json={"signature_png": SIGNATURE, "confirmed": True}, headers=headers
    ).json()
    assert body["status"] == "submitted"

    response = client.put(f"/applications/{app_id}/fields/full_name", json={"value": "x"}, headers=headers)
    assert response.status_code == 409


# --- Chinese demo path (offline mocks) -------------------------------------------


def test_chinese_letter_explanation_keeps_exact_numbers():
    body = _upload("ssa_benefit_letter_sample.jpg", "chen").json()
    assert "社会安全局" in body["explanation"]
    assert "$1,700.00" in body["explanation"]
    assert "MOCK_MODE" not in body["explanation"]


def test_chinese_benefits_explanations():
    _upload("ssa_benefit_letter_sample.jpg", "chen")
    results = client.get("/benefits", params={"user_id": "chen", "language": "zh"}).json()["results"]
    assert results
    assert all("MOCK_MODE" not in r["explanation"] for r in results)
    assert any("您很可能符合" in r["explanation"] for r in results)
