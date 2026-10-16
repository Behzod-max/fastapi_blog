def test_change_password(authorized_client, test_user):
    response = authorized_client.put(
        "/users/me/password",
        json={
            "old_password": test_user["password"],
            "new_password": "yangi_parol_123"
        }
    )
    assert response.status_code == 200