"""Capa de proveedor: el resto del backend no sabe si el número va por WAHA o por la Cloud API."""
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import get_settings
from app.models import WhatsAppNumber


class ProviderError(Exception):
    pass


@dataclass
class SessionInfo:
    status: str
    phone: str | None = None
    name: str = ""


def phone_from_me(me: dict | None) -> str | None:
    raw = ((me or {}).get("id") or "").split("@")[0].split(":")[0]
    return raw or None


class MessagingProvider(Protocol):
    def create_session(self, session_name: str) -> None: ...
    def list_sessions(self) -> list[SessionInfo]: ...
    def get_session(self, session_name: str) -> SessionInfo: ...
    def get_qr(self, session_name: str) -> bytes: ...
    def restart_session(self, session_name: str) -> None: ...
    def delete_session(self, session_name: str) -> None: ...
    def send_text(self, session_name: str, chat_id: str, text: str) -> str | None: ...


class WahaProvider:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.client = httpx.Client(
            base_url=base_url, headers={"X-Api-Key": api_key}, timeout=20
        )

    def _call(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"WAHA {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"WAHA no responde: {exc}") from exc
        return response

    def create_session(self, session_name: str) -> None:
        # El webhook es global (WHATSAPP_HOOK_URL en el contenedor de WAHA): aplica a toda sesión.
        self._call("POST", "/api/sessions", json={"name": session_name, "start": True})

    def list_sessions(self) -> list[SessionInfo]:
        rows = self._call("GET", "/api/sessions", params={"all": "true"}).json()
        return [
            SessionInfo(name=row.get("name", ""), status=row.get("status", "UNKNOWN"), phone=phone_from_me(row.get("me")))
            for row in rows
            if row.get("name")
        ]

    def get_session(self, session_name: str) -> SessionInfo:
        data = self._call("GET", f"/api/sessions/{session_name}").json()
        return SessionInfo(name=session_name, status=data.get("status", "UNKNOWN"), phone=phone_from_me(data.get("me")))

    def get_qr(self, session_name: str) -> bytes:
        return self._call("GET", f"/api/{session_name}/auth/qr", params={"format": "image"}).content

    def restart_session(self, session_name: str) -> None:
        self._call("POST", f"/api/sessions/{session_name}/restart")

    def delete_session(self, session_name: str) -> None:
        self._call("DELETE", f"/api/sessions/{session_name}")

    def send_text(self, session_name: str, chat_id: str, text: str) -> str | None:
        data = self._call(
            "POST", "/api/sendText", json={"session": session_name, "chatId": chat_id, "text": text}
        ).json()
        raw_id = data.get("id")
        if isinstance(raw_id, dict):
            return raw_id.get("_serialized") or raw_id.get("id")
        return raw_id


def waha_provider() -> WahaProvider:
    settings = get_settings()
    return WahaProvider(settings.waha_url, settings.waha_api_key)


def get_provider(number: WhatsAppNumber) -> MessagingProvider:
    if number.provider == "waha":
        return waha_provider()
    raise ProviderError(f"Proveedor no soportado: {number.provider}")
