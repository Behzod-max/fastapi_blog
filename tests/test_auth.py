from jose import jwt

from app.config import settings


def test_login(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"],
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_token_valid(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"],
        },
    )
    payload = jwt.decode(
        response.json()["access_token"],
        settings.secret_key,
        algorithms=[settings.algorithm],
    )

    assert payload.get("user_id") == test_user["id"]


def test_login_wrong_password(client, test_user):
    response = client.post(
        "/login",
        data={"username": test_user["email"], "password": "NOTO'G'RI_PAROL"},
    )

    assert response.status_code == 403


def test_login_wrong_email(client):
    response = client.post(
        "/login",
        data={"username": "yoq@example.com", "password": "password123"},
    )

    assert response.status_code == 403


def test_login_missing_password(client):
    response = client.post("/login", data={"username": "ali@example.com"})

    assert response.status_code == 422


def test_create_post_with_invalid_token(client):
    response = client.post(
        "/posts/",
        headers={"Authorization": "Bearer invalid-token"},
        json={"title": "Post", "body": "Kontent"},
    )

    assert response.status_code == 401


def test_create_post_with_token_without_user_id(client):
    token = jwt.encode(
        {"sub": "missing-user-id"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    response = client.post(
        "/posts/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Post", "body": "Kontent"},
    )

    assert response.status_code == 401
