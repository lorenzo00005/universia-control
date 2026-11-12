"""Registro en memoria de los últimos webhooks recibidos, para diagnosticar integraciones."""
import json
from collections import deque
from datetime import datetime, timezone

_RECENT: deque[dict] = deque(maxlen=30)


def record(body: object, ok: bool, error: str | None = None) -> None:
    event = body.get("event") if isinstance(body, dict) else None
    session = body.get("session") if isinstance(body, dict) else None
    _RECENT.appendleft(
        {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "session": session,
            "ok": ok,
            "error": error,
            "payload": json.dumps(body, ensure_ascii=False, default=str)[:1500],
        }
    )


def recent() -> list[dict]:
    return list(_RECENT)
