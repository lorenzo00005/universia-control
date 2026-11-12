import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WEBHOOK_SECRET"] = "hook-secret"
os.environ["JWT_SECRET"] = "test-jwt-secret-test-jwt-secret-1234"
os.environ["ADMIN_EMAIL"] = "admin@test.com"
os.environ["ADMIN_PASSWORD"] = "admin-pass"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.services.providers import SessionInfo


class FakeProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.created: list[str] = []

    def create_session(self, session_name): self.created.append(session_name)
    def list_sessions(self):
        return [SessionInfo(name="sesion1", status="WORKING", phone="5491100000000")]

    def get_session(self, session_name): return SessionInfo(status="WORKING", phone="5491100000000")
    def get_qr(self, session_name): return b"\x89PNG-fake"
    def restart_session(self, session_name): pass
    def delete_session(self, session_name): pass

    def send_text(self, session_name, chat_id, text):
        self.sent.append((session_name, chat_id, text))
        return f"true_{chat_id}_OUT{len(self.sent)}"


@pytest.fixture()
def fake_provider(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.routers.number_routes.get_provider", lambda number: provider)
    monkeypatch.setattr("app.routers.conversation_routes.get_provider", lambda number: provider)
    monkeypatch.setattr("app.routers.number_routes.waha_provider", lambda: provider)
    return provider


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)  # base limpia en cada test
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/auth/login", data={"username": "admin@test.com", "password": "admin-pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def number(client, auth, fake_provider):
    r = client.post("/numbers", json={"session_name": "ventas1", "label": "Ventas 1"}, headers=auth)
    assert r.status_code == 201
    return r.json()


def waha_event(session="ventas1", event="message.any", **payload):
    return {"event": event, "session": session, "payload": payload}
