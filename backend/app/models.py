from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="operator")  # admin | operator
    is_active: Mapped[bool] = mapped_column(default=True)


class WhatsAppNumber(Base):
    __tablename__ = "whatsapp_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_name: Mapped[str] = mapped_column(String(60), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40), default=None)
    provider: Mapped[str] = mapped_column(String(20), default="waha")  # waha | cloud_api (futuro)
    status: Mapped[str] = mapped_column(String(30), default="STOPPED")
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionEvent(Base):
    """Historial de estados de sesión: base del monitoreo de caídas."""

    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_numbers.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_won: Mapped[bool] = mapped_column(default=False)
    is_lost: Mapped[bool] = mapped_column(default=False)


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("number_id", "chat_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_numbers.id"), index=True)
    chat_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str | None] = mapped_column(String(160), default=None)
    phone: Mapped[str | None] = mapped_column(String(40), default=None)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_numbers.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), unique=True)
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("pipeline_stages.id"), default=None)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | closed
    unread_count: Mapped[int] = mapped_column(default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_message_preview: Mapped[str | None] = mapped_column(String(200), default=None)
    # Base para reportes y Meta CAPI
    first_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ctwa_clid: Mapped[str | None] = mapped_column(String(300), default=None)
    campaign: Mapped[str | None] = mapped_column(String(160), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    contact: Mapped[Contact] = relationship(lazy="joined")
    number: Mapped[WhatsAppNumber] = relationship(lazy="joined")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True, default=None)
    direction: Mapped[str] = mapped_column(String(3))  # in | out
    body: Mapped[str] = mapped_column(Text, default="")
    has_media: Mapped[bool] = mapped_column(default=False)
    ack: Mapped[int] = mapped_column(default=0)
    sent_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ClickTrack(Base):
    """Clic en la landing: guarda los datos que Meta necesita para atribuir la venta al anuncio."""

    __tablename__ = "click_tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    fbclid: Mapped[str | None] = mapped_column(String(500), default=None)
    fbc: Mapped[str | None] = mapped_column(String(500), default=None)
    fbp: Mapped[str | None] = mapped_column(String(200), default=None)
    client_ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(500), default=None)
    source_url: Mapped[str | None] = mapped_column(String(1000), default=None)
    utm_source: Mapped[str | None] = mapped_column(String(160), default=None)
    utm_medium: Mapped[str | None] = mapped_column(String(160), default=None)
    utm_campaign: Mapped[str | None] = mapped_column(String(160), default=None)
    utm_content: Mapped[str | None] = mapped_column(String(160), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversationAttribution(Base):
    """Une una conversación con el clic de la landing que la originó."""

    __tablename__ = "conversation_attributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), unique=True)
    click_id: Mapped[int] = mapped_column(ForeignKey("click_tracks.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversionEvent(Base):
    """Evento enviado (o por enviar) a la Conversions API de Meta."""

    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    event_name: Mapped[str] = mapped_column(String(40), default="Purchase")
    event_id: Mapped[str] = mapped_column(String(80), unique=True)
    value: Mapped[float | None] = mapped_column(default=None)
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed | not_configured
    attempts: Mapped[int] = mapped_column(default=0)
    response: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
