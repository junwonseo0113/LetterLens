"""End-to-end demo script for the hackathon persona: Kim Soon-ja, 74,
Flushing, Queens NY. Drives the full upload -> FIND -> KEEP -> PROTECT
flow against the real FastAPI app in MOCK_MODE (fully offline), using the
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

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ProfileRecord  # noqa: E402

USER_ID = "kim_soonja"
LANGUAGE = "ko"

INTAKE_LETTERS = [
    ("ssa_benefit_letter_sample.jpg", "SSA benefit letter"),
    ("bank_statement_sample.jpg", "Bank statement"),
    ("hra_snap_renewal_notice_sample.jpg", "HRA SNAP renewal notice"),
]
BILL_LETTER = ("medical_bill_sample.jpg", "Medical bill")


def _upload(client: TestClient, filename: str, label: str) -> dict:
    path = DEMO_DIR / filename
    with open(path, "rb") as f:
        response = client.post(
            "/letters",
            files={"file": (filename, f, "image/jpeg")},
            data={"language": LANGUAGE, "user_id": USER_ID},
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
    print("LetterLens demo -- persona: Kim Soon-ja, 74, Flushing, Queens NY")
    print("=" * 70)

    with TestClient(app) as client:
        for filename, label in INTAKE_LETTERS:
            _upload(client, filename, label)

        # Age isn't extracted from any letter type yet (no fixture
        # documents it) -- set it directly so the FIND step below reflects
        # the persona's real age. We also simulate that she successfully
        # enrolled in QMB after an earlier FIND pass, so the PROTECT
        # illegal-billing flow has something real to flag in this walkthrough.
        with Session(engine) as session:
            profile = session.get(ProfileRecord, USER_ID)
            profile.age = 74
            profile.on_qmb = True
            session.add(profile)
            session.commit()
        print(
            "\n(Demo note: set age=74 and on_qmb=True directly in the DB -- no letter "
            "type extracts age yet, and we're simulating a prior successful QMB "
            "enrollment so PROTECT has something to flag below.)"
        )

        _upload(client, *BILL_LETTER)

        print("\n--- KEEP: upcoming deadlines ---")
        reminders = client.get("/reminders", params={"user_id": USER_ID}).json()
        for r in reminders:
            print(
                f"{r['program']}: due {r['deadline']} "
                f"({r['days_until_deadline']} days, overdue={r['overdue']})"
            )
            print(f"  Checklist: {r['checklist']}")

        print("\n--- FIND: benefits found ---")
        benefits = client.get("/benefits", params={"user_id": USER_ID, "language": LANGUAGE}).json()
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

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    status = "OK" if elapsed <= 180 else "SLOW"
    print(f"Demo completed in {elapsed:.1f}s ({status} -- target is under 3 minutes)")
    print("=" * 70)


if __name__ == "__main__":
    main()
