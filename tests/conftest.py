import os

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_letterlens.db")


def auth_headers(user_id: str = "demo") -> dict:
    """Signed-in headers for `user_id`, without going through the phone-code
    flow (tests/test_apply.py covers that). Safe to call after a DB reset."""
    from sqlmodel import Session

    from app.db import engine
    from app.models import AuthSession

    token = f"test-token-{user_id}"
    with Session(engine) as session:
        session.merge(AuthSession(token=token, user_id=user_id, phone="0000000000"))
        session.commit()
    return {"Authorization": f"Bearer {token}"}
