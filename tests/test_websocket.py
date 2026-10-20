import pytest
from starlette.websockets import WebSocketDisconnect


def _register_and_login(client, username, email):
    response = client.post(
        "/users/",
        json={
            "username": username,
            "email": email,
            "password": "password123",
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_chat_persists_messages_and_returns_recent_history(
    authorized_client, token
):
    with authorized_client.websocket_connect(
        f"/ws/chat/general?token={token}"
    ) as websocket:
        assert websocket.receive_json()["type"] == "system"
        websocket.send_text("Hello room")
        message = websocket.receive_json()

    assert message["type"] == "message"
    assert message["message"] == "Hello room"
    history = authorized_client.get("/ws/rooms/general/history")
    assert history.status_code == 200
    assert history.json()[0]["content"] == "Hello room"


def test_typing_and_online_user_events(client, token, test_user):
    second_token = _register_and_login(
        client,
        username="seconduser",
        email="second@example.com",
    )
    with client.websocket_connect(f"/ws/chat/general?token={token}") as first:
        first.receive_json()
        with client.websocket_connect(
            f"/ws/chat/general?token={second_token}"
        ) as second:
            first.receive_json()
            second.receive_json()
            first.send_json({"type": "typing", "username": "forged"})
            typing_event = second.receive_json()

            assert typing_event == {
                "type": "typing",
                "username": test_user["username"],
                "is_typing": True,
            }
            online = client.get("/ws/online")
            assert online.status_code == 200
            assert online.json()["count"] == 2
            assert {item["username"] for item in online.json()["users"]} == {
                "testuser",
                "seconduser",
            }


def test_direct_message_delivers_to_target_user(client, token, test_user):
    target_token = _register_and_login(
        client,
        username="recipient",
        email="recipient@example.com",
    )
    target_id = client.get("/users/2").json()["id"]
    with client.websocket_connect(
        f"/ws/chat/general?token={target_token}"
    ) as recipient:
        recipient.receive_json()
        with client.websocket_connect(
            f"/ws/dm/{target_id}?token={token}"
        ) as sender:
            sender.send_text("Private hello")
            received = recipient.receive_json()
            status = sender.receive_json()

    assert received["type"] == "direct_message"
    assert received["from_username"] == test_user["username"]
    assert received["message"] == "Private hello"
    assert status["type"] == "direct_message_status"
    assert status["delivered"] is True


def test_direct_message_reports_offline_target(client, token, test_user):
    _register_and_login(client, username="offline", email="offline@example.com")
    with client.websocket_connect(
        "/ws/dm/2?token=" + token
    ) as sender:
        sender.send_text("Are you there?")
        status = sender.receive_json()

    assert status["type"] == "direct_message_status"
    assert status["delivered"] is False


def test_websocket_rejects_untrusted_origin(client, token):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            f"/ws/chat/general?token={token}",
            headers={"origin": "https://untrusted.example"},
        ) as websocket:
            websocket.receive_text()

    assert error.value.code == 1008
