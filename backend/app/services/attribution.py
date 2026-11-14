"""Atribución: une el primer mensaje de WhatsApp con el clic guardado en la landing."""
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClickTrack, Conversation, ConversationAttribution

# Sin 0/O/1/I/L para que no se confundan si el cliente lo escribe a mano.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 6
CODE_RE = re.compile(r"\[([A-Za-z0-9]{%d})\]" % CODE_LEN)


def new_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        if db.scalar(select(ClickTrack.id).where(ClickTrack.code == code)) is None:
            return code
    raise RuntimeError("No se pudo generar un código único")


def build_fbc(fbc: str | None, fbclid: str | None, now_ms: int) -> str | None:
    """Meta pide fbc con formato fb.1.<ms>.<fbclid>; si falta la cookie se arma desde fbclid."""
    if fbc:
        return fbc
    if fbclid:
        return f"fb.1.{now_ms}.{fbclid}"
    return None


def attribute_conversation(db: Session, conversation: Conversation, body: str) -> bool:
    """Si el mensaje trae un código [XXXXXX] conocido, asocia la conversación a ese clic."""
    if not body:
        return False
    already = db.scalar(
        select(ConversationAttribution.id).where(ConversationAttribution.conversation_id == conversation.id)
    )
    if already:
        return False
    for match in CODE_RE.finditer(body):
        click = db.scalar(select(ClickTrack).where(ClickTrack.code == match.group(1).upper()))
        if click is None:
            continue
        db.add(ConversationAttribution(conversation_id=conversation.id, click_id=click.id))
        if click.utm_campaign and not conversation.campaign:
            conversation.campaign = click.utm_campaign
        db.flush()
        return True
    return False
