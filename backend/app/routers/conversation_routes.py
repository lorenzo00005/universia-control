from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Conversation, Message, PipelineStage, User, utcnow
from app.schemas import ConversationOut, ConversationUpdate, MessageOut, SendMessageIn
from app.services.hub import hub
from app.services.ingest import message_event, record_message
from app.services.providers import ProviderError, get_provider

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get_conversation(db: Session, conversation_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada")
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    number_id: int | None = None,
    stage_id: int | None = None,
    assigned_to: int | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Conversation).order_by(Conversation.last_message_at.desc().nullslast())
    if number_id is not None:
        query = query.where(Conversation.number_id == number_id)
    if stage_id is not None:
        query = query.where(Conversation.stage_id == stage_id)
    if assigned_to is not None:
        query = query.where(Conversation.assigned_to == assigned_to)
    if status_filter:
        query = query.where(Conversation.status == status_filter)
    return db.scalars(query.limit(min(limit, 200)).offset(offset)).unique().all()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_conversation(db, conversation_id)
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(min(limit, 500))
    ).all()
    return list(reversed(rows))


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    conversation = _get_conversation(db, conversation_id)
    changes = data.model_dump(exclude_unset=True)
    if "stage_id" in changes and changes["stage_id"] is not None:
        if db.get(PipelineStage, changes["stage_id"]) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Etapa inexistente")
    if "assigned_to" in changes and changes["assigned_to"] is not None:
        if db.get(User, changes["assigned_to"]) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Usuario inexistente")
    for field, value in changes.items():
        setattr(conversation, field, value)
    db.commit()
    out = ConversationOut.model_validate(conversation)
    background.add_task(hub.broadcast, {"type": "conversation", "conversation": out.model_dump(mode="json")})
    return out


@router.post("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(conversation_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conversation = _get_conversation(db, conversation_id)
    conversation.unread_count = 0
    db.commit()


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    data: SendMessageIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _get_conversation(db, conversation_id)
    number = conversation.number
    if number.status != "WORKING":
        raise HTTPException(status.HTTP_409_CONFLICT, f"El número no está conectado ({number.status})")

    try:
        external_id = get_provider(number).send_text(
            number.session_name, conversation.contact.chat_id, data.text
        )
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    message, _ = record_message(
        db,
        conversation,
        external_id=external_id,
        direction="out",
        body=data.text,
        has_media=False,
        created_at=utcnow(),
        sent_by=user.id,
    )
    if conversation.assigned_to is None:
        conversation.assigned_to = user.id
    db.commit()
    background.add_task(hub.broadcast, message_event(conversation, message))
    return message
