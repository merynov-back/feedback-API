import pytest
from pydantic import ValidationError

from src.schemas.auth import TokenResponse, VerifyEmailRequest
from src.schemas.user import UserCreate, UserRead

class TestUserCreate:
    """Группа тестов для схемы UserCreate."""

    def test_valid_user_create(self):
        """Корректные данные — схема должна создаться без ошибок."""
        user = UserCreate(
            name="Иван Петров",
            email="ivan@example.com",
            password="StrongPass1!",
        )
        assert user.name == "Иван Петров"
        assert user.email == "ivan@example.com"
        assert user.password == "StrongPass1!"

    def test_name_too_short(self):
        """Имя меньше 2 символов — должна быть ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="A", email="test@test.com", password="StrongPass1!")

        # Проверяем что ошибка именно в поле name
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_name_too_long(self):
        """Имя больше 100 символов — ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="А" * 101,
                email="test@test.com",
                password="StrongPass1!",
            )

    def test_invalid_email(self):
        """Невалидный email — ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(name="Иван", email="not-an-email", password="StrongPass1!")

    def test_password_too_short(self):
        """Пароль меньше 8 символов — ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(name="Иван", email="ivan@test.com", password="short")

    def test_password_too_long(self):
        """Пароль больше 128 символов — ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(name="Иван", email="ivan@test.com", password="A" * 129)

    def test_missing_required_fields(self):
        """Отсутствуют обязательные поля — ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate()  # type: ignore


class TestUserRead:
    """Группа тестов для схемы UserRead."""
    def test_valid_user_read(self):
        user = UserRead(
            id=1,
            name="Иван Петров",
            email="ivan@example.com",
            role="user",
            is_active=True,
        )
        assert user.id == 1
        assert user.role == "user"
        assert user.is_active is True

    def test_model_validate_from_orm(self):
        class FakeUser:
            id = 1
            name = "Абра Кадабра"
            email = "abra@gmail.com"
            is_active = False
            role = "admin"

        user_read = UserRead.model_validate(FakeUser())
        assert user_read.id == 1
        assert user_read.is_active is False
        assert user_read.role == "admin"


class TestVerifyEmailRequest:
    """Тесты для схемы верификации OTP-кода."""

    def test_valid_verify_request(self):
        """Корректный 6-значный код — схема создаётся."""
        req = VerifyEmailRequest(email="ivan@test.com", code="123456")
        assert req.code == "123456"

    def test_code_too_short(self):
        """Код меньше 6 цифр — ValidationError."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest(email="ivan@test.com", code="12345")

    def test_code_too_long(self):
        """Код больше 6 цифр — ValidationError."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest(email="ivan@test.com", code="1234567")

    def test_code_with_letters(self):
        """Буквы в коде — ValidationError (pattern требует только цифры)."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest(email="ivan@test.com", code="12345A")

    def test_code_with_spaces(self):
        """Пробелы в коде — ValidationError."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest(email="ivan@test.com", code="12 456")


class TestTokenResponse:
    """Тесты для схемы ответа с токеном."""

    def test_token_response_defaults(self):
        """Проверяем значения по умолчанию."""
        token = TokenResponse(access_token="123", refresh_token="456")
        assert token.token_type == "bearer"

    def test_test_token_response_all_fields(self):
        """Проверяем все поля."""
        token = TokenResponse(access_token="123", refresh_token="456", token_type="bearer")
        assert token.access_token == "123"
        assert token.refresh_token == "456"

    