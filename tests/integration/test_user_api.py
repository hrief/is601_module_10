import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRead
from main import app


@pytest.fixture
def user_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


DATA = {"username": "newuser", "email": "new@example.com", "password": "TestPass123!"}


def test_registration_login_and_profile(user_client, db_session):
    response = user_client.post("/users", json=DATA)
    assert response.status_code == 201
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    user = db_session.query(User).one()
    assert user.password_hash != DATA["password"]
    assert user.verify_password(DATA["password"])
    assert user.created_at is not None
    assert UserRead.model_validate(user).username == DATA["username"]
    login = user_client.post("/token", json={"username": DATA["username"], "password": DATA["password"]})
    assert login.status_code == 200
    profile = user_client.get("/users/me", headers={"Authorization": "Bearer " + login.json()["access_token"]})
    assert profile.status_code == 200
    assert profile.json()["id"] == response.json()["id"]
    denied = user_client.post("/token", json={"username": DATA["username"], "password": "wrong"})
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"
    assert user_client.get("/users/me").status_code == 401


@pytest.mark.parametrize("field", ["username", "email"])
def test_duplicate_response(user_client, field):
    assert user_client.post("/users", json=DATA).status_code == 201
    other = DATA | {"username": "otheruser", "email": "other@example.com"}
    other[field] = DATA[field]
    assert user_client.post("/users", json=other).status_code == 409


def test_invalid_email_does_not_persist(user_client, db_session):
    assert user_client.post("/users", json=DATA | {"email": "invalid"}).status_code == 400
    assert db_session.query(User).count() == 0


@pytest.mark.parametrize("field", ["username", "email"])
def test_database_enforces_unique_without_registration(db_session, field):
    first = User(**DATA)
    db_session.add(first)
    db_session.commit()
    other = DATA | {"username": "otheruser", "email": "other@example.com"}
    other[field] = DATA[field]
    db_session.add(User(**other))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(User).count() == 1
