"""Resets demo state: wipes the demo SQLite DB and recreates empty tables.

Run with: python demo/seed.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEMO_DB_PATH = Path(__file__).resolve().parent / "demo_letterlens.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DB_PATH}"
os.environ.setdefault("MOCK_MODE", "true")

from sqlmodel import SQLModel  # noqa: E402

from app.db import engine, init_db  # noqa: E402


def main() -> None:
    SQLModel.metadata.drop_all(engine)
    init_db()
    print(f"Demo database reset at {DEMO_DB_PATH}")


if __name__ == "__main__":
    main()
