"""WebSocket client registry and broadcast helpers."""

from __future__ import annotations

import json
from typing import Any

from aiohttp import web


class WebSocketManager:
    """Track connected WebSocket clients and broadcast JSON messages."""

    def __init__(self) -> None:
        self.clients: set[web.WebSocketResponse] = set()

    def add(self, ws: web.WebSocketResponse) -> None:
        self.clients.add(ws)

    def discard(self, ws: web.WebSocketResponse) -> None:
        self.clients.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        payload = json.dumps(message, ensure_ascii=False)
        closed: list[web.WebSocketResponse] = []
        for client in list(self.clients):
            if client.closed:
                closed.append(client)
                continue
            try:
                await client.send_str(payload)
            except ConnectionError:
                closed.append(client)
        for client in closed:
            self.discard(client)
