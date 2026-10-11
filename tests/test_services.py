# test_services.py - Unit тесты для бизнес-логики (AuthService).

# ЧТО ТЕСТИРУЕМ: чистую бизнес-логику без HTTP и без БД.
# УРОВЕНЬ: Unit - используем реальный AuthService, но с моками зависимостей.
# ПАТТЕРН: Arrange -> Act -> Assert (AAA)

# Arrange  = готовим данные и моки
# Act      = вызываем тестируемый метод
# Assert   = проверяем результат

"""
test_services.py — Unit тесты для бизнес-логики (AuthService).

ЧТО ТЕСТИРУЕМ: чистую бизнес-логику без HTTP и без БД.
УРОВЕНЬ: Unit — используем реальный AuthService, но с моками зависимостей.
ПАТТЕРН: Arrange → Act → Assert (AAA)

Arrange  = готовим данные и моки
Act      = вызываем тестируемый метод
Assert   = проверяем результат

Запуск только этого файла:
    pytest src/tests/test_services.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.auth_service import AuthService
from src.models.user import User


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: хеширование паролей
# ═════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    """
    Тестируем статические методы hash_password и verify_password.
    Это чистые функции — не нужны никакие фикстуры.
    """

    def test_hash_password_returns_string(self):
        """hash_password должен вернуть строку (bcrypt хеш)."""
        hashed = AuthService.hash_password("MyPassword123!")
        assert isinstance(hashed, str)

    def test_hash_is_different_from_original(self):
        """Хеш не должен совпадать с исходным паролем."""
        password = "MyPassword123!"
        hashed = AuthService.hash_password(password)
        assert hashed != password

    def test_same_password_different_hashes(self):
        """
        bcrypt добавляет случайную соль — каждый хеш уникален.
        Это критично для безопасности: если БД утечёт,
        злоумышленник не может использовать rainbow tables.
        """
        hashed1 = AuthService.hash_password("MyPassword123!")
        hashed2 = AuthService.hash_password("MyPassword123!")
        assert hashed1 != hashed2  # разные соли → разные хеши

    def test_verify_correct_password(self):
        """Правильный пароль должен успешно верифицироваться."""
        password = "MyPassword123!"
        hashed = AuthService.hash_password(password)
        assert AuthService.verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Неправильный пароль должен провалить верификацию."""
        hashed = AuthService.hash_password("CorrectPassword!")
        assert AuthService.verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_vs_hashed(self):
        """Пустая строка против реального хеша — False."""
        hashed = AuthService.hash_password("RealPassword123!")
        assert AuthService.verify_password("", hashed) is False


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: JWT токены
# ═════════════════════════════════════════════════════════════════════════════

class TestJWTTokens:
    """
    Тестируем создание и декодирование JWT.
    Нужен auth_service (фикстура из conftest.py).
    """

    def test_create_access_token_returns_string(self, auth_service):
        """create_access_token должен вернуть строку."""
        token = auth_service.create_access_token(user_id=1, role="user")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_returns_string(self, auth_service):
        """create_refresh_token должен вернуть строку."""
        token = auth_service.create_refresh_token(user_id=1, role="admin")
        assert isinstance(token, str)

    def test_decode_valid_access_token(self, auth_service):
        """Декодирование корректного токена возвращает правильные данные."""
        token = auth_service.create_access_token(user_id=42, role="admin")
        token_data = auth_service.decode_token(token)

        assert token_data.user_id == 42
        assert token_data.role == "admin"

    def test_decode_valid_refresh_token(self, auth_service):
        """Декодирование refresh токена возвращает правильные данные."""
        token = auth_service.create_refresh_token(user_id=7, role="moderator")
        token_data = auth_service.decode_token(token)

        assert token_data.user_id == 7
        assert token_data.role == "moderator"

    def test_decode_invalid_token_raises(self, auth_service):
        """Невалидный токен должен поднять ValueError."""
        with pytest.raises(ValueError):
            auth_service.decode_token("this.is.not.a.jwt")

    def test_decode_tampered_token_raises(self, auth_service):
        """Изменённый токен (подделка) должен поднять ValueError."""
        token = auth_service.create_access_token(user_id=1, role="user")
        # Добавляем символ в конец — подпись становится невалидной
        tampered = token + "X"
        with pytest.raises(ValueError):
            auth_service.decode_token(tampered)

    def test_build_token_response(self, auth_service):
        """build_token_response должен вернуть оба токена."""
        response = auth_service.build_token_response(user_id=1, role="user")

        assert response.access_token
        assert response.refresh_token
        assert response.token_type == "bearer"
        # access и refresh должны быть разными токенами
        assert response.access_token != response.refresh_token


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: бизнес-логика регистрации
# ═════════════════════════════════════════════════════════════════════════════

class TestRegisterUser:
    """
    Тестируем register_user().
    Используем реальную БД (db_session) и mock Redis.
    """

    def test_register_new_user_success(self, auth_service, db_session, mock_redis):
        """
        Регистрация нового пользователя — должна пройти без ошибок.

        Проверяем:
        1. Метод не поднимает исключений
        2. Redis вызван (OTP сохранён)
        3. Celery вызван (письмо отправлено)
        """
        from src.schemas.user import UserCreate

        data = UserCreate(
            name="Новый Пользователь",
            email="newuser@test.com",
            password="StrongPass123!",
        )

        # patch Celery задачи чтобы не пытались реально отправить письмо
        # Патчим по полному пути модуля где задача определена
        with patch("src.tasks.email_tasks.send_verification_email") as mock_celery:
            mock_celery.delay = MagicMock()
            auth_service.register_user(db_session, data)

        # Redis должен был вызвать set_otp (сохранить код)
        mock_redis.set_otp.assert_called_once()

        # Redis должен был вызвать set_resend_cooldown
        mock_redis.set_resend_cooldown.assert_called_once()

    def test_register_duplicate_email_raises(self, auth_service, db_session, registered_user):
        """
        Повторная регистрация с тем же email — ValueError.
        registered_user уже создан в БД через фикстуру.
        """
        from src.schemas.user import UserCreate

        data = UserCreate(
            name="Другой Пользователь",
            email="test@example.com",  # этот email уже занят (registered_user)
            password="AnotherPass123!",
        )

        with pytest.raises(ValueError, match="уже существует"):
            auth_service.register_user(db_session, data)


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: аутентификация
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthenticateUser:
    """Тестируем authenticate_user() — проверку логина/пароля."""

    def test_authenticate_active_user_success(self, auth_service, db_session, active_user):
        """Активный пользователь с правильным паролем — успех."""
        user = auth_service.authenticate_user(
            db_session,
            email="active@example.com",
            password="TestPass123!",
        )
        assert user.id == active_user.id
        assert user.email == "active@example.com"

    def test_authenticate_wrong_password(self, auth_service, db_session, active_user):
        """Неправильный пароль — ValueError."""
        with pytest.raises(ValueError, match="Неверный email или пароль"):
            auth_service.authenticate_user(
                db_session,
                email="active@example.com",
                password="WrongPassword!",
            )

    def test_authenticate_nonexistent_email(self, auth_service, db_session):
        """Несуществующий email — ValueError (не раскрываем что именно неверно)."""
        with pytest.raises(ValueError, match="Неверный email или пароль"):
            auth_service.authenticate_user(
                db_session,
                email="nobody@test.com",
                password="SomePassword!",
            )

    def test_authenticate_inactive_user(self, auth_service, db_session, registered_user):
        """
        Неактивированный пользователь (is_active=False) — ValueError.
        registered_user создан с is_active=False.
        """
        with pytest.raises(ValueError, match="не активирован"):
            auth_service.authenticate_user(
                db_session,
                email="test@example.com",
                password="TestPass123!",
            )


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: верификация email
# ═════════════════════════════════════════════════════════════════════════════

class TestVerifyEmailCode:
    """Тестируем verify_email_code() — проверку OTP кода."""

    def test_verify_correct_code_activates_user(
        self, auth_service, db_session, registered_user, mock_redis
    ):
        """
        Правильный OTP-код — пользователь активируется и возвращаются токены.
        Настраиваем mock_redis чтобы он вернул правильный код.
        """
        mock_redis.get_otp.return_value = "123456"

        tokens = auth_service.verify_email_code(
            db_session,
            email="test@example.com",
            code="123456",
        )

        assert tokens.access_token
        assert tokens.refresh_token

        # Проверяем что пользователь стал активным в БД
        db_session.refresh(registered_user)
        assert registered_user.is_active is True

        # Redis должен был удалить код после использования
        mock_redis.delete_otp.assert_called_once_with("test@example.com")

    def test_verify_wrong_code_raises(
        self, auth_service, db_session, registered_user, mock_redis
    ):
        """Неправильный код — ValueError."""
        mock_redis.get_otp.return_value = "123456"

        with pytest.raises(ValueError, match="Неверный код"):
            auth_service.verify_email_code(
                db_session,
                email="test@example.com",
                code="999999",  # неверный код
            )

    def test_verify_expired_code_raises(
        self, auth_service, db_session, registered_user, mock_redis
    ):
        """
        Код истёк (Redis вернул None) — ValueError с сообщением об истечении.
        Redis автоматически удаляет ключи после TTL → get_otp возвращает None.
        """
        mock_redis.get_otp.return_value = None  # TTL истёк

        with pytest.raises(ValueError, match="истек"):
            auth_service.verify_email_code(
                db_session,
                email="test@example.com",
                code="123456",
            )

    def test_verify_already_active_user_raises(
        self, auth_service, db_session, active_user, mock_redis
    ):
        """Уже активированный пользователь — ValueError."""
        with pytest.raises(ValueError, match="уже подтвержден"):
            auth_service.verify_email_code(
                db_session,
                email="active@example.com",
                code="123456",
            )