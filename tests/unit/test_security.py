import pytest
from pydantic import ValidationError
from app.security import hash_password, verify_password
from app.schemas.user import UserCreate, UserRead
from app.models.user import User


def test_salted_hash_and_verification():
    first = hash_password("TestPass123!")
    second = hash_password("TestPass123!")
    assert first != second
    assert first.startswith("$argon2id$")
    assert verify_password("TestPass123!", first)
    assert not verify_password("incorrect", first)
    assert not verify_password("TestPass123!", "invalid-hash")


@pytest.mark.parametrize("changes", [
    {"email": "not-an-email"}, {"username": "ab"},
    {"password": "short"}, {"password": "x" * 129},
    {"password": None}, {"password": 12345},
])
def test_invalid_create(changes):
    data = {"username": "validuser", "email": "user@example.com", "password": "TestPass123!"}
    with pytest.raises(ValidationError):
        UserCreate(**(data | changes))


def test_password_required():
    with pytest.raises(ValidationError):
        UserCreate(username="validuser", email="user@example.com")


def test_read_schema_has_no_secrets():
    assert "password_hash" not in UserRead.model_fields
    assert "password" not in UserRead.model_fields
    assert "password_hash" in User.__table__.columns
    assert "password" not in User.__table__.columns
