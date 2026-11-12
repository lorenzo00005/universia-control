from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models import SessionEvent, User, WhatsAppNumber, utcnow
from app.schemas import NumberCreate, NumberOut
from app.services.ingest import upsert_number
from app.services.providers import ProviderError, get_provider, waha_provider

router = APIRouter(prefix="/numbers", tags=["numbers"])


def _get_number(db: Session, number_id: int) -> WhatsAppNumber:
    number = db.get(WhatsAppNumber, number_id)
    if number is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Número no encontrado")
    return number


@router.get("", response_model=list[NumberOut])
def list_numbers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(WhatsAppNumber).order_by(WhatsAppNumber.id)).all()


@router.post("", response_model=NumberOut, status_code=status.HTTP_201_CREATED)
def create_number(data: NumberCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.scalar(select(WhatsAppNumber).where(WhatsAppNumber.session_name == data.session_name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una sesión con ese nombre")

    number = WhatsAppNumber(session_name=data.session_name, label=data.label, status="STARTING")
    try:
        get_provider(number).create_session(number.session_name)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    db.add(number)
    db.flush()
    db.add(SessionEvent(number_id=number.id, status="STARTING"))
    db.commit()
    return number


@router.post("/sync", response_model=list[NumberOut])
def sync_numbers(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Importa las sesiones que ya existen en WAHA (por ejemplo las creadas desde su dashboard)."""
    try:
        sessions = waha_provider().list_sessions()
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    for info in sessions:
        upsert_number(db, info.name, info.status, info.phone)
    db.commit()
    return db.scalars(select(WhatsAppNumber).order_by(WhatsAppNumber.id)).all()


@router.get("/{number_id}/status", response_model=NumberOut)
def refresh_status(number_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    number = _get_number(db, number_id)
    try:
        info = get_provider(number).get_session(number.session_name)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    if info.status != number.status:
        number.status = info.status
        number.status_changed_at = utcnow()
        db.add(SessionEvent(number_id=number.id, status=info.status))
    number.phone = info.phone or number.phone
    db.commit()
    return number


@router.get("/{number_id}/qr")
def get_qr(number_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    number = _get_number(db, number_id)
    try:
        image = get_provider(number).get_qr(number.session_name)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return Response(content=image, media_type="image/png")


@router.post("/{number_id}/restart", status_code=status.HTTP_204_NO_CONTENT)
def restart(number_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    number = _get_number(db, number_id)
    try:
        get_provider(number).restart_session(number.session_name)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.delete("/{number_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_number(number_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    number = _get_number(db, number_id)
    try:
        get_provider(number).delete_session(number.session_name)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    # Las conversaciones se conservan; el número queda marcado como eliminado.
    number.status = "DELETED"
    number.status_changed_at = utcnow()
    db.commit()
