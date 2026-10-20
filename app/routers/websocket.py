import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import SessionLocal, get_db
from app.oauth2 import get_current_user

router = APIRouter(tags=["WebSocket"])
MAX_MESSAGE_LENGTH = 2000


async def get_ws_user(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = payload.get("user_id")
        if type(user_id) is not int or user_id < 1:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        return db.query(models.User).filter(models.User.id == user_id).first()
    finally:
        db.close()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[int, set[WebSocket]] = {}
        self.connection_users: Dict[WebSocket, tuple[int, str]] = {}
        self.connection_rooms: Dict[WebSocket, str] = {}
        self.usernames: Dict[int, str] = {}

    async def connect(self, websocket: WebSocket, room: str, user: models.User):
        await websocket.accept()
        self.active_connections.setdefault(room, []).append(websocket)
        self.user_connections.setdefault(user.id, set()).add(websocket)
        self.connection_users[websocket] = (user.id, user.username)
        self.connection_rooms[websocket] = room
        self.usernames[user.id] = user.username

    def disconnect(self, websocket: WebSocket):
        room = self.connection_rooms.pop(websocket, None)
        if room is None:
            return
        connections = self.active_connections.get(room, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(room, None)

        user = self.connection_users.pop(websocket, None)
        if user is not None:
            user_id = user[0]
            user_connections = self.user_connections.get(user_id, set())
            user_connections.discard(websocket)
            if not user_connections:
                self.user_connections.pop(user_id, None)
                self.usernames.pop(user_id, None)

    def get_room_count(self, room: str) -> int:
        return len(self.active_connections.get(room, []))

    def get_online_users(self) -> list[dict[str, int | str]]:
        return [
            {"id": user_id, "username": self.usernames[user_id]}
            for user_id, connections in sorted(self.user_connections.items())
            if connections
        ]

    async def broadcast(
        self,
        message: str,
        room: str,
        exclude: WebSocket | None = None,
    ):
        for connection in list(self.active_connections.get(room, [])):
            if connection is exclude:
                continue
            try:
                await connection.send_text(message)
            except (RuntimeError, WebSocketDisconnect):
                self.disconnect(connection)

    async def send_to_user(self, user_id: int, message: str) -> bool:
        connections = list(self.user_connections.get(user_id, set()))
        if not connections:
            return False

        delivered = False
        for connection in connections:
            try:
                await connection.send_text(message)
                delivered = True
            except (RuntimeError, WebSocketDisconnect):
                self.disconnect(connection)
        return delivered


manager = ConnectionManager()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


async def _authenticated_user(websocket: WebSocket, token: str):
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.origins_list:
        await websocket.close(code=1008, reason="Origin not allowed")
        return None
    if not token:
        await websocket.close(code=1008, reason="Token required")
        return None
    user = await get_ws_user(token)
    if user is None:
        await websocket.close(code=1008, reason="Invalid token")
    return user


@router.websocket("/ws/chat/{room}")
async def chat_endpoint(
    websocket: WebSocket,
    room: str,
    token: str = "",
):
    user = await _authenticated_user(websocket, token)
    if user is None:
        return

    room = room.strip()
    if not room or len(room) > 100:
        await websocket.close(code=1008, reason="Invalid room")
        return

    await manager.connect(websocket, room, user)
    try:
        await manager.broadcast(
            json.dumps({
                "type": "system",
                "message": f"{user.username} xonaga qo'shildi",
                "users_count": manager.get_room_count(room),
                "timestamp": _timestamp(),
            }),
            room,
        )

        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                payload = None

            if isinstance(payload, dict) and payload.get("type") == "typing":
                is_typing = payload.get("is_typing", True)
                if not isinstance(is_typing, bool):
                    continue
                await manager.broadcast(
                    json.dumps({
                        "type": "typing",
                        "username": user.username,
                        "is_typing": is_typing,
                    }),
                    room,
                    exclude=websocket,
                )
                continue

            if isinstance(payload, dict):
                if payload.get("type") != "message":
                    continue
                message = payload.get("message", "")
            else:
                message = raw_message

            if not isinstance(message, str):
                continue
            message = message.strip()
            if not message:
                continue
            if len(message) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Xabar {MAX_MESSAGE_LENGTH} belgidan oshmasin",
                })
                continue

            db = SessionLocal()
            try:
                db.add(models.Message(room=room, username=user.username, content=message))
                db.commit()
            finally:
                db.close()

            await manager.broadcast(
                json.dumps({
                    "type": "message",
                    "username": user.username,
                    "message": message,
                    "timestamp": _timestamp(),
                }),
                room,
            )

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        await manager.broadcast(
            json.dumps({
                "type": "system",
                "message": f"{user.username} xonadan chiqdi",
                "users_count": manager.get_room_count(room),
                "timestamp": _timestamp(),
            }),
            room,
        )


@router.websocket("/ws/dm/{target_user_id}")
async def direct_message(
    websocket: WebSocket,
    target_user_id: int,
    token: str = Query(...),
):
    user = await _authenticated_user(websocket, token)
    if user is None:
        return
    if target_user_id == user.id:
        await websocket.close(code=1008, reason="Cannot send a direct message to yourself")
        return

    db = SessionLocal()
    try:
        target = db.query(models.User).filter(models.User.id == target_user_id).first()
        target_username = target.username if target is not None else None
    finally:
        db.close()
    if target_username is None:
        await websocket.close(code=1008, reason="Target user not found")
        return

    room = f"dm:{user.id}"
    await manager.connect(websocket, room, user)
    try:
        while True:
            message = (await websocket.receive_text()).strip()
            if not message:
                continue
            if len(message) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Xabar {MAX_MESSAGE_LENGTH} belgidan oshmasin",
                })
                continue

            delivered = await manager.send_to_user(
                target_user_id,
                json.dumps({
                    "type": "direct_message",
                    "from_user_id": user.id,
                    "from_username": user.username,
                    "message": message,
                    "timestamp": _timestamp(),
                }),
            )
            await websocket.send_json({
                "type": "direct_message_status",
                "to_user_id": target_user_id,
                "delivered": delivered,
                "detail": (
                    f"{target_username} ga xabar yuborildi"
                    if delivered
                    else f"{target_username} hozir online emas"
                ),
            })
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@router.get("/ws/rooms/{room}/history", response_model=list[schemas.MessageResponse])
def get_room_history(
    room: str,
    limit: int = Query(default=50, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    normalized_room = room.strip()
    if not normalized_room or len(normalized_room) > 100:
        raise HTTPException(status_code=400, detail="Xona nomi noto'g'ri")

    messages = (
        db.query(models.Message)
        .filter(models.Message.room == normalized_room)
        .order_by(models.Message.created_at.desc(), models.Message.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


@router.get("/ws/online")
def get_online_users():
    users = manager.get_online_users()
    return {"users": users, "count": len(users)}
