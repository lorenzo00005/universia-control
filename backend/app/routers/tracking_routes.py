import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ClickTrack, Conversation, ConversionEvent, PipelineStage, User, utcnow
from app.schemas import ClickIn, ClickOut, ConversationOut, ConversionEventOut, SaleIn
from app.services.attribution import build_fbc, new_code
from app.services.hub import hub
from app.services.meta_capi import send_event

router = APIRouter(tags=["tracking"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


@router.post("/track/click", response_model=ClickOut, status_code=status.HTTP_201_CREATED)
def track_click(data: ClickIn, request: Request, db: Session = Depends(get_db)):
    """Público: lo llama el script de la landing al cargar la página."""
    click = ClickTrack(
        code=new_code(db),
        fbclid=data.fbclid,
        fbc=build_fbc(data.fbc, data.fbclid, int(time.time() * 1000)),
        fbp=data.fbp,
        client_ip=_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        source_url=data.source_url,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
    )
    db.add(click)
    db.commit()
    return ClickOut(code=click.code)


@router.post("/conversations/{conversation_id}/sale", response_model=ConversationOut)
def mark_sale(
    conversation_id: int,
    data: SaleIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marca el chat como venta: mueve a la etapa 'ganada' y manda Purchase a Meta."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversación no encontrada")

    won = db.scalar(select(PipelineStage).where(PipelineStage.is_won.is_(True)).order_by(PipelineStage.position))
    if won:
        conversation.stage_id = won.id

    now = utcnow()
    event = ConversionEvent(
        conversation_id=conversation.id,
        event_name="Purchase",
        event_id=f"purchase-{conversation.id}-{int(now.timestamp())}",
        value=data.value,
        currency=(data.currency or get_settings().meta_default_currency).upper(),
        created_by=user.id,
        created_at=now,
    )
    db.add(event)
    db.commit()
    background.add_task(send_event, event.id)

    out = ConversationOut.model_validate(conversation)
    background.add_task(hub.broadcast, {"type": "conversation", "conversation": out.model_dump(mode="json")})
    return out


@router.get("/conversions", response_model=list[ConversionEventOut])
def list_conversions(
    limit: int = 100, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return db.scalars(
        select(ConversionEvent).order_by(ConversionEvent.id.desc()).limit(min(limit, 500))
    ).all()


@router.post("/conversions/{event_id}/retry", response_model=ConversionEventOut)
def retry_conversion(
    event_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    event = db.get(ConversionEvent, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento no encontrado")
    if event.status == "sent":
        raise HTTPException(status.HTTP_409_CONFLICT, "El evento ya fue enviado")
    event.status = "pending"
    db.commit()
    background.add_task(send_event, event.id)
    return event
