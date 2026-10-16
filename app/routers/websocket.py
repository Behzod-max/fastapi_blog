
import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app import models
from app.config import settings
from app.database import SessionLocal

router = APIRouter(tags=["WebSocket"])


async def get_ws_user(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = payload.get("user_id")

        if user_id is None:
            return None

    except JWTError:
        return None

    db = SessionLocal()
    try:
        return db.query(models.User).filter(
            models.User.id == user_id
        ).first()
    finally:
        db.close()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.active_connections.setdefault(room, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        connections = self.active_connections.get(room, [])

        if websocket in connections:
            connections.remove(websocket)

        if not connections and room in self.active_connections:
            del self.active_connections[room]

    def get_room_count(self, room: str) -> int:
        return len(self.active_connections.get(room, []))

    async def broadcast(self, message: str, room: str):
        connections = self.active_connections.get(room, [])

        for connection in list(connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection, room)


manager = ConnectionManager()


@router.websocket("/ws/chat/{room}")
async def chat_endpoint(
    websocket: WebSocket,
    room: str,
    token: str = "",
):
    # Access Token tekshiriladi
    if not token:
        await websocket.close(code=1008, reason="Token required")
        return

    user = await get_ws_user(token)

    if user is None:
        await websocket.close(code=1008, reason="Invalid token")
        return

    username = user.username

    await manager.connect(websocket, room)

    try:
        # Xonaga kirgan foydalanuvchilar soni
        await manager.broadcast(
            json.dumps({
                "type": "system",
                "message": f"{username} xonaga qo'shildi",
                "users_count": manager.get_room_count(room),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }),
            room,
        )

        # Xabarlarni qabul qilish va barcha xonadoshlarga yuborish
        while True:
            message = await websocket.receive_text()
            message = message.strip()

            if not message:
                continue

            await manager.broadcast(
                json.dumps({
                    "type": "message",
                    "username": username,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).strftime(
                        "%H:%M:%S"
                    ),
                }),
                room,
            )

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(websocket, room)

        await manager.broadcast(
            json.dumps({
                "type": "system",
                "message": f"{username} xonadan chiqdi",
                "users_count": manager.get_room_count(room),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }),
            room,
        )