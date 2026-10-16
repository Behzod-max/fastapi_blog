
from app.database import get_db


def test_get_db_closes_session(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    monkeypatch.setattr(
        "app.database.SessionLocal",
        lambda: fake_session,
    )

    db_generator = get_db()
    db = next(db_generator)

    assert db is fake_session
    assert fake_session.closed is False

    try:
        next(db_generator)
    except StopIteration:
        pass

    assert fake_session.closed is True
