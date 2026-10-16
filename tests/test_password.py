def test_get_current_user(authorized_client, test_user):
    response = authorized_client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]

def test_get_current_user_unauthorized(client):
    response = client.get("/users/me")
    assert response.status_code == 401