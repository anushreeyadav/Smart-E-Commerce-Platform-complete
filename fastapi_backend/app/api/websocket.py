from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import SessionLocal
from app.models.user import User
from app.services.connection_manager import manager


router = APIRouter()


@router.websocket("/ws/notifications")
async def notification_websocket(
    websocket: WebSocket,
):
    token = websocket.query_params.get("token")
    user_id: str | None = None

    if not token:
        await websocket.close(code=1008)
        return

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")

    if not user_id:
        await websocket.close(code=1008)
        return

    db: Session = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )
    finally:
        db.close()

    if not user:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    manager.add_connection(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove_connection(user_id, websocket)
