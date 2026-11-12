import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import require_admin
from app.models import User
from app.services import webhook_log
from app.services.hub import hub
from app.services.ingest import ingest_waha_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = logging.getLogger("uvicorn.error")


@router.post("/waha/{secret}", status_code=status.HTTP_200_OK)
def waha_webhook(
    secret: str,
    background: BackgroundTasks,
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    if not hmac.compare_digest(secret, get_settings().webhook_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Secreto inválido")
    log.info("webhook WAHA event=%s session=%s", body.get("event"), body.get("session"))
    try:
        event = ingest_waha_event(db, body)
    except Exception as exc:  # un payload raro no debe tirar abajo la entrega ni disparar reintentos
        db.rollback()
        log.exception("Error procesando webhook de WAHA")
        webhook_log.record(body, ok=False, error=f"{type(exc).__name__}: {exc}")
        return {"ok": False}
    webhook_log.record(body, ok=True)
    if event:
        background.add_task(hub.broadcast, event)
    return {"ok": True}


@router.get("/recent")
def recent_webhooks(_: User = Depends(require_admin)) -> list[dict]:
    """Últimos 30 webhooks recibidos (más nuevo primero). Sirve para ver qué manda WAHA y si falló algo."""
    return webhook_log.recent()
