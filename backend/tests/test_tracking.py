import json

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.models import ConversionEvent
from app.services import meta_capi
from app.services.attribution import build_fbc, CODE_RE
from tests.conftest import waha_event

HOOK = "/webhooks/waha/hook-secret"
CHAT = "5491155550000@c.us"


def inbound(body, msg_id="true_in_1"):
    return waha_event(id=msg_id, timestamp=1_700_000_000, **{"from": CHAT, "fromMe": False, "to": "x@c.us"},
                      body=body, hasMedia=False, _data={"pushName": "Juan"})


def new_click(client, **extra):
    data = {"fbclid": "IwAR123", "fbp": "fb.1.111.222", "source_url": "https://landing.test/promo",
            "utm_campaign": "black-friday", **extra}
    r = client.post("/track/click", json=data, headers={"User-Agent": "UA-test", "X-Forwarded-For": "200.1.2.3, 10.0.0.1"})
    assert r.status_code == 201
    return r.json()["code"]


def test_click_returns_code_and_builds_fbc(client):
    code = new_click(client)
    assert len(code) == 6 and code.isalnum()
    assert build_fbc(None, "abc", 1000) == "fb.1.1000.abc"
    assert build_fbc("fb.1.5.x", "abc", 1000) == "fb.1.5.x"
    assert build_fbc(None, None, 1000) is None


def test_code_in_first_message_attributes_conversation(client, auth, number):
    code = new_click(client)
    client.post(HOOK, json=inbound(f"Hola, quiero info [{code}]"))
    conv = client.get("/conversations", headers=auth).json()[0]
    assert conv["campaign"] == "black-friday"


def test_unknown_or_missing_code_is_ignored(client, auth, number):
    client.post(HOOK, json=inbound("Hola [ZZZZZZ]"))
    assert client.get("/conversations", headers=auth).json()[0]["campaign"] is None
    assert CODE_RE.search("sin codigo") is None


def test_mark_sale_moves_stage_and_queues_event(client, auth, number, monkeypatch):
    sent = []
    monkeypatch.setattr("app.routers.tracking_routes.send_event", lambda event_id: sent.append(event_id))
    client.post(HOOK, json=inbound("hola"))
    conv = client.get("/conversations", headers=auth).json()[0]

    r = client.post(f"/conversations/{conv['id']}/sale", json={"value": 15000, "currency": "ars"}, headers=auth)
    assert r.status_code == 200
    stages = {s["id"]: s for s in client.get("/stages", headers=auth).json()}
    assert stages[r.json()["stage_id"]]["is_won"] is True

    events = client.get("/conversions", headers=auth).json()
    assert len(events) == 1 and events[0]["value"] == 15000 and events[0]["currency"] == "ARS"
    assert sent == [events[0]["id"]]
    assert client.post("/conversations/999/sale", json={}, headers=auth).status_code == 404


def test_send_event_payload_and_success(client, auth, number, monkeypatch):
    monkeypatch.setenv("META_PIXEL_ID", "PIX1")
    monkeypatch.setenv("META_ACCESS_TOKEN", "TOKEN")
    get_settings.cache_clear()
    try:
        monkeypatch.setattr("app.routers.tracking_routes.send_event", lambda event_id: None)
        code = new_click(client)
        client.post(HOOK, json=inbound(f"hola [{code}]"))
        conv = client.get("/conversations", headers=auth).json()[0]
        client.post(f"/conversations/{conv['id']}/sale", json={"value": 100}, headers=auth)
        event_id = client.get("/conversions", headers=auth).json()[0]["id"]

        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"events_received": 1})

        meta_capi.send_event(event_id, client=httpx.Client(transport=httpx.MockTransport(handler)))
        assert "/PIX1/events" in captured["url"] and "access_token=TOKEN" in captured["url"]
        item = captured["body"]["data"][0]
        assert item["event_name"] == "Purchase" and item["action_source"] == "website"
        assert item["custom_data"] == {"currency": "ARS", "value": 100.0}
        ud = item["user_data"]
        assert ud["fbp"] == "fb.1.111.222" and ud["fbc"].endswith(".IwAR123")
        assert ud["client_ip_address"] == "200.1.2.3" and ud["client_user_agent"] == "UA-test"
        assert len(ud["ph"]) == 2 and all(len(h) == 64 for h in ud["ph"])  # variantes 549.. y 54..
        assert "5491155550000" not in json.dumps(captured["body"])  # el teléfono va solo hasheado
        assert item["event_source_url"] == "https://landing.test/promo"
        with SessionLocal() as db:
            assert db.get(ConversionEvent, event_id).status == "sent"
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_send_event_not_configured_and_retry(client, auth, number, monkeypatch):
    monkeypatch.setattr("app.routers.tracking_routes.send_event", lambda event_id: None)
    client.post(HOOK, json=inbound("hola"))
    conv = client.get("/conversations", headers=auth).json()[0]
    client.post(f"/conversations/{conv['id']}/sale", json={}, headers=auth)
    event_id = client.get("/conversions", headers=auth).json()[0]["id"]
    meta_capi.send_event(event_id)
    ev = client.get("/conversions", headers=auth).json()[0]
    assert ev["status"] == "not_configured"
    assert client.post(f"/conversions/{event_id}/retry", headers=auth).json()["status"] == "pending"
    assert client.post("/conversions/999/retry", headers=auth).status_code == 404


def test_client_error_is_not_retried(client, auth, number, monkeypatch):
    monkeypatch.setenv("META_PIXEL_ID", "PIX1")
    monkeypatch.setenv("META_ACCESS_TOKEN", "BAD")
    get_settings.cache_clear()
    try:
        monkeypatch.setattr("app.routers.tracking_routes.send_event", lambda event_id: None)
        client.post(HOOK, json=inbound("hola"))
        conv = client.get("/conversations", headers=auth).json()[0]
        client.post(f"/conversations/{conv['id']}/sale", json={}, headers=auth)
        event_id = client.get("/conversions", headers=auth).json()[0]["id"]
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(400, json={"error": {"message": "Invalid OAuth access token"}})

        meta_capi.send_event(event_id, client=httpx.Client(transport=httpx.MockTransport(handler)))
        assert len(calls) == 1
        ev = client.get("/conversions", headers=auth).json()[0]
        assert ev["status"] == "failed" and "Invalid OAuth" in ev["response"]
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
