"""Envío de eventos a la Conversions API de Meta (flujo landing -> WhatsApp, action_source=website)."""
import hashlib
import json
import re
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    ClickTrack,
    Conversation,
    ConversationAttribution,
    ConversionEvent,
    utcnow,
)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def phone_hashes(phone: str | None) -> list[str]:
    """Teléfono normalizado (solo dígitos, con código de país) y hasheado con SHA-256.

    WhatsApp usa 549... para celulares de Argentina; Meta suele esperar 54 + área + número,
    así que se envían ambas variantes.
    """
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return []
    variants = {digits}
    if digits.startswith("549") and len(digits) > 10:
        variants.add("54" + digits[3:])
    return [sha256(v) for v in sorted(variants)]


def is_configured() -> bool:
    s = get_settings()
    return bool(s.meta_pixel_id and s.meta_access_token)


def build_payload(db: Session, event: ConversionEvent) -> dict:
    conversation = db.get(Conversation, event.conversation_id)
    user_data: dict = {"external_id": [sha256(f"conv-{conversation.id}")]}
    hashes = phone_hashes(conversation.contact.phone)
    if hashes:
        user_data["ph"] = hashes

    event_source_url = None
    click = db.scalar(
        select(ClickTrack)
        .join(ConversationAttribution, ConversationAttribution.click_id == ClickTrack.id)
        .where(ConversationAttribution.conversation_id == conversation.id)
    )
    if click:
        for key, value in (
            ("fbc", click.fbc),
            ("fbp", click.fbp),
            ("client_ip_address", click.client_ip),
            ("client_user_agent", click.user_agent),
        ):
            if value:
                user_data[key] = value
        event_source_url = click.source_url

    item: dict = {
        "event_name": event.event_name,
        "event_time": int(event.created_at.timestamp()),
        "event_id": event.event_id,
        "action_source": "website",
        "user_data": user_data,
    }
    if event_source_url:
        item["event_source_url"] = event_source_url
    if event.value is not None:
        item["custom_data"] = {"currency": event.currency, "value": event.value}

    payload: dict = {"data": [item]}
    test_code = get_settings().meta_test_event_code
    if test_code:
        payload["test_event_code"] = test_code
    return payload


def send_event(event_id: int, *, client: httpx.Client | None = None) -> None:
    """Envía un ConversionEvent (con hasta 3 intentos). Se usa como tarea en segundo plano."""
    settings = get_settings()
    with SessionLocal() as db:
        event = db.get(ConversionEvent, event_id)
        if event is None or event.status == "sent":
            return
        if not is_configured():
            event.status = "not_configured"
            event.response = "Falta META_PIXEL_ID o META_ACCESS_TOKEN en el .env"
            db.commit()
            return

        url = f"https://graph.facebook.com/{settings.meta_api_version}/{settings.meta_pixel_id}/events"
        payload = build_payload(db, event)
        own_client = client or httpx.Client(timeout=15)
        try:
            for attempt in range(3):
                event.attempts += 1
                try:
                    r = own_client.post(url, params={"access_token": settings.meta_access_token}, json=payload)
                    event.response = r.text[:2000]
                    if r.status_code == 200:
                        event.status = "sent"
                        event.sent_at = utcnow()
                        break
                    event.status = "failed"
                    if 400 <= r.status_code < 500:
                        break  # error de datos/permisos: reintentar igual no sirve
                except httpx.HTTPError as exc:
                    event.status = "failed"
                    event.response = f"Error de red: {exc}"[:2000]
                db.commit()
                time.sleep(2 * (attempt + 1))
            db.commit()
        finally:
            if client is None:
                own_client.close()
