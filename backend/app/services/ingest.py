"""Procesa los eventos que llegan de WAHA y los guarda."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Contact,
    Conversation,
    Message,
    PipelineStage,
    SessionEvent,
    WhatsAppNumber,
    utcnow,
)
from app.schemas import ConversationOut, MessageOut
from app.services.attribution import attribute_conversation


def find_key(data: object, key: str) -> str | None:
    """Busca recursivamente una clave (sin importar mayúsculas). Sirve para ctwa_clid."""
    target = key.lower()
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == target and isinstance(v, str) and v:
                return v
            found = find_key(v, key)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_key(item, key)
            if found:
                return found
    return None


def upsert_number(db: Session, session_name: str, status: str, phone: str | None) -> WhatsAppNumber:
    """Registra (o actualiza) un número a partir de una sesión que existe en WAHA."""
    number = db.scalar(select(WhatsAppNumber).where(WhatsAppNumber.session_name == session_name))
    if number is None:
        number = WhatsAppNumber(session_name=session_name, label=session_name, status=status, phone=phone)
        db.add(number)
        db.flush()
        db.add(SessionEvent(number_id=number.id, status=status))
        return number
    if status != number.status:
        number.status = status
        number.status_changed_at = utcnow()
        db.add(SessionEvent(number_id=number.id, status=status))
    number.phone = phone or number.phone
    return number


def get_or_create_conversation(
    db: Session, number: WhatsAppNumber, chat_id: str, name: str | None
) -> Conversation:
    contact = db.scalar(
        select(Contact).where(Contact.number_id == number.id, Contact.chat_id == chat_id)
    )
    if contact is None:
        phone = chat_id.split("@")[0] if chat_id.endswith("@c.us") else None
        contact = Contact(number_id=number.id, chat_id=chat_id, name=name, phone=phone)
        db.add(contact)
        db.flush()
    elif name and not contact.name:
        contact.name = name

    conversation = db.scalar(select(Conversation).where(Conversation.contact_id == contact.id))
    if conversation is None:
        first_stage = db.scalar(select(PipelineStage).order_by(PipelineStage.position))
        conversation = Conversation(
            number_id=number.id,
            contact_id=contact.id,
            stage_id=first_stage.id if first_stage else None,
        )
        db.add(conversation)
        db.flush()
    return conversation


def record_message(
    db: Session,
    conversation: Conversation,
    *,
    external_id: str | None,
    direction: str,
    body: str,
    has_media: bool,
    created_at: datetime,
    sent_by: int | None = None,
) -> tuple[Message, bool]:
    """Devuelve (mensaje, es_nuevo). Deduplica por external_id."""
    if external_id:
        existing = db.scalar(select(Message).where(Message.external_id == external_id))
        if existing:
            return existing, False

    message = Message(
        conversation_id=conversation.id,
        external_id=external_id,
        direction=direction,
        body=body,
        has_media=has_media,
        sent_by=sent_by,
        created_at=created_at,
    )
    db.add(message)

    conversation.last_message_at = created_at
    conversation.last_message_preview = (body or ("[archivo]" if has_media else ""))[:200]
    if direction == "in":
        conversation.unread_count += 1
        conversation.status = "open"
        if conversation.first_inbound_at is None:
            conversation.first_inbound_at = created_at
    elif conversation.first_inbound_at and conversation.first_response_at is None:
        conversation.first_response_at = created_at
    db.flush()
    return message, True


def message_event(conversation: Conversation, message: Message) -> dict:
    return {
        "type": "message",
        "conversation": ConversationOut.model_validate(conversation).model_dump(mode="json"),
        "message": MessageOut.model_validate(message).model_dump(mode="json"),
    }


def ingest_waha_event(db: Session, body: dict) -> dict | None:
    """Procesa un webhook de WAHA. Devuelve el evento a emitir al panel, si corresponde."""
    event = body.get("event")
    payload = body.get("payload") or {}
    session_name = body.get("session")
    if not session_name:
        return None
    number = db.scalar(select(WhatsAppNumber).where(WhatsAppNumber.session_name == session_name))
    if number is None:
        # Sesión creada fuera del CRM (ej. dashboard de WAHA): se registra sola.
        number = upsert_number(db, session_name, "WORKING" if event != "session.status" else (payload.get("status") or "UNKNOWN"), None)
        db.commit()

    if event == "session.status":
        status = payload.get("status") or "UNKNOWN"
        if status != number.status:
            number.status = status
            number.status_changed_at = utcnow()
            db.add(SessionEvent(number_id=number.id, status=status))
        me = (payload.get("me") or {}).get("id") or ""
        if me:
            number.phone = me.split("@")[0].split(":")[0]
        db.commit()
        return {"type": "session", "number_id": number.id, "status": status}

    if event == "message.ack":
        message = db.scalar(select(Message).where(Message.external_id == payload.get("id")))
        if message and isinstance(payload.get("ack"), int):
            message.ack = payload["ack"]
            db.commit()
            return {"type": "ack", "message_id": message.id, "ack": message.ack}
        return None

    if event == "message.any":
        from_me = bool(payload.get("fromMe"))
        chat_id = payload.get("to") if from_me else payload.get("from")
        if not chat_id or chat_id.endswith("@g.us") or chat_id == "status@broadcast":
            return None  # grupos y estados: fuera de alcance

        raw = payload.get("_data") or {}
        push_name = None if from_me else (raw.get("pushName") or find_key(raw, "pushName"))
        conversation = get_or_create_conversation(db, number, chat_id, push_name)

        ts = payload.get("timestamp")
        created_at = (
            datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) else utcnow()
        )
        message, is_new = record_message(
            db,
            conversation,
            external_id=payload.get("id"),
            direction="out" if from_me else "in",
            body=payload.get("body") or "",
            has_media=bool(payload.get("hasMedia")),
            created_at=created_at,
        )
        if not is_new:
            return None
        if not from_me and not conversation.ctwa_clid:
            conversation.ctwa_clid = find_key(raw, "ctwaClid")
        if not from_me:
            attribute_conversation(db, conversation, payload.get("body") or "")
        db.commit()
        db.refresh(conversation)
        return message_event(conversation, message)

    return None
