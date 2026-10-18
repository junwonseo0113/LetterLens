"""Demo shortcuts only exist in explicit DEMO_MODE (app/settings.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app import settings
from app.db import engine
from app.main import app

client = TestClient(app)  # no `with`: lifespan (startup checks) tested separately


@pytest.fixture(autouse=True)
def _reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("CASEWORKER_KEY", raising=False)


def test_demo_mode_returns_the_code_and_allows_the_demo_key():
    body = client.post("/auth/request-code", json={"phone": "7185550142"}).json()
    assert body["demo_code"] and len(body["demo_code"]) == 6
    assert client.get("/review-queue", headers={"X-Caseworker-Key": "demo-caseworker"}).status_code == 200


def test_outside_demo_mode_no_code_is_returned(production):
    response = client.post("/auth/request-code", json={"phone": "7185550142"})
    assert response.status_code == 503
    assert "demo_code" not in response.json()
    assert response.json()["detail_zh"]


def test_outside_demo_mode_there_is_no_default_caseworker_key(production):
    response = client.get("/review-queue", headers={"X-Caseworker-Key": "demo-caseworker"})
    assert response.status_code == 503


def test_outside_demo_mode_a_configured_key_works(production, monkeypatch):
    monkeypatch.setenv("CASEWORKER_KEY", "s3cret-key")
    assert client.get("/review-queue", headers={"X-Caseworker-Key": "demo-caseworker"}).status_code == 401
    assert client.get("/review-queue", headers={"X-Caseworker-Key": "s3cret-key"}).status_code == 200


def test_demo_mode_must_be_explicit(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert settings.demo_mode() is False


def test_production_startup_fails_clearly_when_config_is_missing(production):
    problems = settings.production_config_problems()
    assert any("CASEWORKER_KEY" in p for p in problems)
    assert any("SMS" in p for p in problems)
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        with TestClient(app):
            pass


def test_production_rejects_the_public_demo_key(production, monkeypatch):
    monkeypatch.setenv("CASEWORKER_KEY", "demo-caseworker")
    assert any("public demo key" in p for p in settings.production_config_problems())
