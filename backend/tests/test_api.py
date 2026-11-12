from tests.conftest import waha_event

HOOK = "/webhooks/waha/hook-secret"
CHAT = "5491155550000@c.us"


def inbound(msg_id="true_in_1", ts=1_700_000_000, body="hola"):
    return waha_event(id=msg_id, timestamp=ts, **{"from": CHAT, "fromMe": False, "to": "x@c.us"},
                      body=body, hasMedia=False, _data={"pushName": "Juan"})


def test_login_ok_and_bad(client):
    assert client.post("/auth/login", data={"username": "admin@test.com", "password": "x"}).status_code == 401
    assert client.get("/numbers").status_code == 401


def test_create_number_and_duplicate(client, auth, number, fake_provider):
    assert fake_provider.created == ["ventas1"]
    dup = client.post("/numbers", json={"session_name": "ventas1", "label": "x"}, headers=auth)
    assert dup.status_code == 409
    bad = client.post("/numbers", json={"session_name": "Con Espacios", "label": "x"}, headers=auth)
    assert bad.status_code == 422


def test_webhook_rejects_bad_secret(client):
    assert client.post("/webhooks/waha/nope", json={}).status_code == 403


def test_inbound_creates_conversation_and_dedupes(client, auth, number):
    assert client.post(HOOK, json=inbound()).status_code == 200
    assert client.post(HOOK, json=inbound()).status_code == 200  # mismo id: no duplica

    convs = client.get("/conversations", headers=auth).json()
    assert len(convs) == 1
    assert convs[0]["contact"]["name"] == "Juan"
    assert convs[0]["unread_count"] == 1
    assert convs[0]["stage_id"] is not None  # etapa inicial "Nuevo"
    msgs = client.get(f"/conversations/{convs[0]['id']}/messages", headers=auth).json()
    assert [m["body"] for m in msgs] == ["hola"]


def test_first_response_time_recorded(client, auth, number):
    client.post(HOOK, json=inbound())
    out = waha_event(id="true_out_1", timestamp=1_700_000_060, to=CHAT, fromMe=True, body="hola!", hasMedia=False)
    client.post(HOOK, json=out)
    conv = client.get("/conversations", headers=auth).json()[0]
    assert conv["first_inbound_at"] is not None and conv["first_response_at"] is not None


def test_group_messages_ignored(client, auth, number):
    group = waha_event(id="g1", timestamp=1, **{"from": "123@g.us", "fromMe": False}, body="x")
    client.post(HOOK, json=group)
    assert client.get("/conversations", headers=auth).json() == []


def test_session_status_updates_number(client, auth, number):
    client.post(HOOK, json=waha_event(event="session.status", status="FAILED"))
    numbers = client.get("/numbers", headers=auth).json()
    assert numbers[0]["status"] == "FAILED"


def test_send_requires_connected_number(client, auth, number, fake_provider):
    client.post(HOOK, json=inbound())
    conv_id = client.get("/conversations", headers=auth).json()[0]["id"]

    blocked = client.post(f"/conversations/{conv_id}/messages", json={"text": "hi"}, headers=auth)
    assert blocked.status_code == 409  # número en STARTING

    client.post(HOOK, json=waha_event(event="session.status", status="WORKING"))
    sent = client.post(f"/conversations/{conv_id}/messages", json={"text": "hola Juan"}, headers=auth)
    assert sent.status_code == 201
    assert fake_provider.sent == [("ventas1", CHAT, "hola Juan")]

    # el eco del webhook con el mismo id no duplica el mensaje
    echo = waha_event(id=sent.json() and "true_" + CHAT + "_OUT1", timestamp=1_700_000_100,
                      to=CHAT, fromMe=True, body="hola Juan", hasMedia=False)
    client.post(HOOK, json=echo)
    msgs = client.get(f"/conversations/{conv_id}/messages", headers=auth).json()
    assert [m["direction"] for m in msgs] == ["in", "out"]


def test_move_stage_and_validate(client, auth, number):
    client.post(HOOK, json=inbound())
    conv_id = client.get("/conversations", headers=auth).json()[0]["id"]
    stages = client.get("/stages", headers=auth).json()
    won = next(s for s in stages if s["is_won"])

    ok = client.patch(f"/conversations/{conv_id}", json={"stage_id": won["id"]}, headers=auth)
    assert ok.status_code == 200 and ok.json()["stage_id"] == won["id"]
    bad = client.patch(f"/conversations/{conv_id}", json={"stage_id": 9999}, headers=auth)
    assert bad.status_code == 422


def test_websocket_requires_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=bad"):
            pass


def test_list_users_requires_auth(client, auth):
    assert client.get("/users").status_code == 401
    users = client.get("/users", headers=auth).json()
    assert users[0]["email"] == "admin@test.com" and "hashed_password" not in users[0]


def test_sync_imports_sessions_created_in_waha(client, auth, fake_provider):
    numbers = client.post("/numbers/sync", headers=auth).json()
    assert [(n["session_name"], n["status"], n["phone"]) for n in numbers] == [("sesion1", "WORKING", "5491100000000")]
    again = client.post("/numbers/sync", headers=auth).json()
    assert len(again) == 1  # idempotente


def test_unknown_session_message_auto_registers_number(client, auth):
    event = waha_event(session="desde-dashboard", id="x1", timestamp=1_700_000_000,
                       **{"from": CHAT, "fromMe": False}, body="hola", hasMedia=False)
    assert client.post(HOOK, json=event).status_code == 200
    numbers = client.get("/numbers", headers=auth).json()
    assert numbers[0]["session_name"] == "desde-dashboard" and numbers[0]["status"] == "WORKING"
    assert len(client.get("/conversations", headers=auth).json()) == 1


def test_bad_payload_is_logged_not_fatal(client, auth, number):
    r = client.post(HOOK, json={"event": "message.any", "session": "ventas1", "payload": "raro"})
    assert r.status_code == 200 and r.json() == {"ok": False}
    recent = client.get("/webhooks/recent", headers=auth).json()
    assert recent[0]["ok"] is False and "AttributeError" in recent[0]["error"]
    client.post(HOOK, json=inbound())
    assert client.get("/webhooks/recent", headers=auth).json()[0]["ok"] is True
    assert client.get("/webhooks/recent").status_code == 401
