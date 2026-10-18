import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.apply.normalize import FieldValueError, normalize
from app.db import engine
from app.main import app
from tests.conftest import auth_headers

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


def _upload(filename: str, headers: dict):
    response = client.post(
        "/letters",
        files={"file": (filename, io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        data={"language": "zh"},
        headers=headers,
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
    response = client.post("/auth/request-code", json={"phone": "12345"})
    assert response.status_code == 422
    assert response.json()["detail_zh"] == "请输入10位数的美国电话号码。"


def test_code_requests_are_rate_limited():
    for _ in range(5):
        assert client.post("/auth/request-code", json={"phone": "7185550142"}).status_code == 200
    assert client.post("/auth/request-code", json={"phone": "7185550142"}).status_code == 429


def test_sign_out_revokes_the_session():
    headers, _ = _sign_in()
    assert client.post("/auth/sign-out", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected():
    from datetime import datetime, timedelta, timezone

    from sqlmodel import Session

    from app.models import AuthSession

    headers, _ = _sign_in()
    token = headers["Authorization"].removeprefix("Bearer ")
    with Session(engine) as session:
        auth = session.get(AuthSession, token)
        auth.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        session.add(auth)
        session.commit()
    assert client.get("/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/letters"),
        ("get", "/benefits"),
        ("get", "/reminders"),
        ("get", "/msp-checklist"),
        ("get", "/profile/on-qmb"),
        ("post", "/profile/on-qmb?on_qmb=true"),
    ],
)
def test_personal_endpoints_require_sign_in(method, path):
    assert getattr(client, method)(path).status_code == 401
    # A user_id parameter no longer lets you read someone else's data.
    assert getattr(client, method)(path + ("&" if "?" in path else "?") + "user_id=demo").status_code == 401


def test_upload_requires_sign_in():
    response = client.post(
        "/letters",
        files={"file": ("ssa.jpg", io.BytesIO(b"x"), "image/jpeg")},
        data={"language": "en", "user_id": "demo"},
    )
    assert response.status_code == 401


def test_users_only_see_their_own_letters():
    alice, _ = _sign_in("7185550142")
    bob, _ = _sign_in("6465550199")
    _upload("ssa_benefit_letter_sample.jpg", alice)
    assert len(client.get("/letters", headers=alice).json()) == 1
    assert client.get("/letters", headers=bob).json() == []


# --- pre-fill + interview ----------------------------------------------------


def test_application_prefills_from_letters_and_sign_in():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)

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
    headers, _ = _sign_in()
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    client.put(f"/applications/{app_id}/fields/full_name", json={"value": "陈玉兰"}, headers=headers)

    _upload("ssa_benefit_letter_sample.jpg", headers)
    body = client.post("/applications", json={"program": "MSP"}, headers=headers).json()
    fields = {f["key"]: f for f in body["fields"]}

    assert body["id"] == app_id
    assert fields["full_name"]["value"] == "陈玉兰"  # the user's answer wins
    assert fields["home_address"]["source"] == "ssa_benefit_letter"


def test_spoken_chinese_answers_are_normalized():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]

    body = _answer_remaining(headers, app_id)
    fields = {f["key"]: f["value"] for f in body["fields"]}

    assert fields["date_of_birth"] == "1952-03-05"
    assert fields["medicare_number"] == "1EG4TE5MK73"
    assert fields["married"] == "no"
    assert fields["household_size"] == "1"
    assert fields["monthly_work_income"] == "0"
    assert body["next_question"] is None


def test_answers_update_the_eligibility_profile():
    from sqlmodel import Session

    from app.models import ProfileRecord

    headers, user_id = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)
    client.put(f"/applications/{app_id}/fields/household_size", json={"value": "2"}, headers=headers)

    with Session(engine) as session:
        profile = session.get(ProfileRecord, user_id)
        assert profile.age >= 74  # born 1952-03-05
        assert profile.married is False
        assert profile.household_size == 2
        assert profile.earned_income_monthly == 0
        assert profile.ss_gross_monthly == 1700  # from the letter, untouched

    # A household of 2 that isn't a couple: the other person's income is
    # now a missing fact, asked rather than assumed to be $0.
    snap = next(
        r for r in client.get("/benefits", headers=headers).json()["results"] if r["program"] == "SNAP"
    )
    assert snap["missing_fields"] == ["other_household_income_monthly"]
    client.post("/profile/answers", json={"key": "other_household_income_monthly", "value": "0"}, headers=headers)

    snap = next(
        r for r in client.get("/benefits", headers=headers).json()["results"] if r["program"] == "SNAP"
    )
    assert snap["status"] == "likely"


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
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
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
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)

    body = client.post(
        f"/applications/{app_id}/submit", json={"signature_png": SIGNATURE, "confirmed": True}, headers=headers
    ).json()
    assert body["status"] == "needs_review"
    assert set(body["missing_documents"]) == set(OTHER_DOCS)
    # Income was read from the SSA letter -- evidence, but nobody has checked it.
    assert body["unverified_documents"] == ["proof_of_income"]
    assert set(body["review_reason"]) == set(OTHER_DOCS) | {"proof_of_income"}
    assert body["confirmation_number"] is None

    assert client.get("/review-queue").status_code == 401
    queue = client.get("/review-queue", headers=CASEWORKER).json()
    assert [a["id"] for a in queue] == [app_id]

    approved = client.post(
        f"/review-queue/{app_id}/approve",
        json={"note": "Saw documents in person", "verified_documents": ["proof_of_income", "medicare_card"]},
        headers=CASEWORKER,
    ).json()
    assert approved["status"] == "submitted"
    assert approved["confirmation_number"].startswith("MSP-")
    statuses = {d["key"]: d["status"] for d in approved["documents"]}
    assert statuses["proof_of_income"] == "verified"
    assert statuses["medicare_card"] == "verified"
    assert statuses["social_security_card"] == "missing"  # only what the caseworker saw
    assert client.get("/review-queue", headers=CASEWORKER).json() == []


def test_caseworker_request_info_lets_user_fix_and_resubmit():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
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
    # Photos are "uploaded", not verified: they're discarded, so a
    # caseworker still has to see the originals.
    assert resubmitted["status"] == "needs_review"
    assert resubmitted["simulated"] is True
    assert resubmitted["missing_documents"] == []
    assert set(resubmitted["unverified_documents"]) == set(OTHER_DOCS) | {"proof_of_income"}
    statuses = {d["key"]: d["status"] for d in resubmitted["documents"]}
    assert statuses["medicare_card"] == "uploaded"
    assert statuses["proof_of_income"] == "from_letter"


def test_caseworker_cannot_verify_unknown_documents():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    _answer_remaining(headers, app_id)
    client.post(f"/applications/{app_id}/submit", json={"signature_png": SIGNATURE, "confirmed": True}, headers=headers)
    response = client.post(
        f"/review-queue/{app_id}/approve", json={"verified_documents": ["passport"]}, headers=CASEWORKER
    )
    assert response.status_code == 422


def test_submitted_application_is_locked():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
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
    assert body["status"] == "needs_review"
    response = client.put(f"/applications/{app_id}/fields/full_name", json={"value": "x"}, headers=headers)
    assert response.status_code == 409  # locked while a caseworker reviews

    verified = OTHER_DOCS + ["proof_of_income"]
    body = client.post(
        f"/review-queue/{app_id}/approve", json={"verified_documents": verified}, headers=CASEWORKER
    ).json()
    assert body["status"] == "submitted"
    assert body["unverified_documents"] == []

    response = client.put(f"/applications/{app_id}/fields/full_name", json={"value": "x"}, headers=headers)
    assert response.status_code == 409


# --- Chinese demo path (offline mocks) -------------------------------------------


def test_chinese_letter_explanation_keeps_exact_numbers():
    body = _upload("ssa_benefit_letter_sample.jpg", auth_headers("chen")).json()
    assert "社会安全局" in body["explanation"]
    assert "$1,700.00" in body["explanation"]
    assert "MOCK_MODE" not in body["explanation"]


def _answer_basics(headers: dict) -> None:
    """Answer the facts no sample letter contains: single, no work income, lives alone."""
    for key, value in [("earned_income_monthly", "0"), ("married", "no"), ("household_size", "1")]:
        assert client.post("/profile/answers", json={"key": key, "value": value}, headers=headers).status_code == 200


def test_chinese_benefits_explanations():
    _upload("ssa_benefit_letter_sample.jpg", auth_headers("chen"))
    _answer_basics(auth_headers("chen"))
    results = client.get("/benefits", params={"language": "zh"}, headers=auth_headers("chen")).json()["results"]
    assert results
    assert all("MOCK_MODE" not in r["explanation"] for r in results)
    assert any("您很可能符合" in r["explanation"] for r in results)


def test_every_rule_has_matching_chinese_with_the_same_numbers():
    import re

    from app.rules.engine import Profile, evaluate

    profiles = [
        Profile(has_medicare=True, ss_gross_monthly=1700, savings=40000, age=74),
        Profile(has_medicare=True, ss_gross_monthly=2300, age=70),
        Profile(has_medicare=True, ss_gross_monthly=5000, age=70),
        Profile(has_medicare=True, ss_gross_monthly=1790, age=62),
        Profile(has_medicare=False, ss_gross_monthly=1000),
        Profile(nyc_resident=False),
        Profile(has_medicare=True, on_medicaid=True, ss_gross_monthly=900),
        Profile(has_medicare=True, married=True, ss_gross_monthly=1200, ss_gross_monthly_spouse=900),
    ]
    money = re.compile(r"\$[\d,]+\.\d{2}")
    for profile in profiles:
        for result in evaluate(profile):
            assert result.rule_applied_zh, result.rule_applied
            assert money.findall(result.rule_applied) == money.findall(result.rule_applied_zh), result.rule_applied
            assert len(result.warnings) == len(result.warnings_zh)


def test_benefits_in_chinese_are_fully_chinese_with_english_rule_kept():
    _upload("ssa_benefit_letter_sample.jpg", auth_headers("chen"))
    _upload("bank_statement_sample.jpg", auth_headers("chen"))
    _answer_basics(auth_headers("chen"))
    results = client.get("/benefits", params={"language": "zh"}, headers=auth_headers("chen")).json()["results"]
    qmb = next(r for r in results if r["program"] == "QMB")
    assert "可计算收入" in qmb["rule_applied"]
    assert qmb["rule_applied_en"].startswith("Countable income")
    assert qmb["disclaimer"].startswith("最终决定")
    assert any("存款不会影响" in line for line in qmb["myth_busting_lines"])


def test_chinese_letter_action_items():
    body = _upload("hra_snap_renewal_notice_sample.jpg", auth_headers("chen")).json()
    assert body["action_items"] == ["请在 2026-11-15 之前提交：收入证明、居住证明、身份证明"]
    assert "收入证明、居住证明、身份证明" in body["explanation"]


def test_viewing_my_application_does_not_start_one():
    headers, _ = _sign_in()
    assert client.get("/applications/current", headers=headers).json() is None
    assert client.get("/applications/current", headers=headers).json() is None  # still nothing created
    app_id = client.post("/applications", json={"program": "MSP"}, headers=headers).json()["id"]
    assert client.get("/applications/current", headers=headers).json()["id"] == app_id
    assert client.get("/applications/current").status_code == 401


def test_answers_given_on_benefits_page_prefill_the_application():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    for key, value in [("married", "no"), ("household_size", "1"), ("earned_income_monthly", "0")]:
        client.post("/profile/answers", json={"key": key, "value": value}, headers=headers)
    body = client.post("/applications", json={"program": "MSP"}, headers=headers).json()
    fields = {f["key"]: f for f in body["fields"]}
    assert fields["married"]["value"] == "no" and fields["married"]["source"] == "you"
    assert fields["household_size"]["value"] == "1"
    assert fields["monthly_work_income"]["value"] == "0"
    # Never answered anywhere: still asked, not defaulted.
    assert fields["date_of_birth"]["value"] is None


def test_profile_defaults_never_prefill_the_application():
    headers, _ = _sign_in()
    _upload("ssa_benefit_letter_sample.jpg", headers)
    body = client.post("/applications", json={"program": "MSP"}, headers=headers).json()
    fields = {f["key"]: f for f in body["fields"]}
    assert fields["married"]["value"] is None  # default False is not an answer
    assert fields["household_size"]["value"] is None  # default 1 is not an answer
