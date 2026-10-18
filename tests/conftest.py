import os

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("DEMO_MODE", "true")
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


class _Combined:
    """Response-like result of read + confirm: the confirm response, with the
    read step's trace (confirm does no OCI work of its own)."""

    def __init__(self, response, extra: dict | None = None):
        self.status_code = response.status_code
        self._body = response.json()
        if extra:
            self._body.update(extra)

    def json(self):
        return self._body


def upload_letter(client, filename: str, headers: dict, language: str = "en", save_identifiers: bool = True):
    """Scan a letter the way the app now does: read it (nothing saved), then
    confirm the facts as read. Returns the confirm response (or the failed
    read response)."""
    import io

    read = client.post(
        "/letters/read",
        files={"file": (filename, io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        data={"language": language},
        headers=headers,
    )
    if read.status_code != 200:
        return read
    draft = read.json()
    confirm = client.post(
        "/letters/confirm",
        json={
            "draft_token": draft["draft_token"],
            "facts": {**draft["facts"], **draft["identifiers"]},
            "save_identifiers": save_identifiers,
            "language": language,
        },
        headers=headers,
    )
    if confirm.status_code != 200:
        return confirm
    return _Combined(confirm, {"trace": draft["trace"]})
