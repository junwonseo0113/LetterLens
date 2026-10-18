"""Resets the demo DB straight to a given moment in the Mei-ling Chen
story (demo/fixtures/SPEC.md), so a presenter can jump to KEEP or
PROTECT without re-uploading earlier letters live on stage, or recover
instantly if something goes wrong mid-demo.

Calls the real pipeline functions directly (no HTTP, no auth token
needed) with MOCK_MODE=true, so this never touches real OCI.

Run with:
    python scripts/seed_demo.py --step find      # fixtures 1-2
    python scripts/seed_demo.py --step keep      # + fixture 3
    python scripts/seed_demo.py --step protect   # + QMB active, fixture 4
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEMO_DB_PATH = REPO_ROOT / "demo" / "demo_letterlens.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DB_PATH}"
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("DEMO_MODE", "true")

from sqlmodel import SQLModel, Session  # noqa: E402

from app.auth.service import user_id_for_phone  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.benefits.service import save_answer  # noqa: E402
from app.docs.pipeline import confirm_letter, read_letter  # noqa: E402
from app.models import ProfileRecord  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "demo" / "fixtures"
# user_id is always derived from the signed-in phone number (see
# app.auth.service.user_id_for_phone) -- never an arbitrary string, so a
# presenter can actually sign in and see this seeded data. Dial this
# number at the sign-in screen; MOCK_MODE shows the OTP on screen.
DEMO_PHONE = "7185550100"
USER_ID = user_id_for_phone(DEMO_PHONE)
LANGUAGE = "zh"

STEPS = ["find", "keep", "protect"]


def _upload(session: Session, filename: str) -> None:
    image_bytes = (FIXTURES_DIR / filename).read_bytes()
    # The app's two steps: read (saves nothing), then confirm the facts as read
    # -- including name/address, as a presenter would tick "use for my application".
    draft = read_letter(session=session, image=image_bytes, filename=filename, language=LANGUAGE, user_id=USER_ID)
    confirm_letter(
        session=session,
        user_id=USER_ID,
        draft_token=draft.draft_token,
        facts={**draft.facts, **draft.identifiers},
        save_identifiers=True,
        language=LANGUAGE,
    )
    print(f"  uploaded {filename}")


def seed(step: str) -> None:
    if step not in STEPS:
        raise SystemExit(f"--step must be one of {STEPS}, got {step!r}")

    SQLModel.metadata.drop_all(engine)
    init_db()
    print(f"Demo database reset at {DEMO_DB_PATH}")

    with Session(engine) as session:
        # FIND: SSA benefit letter + bank statement.
        _upload(session, "01_ssa_benefit_letter.png")
        _upload(session, "02_bank_statement.png")

        # The two facts no letter in this story contains: Mei-ling lives
        # alone with no work income.
        save_answer(session, USER_ID, "earned_income_monthly", "0")
        save_answer(session, USER_ID, "married", "no")
        print("  answered: earned_income_monthly=0, married=no")

        if step in ("keep", "protect"):
            _upload(session, "03_hra_snap_recert_notice.png")

        if step == "protect":
            profile = session.get(ProfileRecord, USER_ID) or ProfileRecord(user_id=USER_ID)
            profile.on_qmb = True
            session.add(profile)
            session.commit()
            print("  set on_qmb=True (QMB approved, per the PROTECT moment's timeline)")
            _upload(session, "04_clinic_bill.png")

    print(f"\nSeeded through '{step}'. Sign in with phone {DEMO_PHONE} (demo OTP shown on screen).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", required=True, choices=STEPS)
    args = parser.parse_args()
    seed(args.step)


if __name__ == "__main__":
    main()
