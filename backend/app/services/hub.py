from fastapi import WebSocket


class Hub:
    """Distribuye eventos en tiempo real a los paneles conectados.

    En memoria: sirve con un solo proceso. Con varios workers hay que pasarlo a Redis pub/sub.
    """

    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, event: dict) -> None:
        for ws in list(self.connections):
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect(ws)


hub = Hub()
