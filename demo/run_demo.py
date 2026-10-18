"""End-to-end demo script for the hackathon persona: Chen Yu-lan (陈玉兰), 74,
Flushing, Queens NY, Mandarin speaker. Drives the full sign-in -> upload ->
FIND -> APPLY -> KEEP -> PROTECT flow against the real FastAPI app in MOCK_MODE (fully offline), using the
sample letters in this directory. No server needs to be running.

Run with: python demo/run_demo.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DIR / 'demo_letterlens.db'}"
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("DEMO_MODE", "true")

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

PHONE = "718-555-0142"
LANGUAGE = "zh"
SIGNATURE = "data:image/png;base64,iVBORw0KGgo="
# What she says out loud during the interview (browser speech -> text).
SPOKEN_ANSWERS = {
    "date_of_birth": "一九五二年三月五日",
    "medicare_number": "1EG4-TE5-MK73",
    "married": "没有，我丈夫去世了",
    "household_size": "一个人",
    "monthly_work_income": "没有",
}

INTAKE_LETTERS = [
    ("ssa_benefit_letter_sample.jpg", "SSA benefit letter"),
    ("bank_statement_sample.jpg", "Bank statement"),
    ("hra_snap_renewal_notice_sample.jpg", "HRA SNAP renewal notice"),
]
BILL_LETTER = ("medical_bill_sample.jpg", "Medical bill")


def _upload(client: TestClient, auth: dict, filename: str, label: str) -> dict:
    path = DEMO_DIR / filename
    with open(path, "rb") as f:
        response = client.post(
            "/letters",
            files={"file": (filename, f, "image/jpeg")},
            data={"language": LANGUAGE},
            headers=auth,
        )
    response.raise_for_status()
    body = response.json()

    print(f"\n--- {label} ({filename}) ---")
    print(f"Classified as: {body['letter_type']}")
    print(f"Explanation: {body['explanation']}")
    print(f"Action items: {body['action_items']}")
    if body.get("deadline"):
        print(f"Deadline: {body['deadline']}")
    if body.get("reminder"):
        print(f"Reminder created: {body['reminder']}")
    if body.get("bill_check"):
        print(f"Bill check: {body['bill_check']}")
    return body


def main() -> None:
    start = time.time()

    print("=" * 70)
    print("LetterLens demo -- persona: Chen Yu-lan (陈玉兰), 74, Flushing, Queens NY")
    print("=" * 70)

    # Start clean so the walkthrough is identical every run.
    SQLModel.metadata.drop_all(engine)

    with TestClient(app) as client:
        print("\n--- Sign in with a phone code ---")
        code = client.post("/auth/request-code", json={"phone": PHONE}).json()["demo_code"]
        session_out = client.post("/auth/verify", json={"phone": PHONE, "code": code}).json()
        user_id = session_out["user_id"]
        auth = {"Authorization": f"Bearer {session_out['token']}"}
        print(f"Code {code} verified -> signed in as {user_id}")

        for filename, label in INTAKE_LETTERS:
            _upload(client, auth, filename, label)

        # No sample letter states these facts, so she answers the app's
        # "More information needed" questions -- unknown facts are asked,
        # never assumed. Then we simulate that she enrolled in QMB after an
        # earlier FIND pass, so PROTECT has something real to flag below.
        print("\n--- More information needed: she answers the app's questions ---")
        for key, value in [("earned_income_monthly", "没有"), ("married", "没有"),
                           ("household_size", "一个人"), ("age", "74")]:
            client.post("/profile/answers", json={"key": key, "value": value}, headers=auth).raise_for_status()
            print(f"  {key}: {value!r}")
        client.post("/profile/on-qmb", params={"on_qmb": True}, headers=auth).raise_for_status()
        print("  (Demo: QMB enrollment switched on, so the medical bill below gets checked.)")

        _upload(client, auth, *BILL_LETTER)

        print("\n--- KEEP: upcoming deadlines ---")
        reminders = client.get("/reminders", headers=auth).json()
        for r in reminders:
            print(
                f"{r['program']}: due {r['deadline']} "
                f"({r['days_until_deadline']} days, overdue={r['overdue']})"
            )
            print(f"  Checklist: {r['checklist']}")

        print("\n--- FIND: benefits found ---")
        benefits = client.get("/benefits", params={"language": LANGUAGE}, headers=auth).json()["results"]
        for b in benefits:
            print(f"\n{b['program']}: {b['status']} (confidence={b['confidence']})")
            print(f"  Monthly value: ${b['monthly_value']:,.2f}  Annual: ${b['annual_value']:,.2f}")
            print(f"  Rule applied: {b['rule_applied']}")
            print(f"  Numbers used: {b['numbers_used']}")
            print(f"  Explanation: {b['explanation']}")
            if b["myth_busting_lines"]:
                print(f"  Myth-busting: {b['myth_busting_lines']}")
            if b["warnings"]:
                print(f"  Warnings: {b['warnings']}")
            print(f"  {b['disclaimer']}")

        print("\n--- APPLY: MSP + Extra Help, filled in for her ---")
        application = client.post("/applications", json={"program": "MSP"}, headers=auth).json()
        prefilled = [f for f in application["fields"] if f["value"] is not None]
        print(f"Pre-filled {len(prefilled)} of {len(application['fields'])} answers from her letters and sign-in:")
        for f in prefilled:
            print(f"  {f['label_en']}: {f['value']}  (source: {f['source']})")
        while application["next_question"]:
            key = application["next_question"]
            spoken = SPOKEN_ANSWERS[key]
            application = client.put(
                f"/applications/{application['id']}/fields/{key}", json={"value": spoken}, headers=auth
            ).json()
            value = next(f["value"] for f in application["fields"] if f["key"] == key)
            print(f"  Asked {key!r}, she said {spoken!r} -> {value}")

        application = client.post(
            f"/applications/{application['id']}/submit",
            json={"signature_png": SIGNATURE, "confirmed": True},
            headers=auth,
        ).json()
        print(f"She reviewed, signed and said yes -> status: {application['status']}")
        if application["status"] == "needs_review":
            print(f"  Routed to a caseworker; missing documents: {application['review_reason']}")

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    status = "OK" if elapsed <= 180 else "SLOW"
    print(f"Demo completed in {elapsed:.1f}s ({status} -- target is under 3 minutes)")
    print("=" * 70)


if __name__ == "__main__":
    main()
