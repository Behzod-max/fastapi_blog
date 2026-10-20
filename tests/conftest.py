import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from app.routers import posts as posts_router
from app.routers import websocket as websocket_router
from app.routers import users as users_router


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db, monkeypatch):
    async def skip_email(*args, **kwargs):
        return None

    monkeypatch.setattr(users_router, "send_welcome_email", skip_email)
    monkeypatch.setattr(posts_router, "send_post_notification", skip_email)
    monkeypatch.setattr(websocket_router, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user(client):
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201

    user = response.json()
    user["password"] = user_data["password"]
    return user


@pytest.fixture
def token(client, test_user):
    response = client.post(
        "/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def authorized_client(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def test_posts(db, test_user):
    posts = [
        models.Post(
            title="Birinchi post",
            body="Birinchi kontent",
            published=True,
            owner_id=test_user["id"],
        ),
        models.Post(
            title="Ikkinchi post",
            body="Ikkinchi kontent",
            published=True,
            owner_id=test_user["id"],
        ),
        models.Post(
            title="Uchinchi post",
            body="Uchinchi kontent",
            published=False,
            owner_id=test_user["id"],
        ),
    ]
    db.add_all(posts)
    db.commit()

    return db.query(models.Post).order_by(models.Post.id).all()
