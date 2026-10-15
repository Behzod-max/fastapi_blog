from app import models


def test_get_all_posts(client, test_posts):
    response = client.get("/posts/")

    assert response.status_code == 200
    assert len(response.json()) == len(test_posts)


def test_get_post(client, test_posts):
    response = client.get(f"/posts/{test_posts[0].id}")

    assert response.status_code == 200
    assert response.json()["id"] == test_posts[0].id
    assert response.json()["title"] == test_posts[0].title


def test_get_post_not_found(client):
    response = client.get("/posts/99999")

    assert response.status_code == 404


def test_create_post(authorized_client):
    response = authorized_client.post(
        "/posts/",
        json={
            "title": "Yangi post",
            "body": "Yangi kontent",
            "published": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Yangi post"
    assert data["body"] == "Yangi kontent"
    assert data["published"] is True
    assert "id" in data
    assert "owner_id" in data


def test_create_post_unauthorized(client):
    response = client.post(
        "/posts/",
        json={"title": "Post", "body": "Kontent"},
    )

    assert response.status_code == 401


def test_create_post_default_published(authorized_client):
    response = authorized_client.post(
        "/posts/",
        json={"title": "Post", "body": "Kontent"},
    )

    assert response.status_code == 201
    assert response.json()["published"] is True


def test_create_post_empty_title(authorized_client):
    response = authorized_client.post(
        "/posts/",
        json={"title": "", "body": "Kontent"},
    )

    assert response.status_code == 422


def test_create_post_long_title(authorized_client):
    response = authorized_client.post(
        "/posts/",
        json={"title": "A" * 256, "body": "Kontent"},
    )

    assert response.status_code == 422


def test_update_post(authorized_client, test_posts):
    response = authorized_client.put(
        f"/posts/{test_posts[0].id}",
        json={
            "title": "Yangilangan sarlavha",
            "body": "Yangilangan kontent",
            "published": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Yangilangan sarlavha"
    assert response.json()["body"] == "Yangilangan kontent"


def test_update_post_not_found(authorized_client):
    response = authorized_client.put(
        "/posts/99999",
        json={
            "title": "Yangilangan sarlavha",
            "body": "Yangilangan kontent",
            "published": True,
        },
    )

    assert response.status_code == 404


def test_update_other_user_post(authorized_client, db):
    other_user = models.User(
        username="other",
        email="other@example.com",
        password="irrelevant-hashed-password",
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_post = models.Post(
        title="Boshqaning posti",
        body="Kontent",
        owner_id=other_user.id,
    )
    db.add(other_post)
    db.commit()
    db.refresh(other_post)

    response = authorized_client.put(
        f"/posts/{other_post.id}",
        json={
            "title": "O'g'irlashga urindim",
            "body": "Kontent",
            "published": True,
        },
    )

    assert response.status_code == 403


def test_delete_post(authorized_client, test_posts):
    response = authorized_client.delete(f"/posts/{test_posts[0].id}")

    assert response.status_code == 204


def test_delete_post_check(authorized_client, test_posts):
    post_id = test_posts[0].id
    authorized_client.delete(f"/posts/{post_id}")
    response = authorized_client.get(f"/posts/{post_id}")

    assert response.status_code == 404


def test_delete_post_not_found(authorized_client):
    response = authorized_client.delete("/posts/99999")

    assert response.status_code == 404


def test_delete_other_user_post(authorized_client, db):
    other_user = models.User(
        username="other2",
        email="other2@example.com",
        password="irrelevant-hashed-password",
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_post = models.Post(
        title="Boshqaning posti",
        body="Kontent",
        owner_id=other_user.id,
    )
    db.add(other_post)
    db.commit()
    db.refresh(other_post)

    response = authorized_client.delete(f"/posts/{other_post.id}")

    assert response.status_code == 403


def test_get_posts_pagination(client, test_posts):
    first_page = client.get("/posts/?limit=2&skip=0")
    second_page = client.get("/posts/?limit=2&skip=2")

    assert first_page.status_code == 200
    assert len(first_page.json()) == 2
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1


def test_get_posts_search(client, test_posts):
    response = client.get("/posts/?search=Birinchi")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Birinchi post"


def test_create_post_without_token(client):
    response = client.post(
        "/posts/",
        json={"title": "Test post", "body": "Kontent"},
    )

    assert response.status_code == 401
