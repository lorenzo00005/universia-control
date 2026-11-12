from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.security import decode_access_token
from app.services.hub import hub

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def realtime(ws: WebSocket, token: str = ""):
    if decode_access_token(token) is None:
        await ws.close(code=4401)
        return
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()  # mantiene la conexión; el panel no envía nada
    except WebSocketDisconnect:
        hub.disconnect(ws)
