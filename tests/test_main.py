from sqlalchemy.exc import SQLAlchemyError


def test_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Blog API"
    assert response.json()["version"]


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_health_check_database_unavailable(client, monkeypatch, db):
    def fail_execute(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(db, "execute", fail_execute)
    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
