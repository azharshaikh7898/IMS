from __future__ import annotations

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.api.deps import ServiceContainer


async def websocket_dashboard(websocket: WebSocket, services: ServiceContainer) -> None:
    await websocket.accept()
    queue = services.realtime.register_listener()
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, default=str))
    except WebSocketDisconnect:
        pass
    finally:
        services.realtime.unregister_listener(queue)
