from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    def add_connection(
        self,
        user_id: str,
        websocket: WebSocket,
    ) -> None:
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

    def remove_connection(
        self,
        user_id: str,
        websocket: WebSocket,
    ) -> None:
        connections = self.active_connections.get(user_id)

        if not connections:
            return

        connections.discard(websocket)

        if not connections:
            del self.active_connections[user_id]

    async def send_to_user(
        self,
        user_id: str,
        event: str,
        data: dict,
    ) -> None:
        connections = self.active_connections.get(user_id, set())

        disconnected_connections: list[WebSocket] = []

        for websocket in connections.copy():
            try:
                await websocket.send_json(
                    {
                        "event": event,
                        "data": data,
                    }
                )
            except Exception:
                disconnected_connections.append(websocket)

        for websocket in disconnected_connections:
            self.remove_connection(user_id, websocket)


manager = ConnectionManager()
