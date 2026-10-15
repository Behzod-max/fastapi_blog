def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "username": "ali",
            "email": "ali@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ali@example.com"
    assert data["username"] == "ali"
    assert "password" not in data
    assert "id" in data
    assert "created_at" in data


def test_create_user_duplicate_email(client):
    user = {
        "username": "ali",
        "email": "ali@example.com",
        "password": "password123",
    }
    client.post("/users/", json=user)
    response = client.post(
        "/users/",
        json={**user, "username": "vali", "password": "password456"},
    )

    assert response.status_code == 400
    assert "allaqachon" in response.json()["detail"]


def test_create_user_invalid_email(client):
    response = client.post(
        "/users/",
        json={
            "username": "ali",
            "email": "bu-email-emas",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_get_user(client, test_user):
    response = client.get(f"/users/{test_user['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]
    assert response.json()["username"] == test_user["username"]


def test_get_user_not_found(client):
    response = client.get("/users/99999")

    assert response.status_code == 404


def test_get_current_user(authorized_client, test_user):
    response = authorized_client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]


def test_get_current_user_unauthorized(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_change_password(authorized_client, client, test_user):
    response = authorized_client.put(
        "/users/me/password",
        json={
            "old_password": test_user["password"],
            "new_password": "yangi_parol_123",
        },
    )

    assert response.status_code == 200
    login_response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": "yangi_parol_123",
        },
    )
    assert login_response.status_code == 200


def test_change_password_wrong_old_password(authorized_client):
    response = authorized_client.put(
        "/users/me/password",
        json={"old_password": "wrong", "new_password": "new-password"},
    )

    assert response.status_code == 403


def test_change_password_unauthorized(client):
    response = client.put(
        "/users/me/password",
        json={"old_password": "password123", "new_password": "new-password"},
    )

    assert response.status_code == 401
