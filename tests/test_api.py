from unittest.mock import MagicMock, patch
class TestHealthCheck:

    def test_root_endpoint_returns_200(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_status_ok(self, test_client):
        response = test_client.get("/")
        data = response.json()
        assert data.get("status") == "ok"
        
    def test_root_endpoint_has_message(self, test_client):
        response = test_client.get("/")
        data = response.json()
        assert "message" in data


class TestRegisterEndpoint:
    def test_register_new_user_returns_201(self, test_client):
        with patch("src.tasks.email_tasks.send_verification_email") as mock_task:
            mock_task.delay = MagicMock()

            response = test_client.post("/auth/register", json={
                "email" : "email@gmail.com",
                "password": "password123",
                "name": "John Doe"
            })
        
        assert response.status_code == 201

    def test_register_returns_message(self, test_client):
        with patch("src.tasks.email_tasks.send_verification_email") as mock_task:
            mock_task.delay = MagicMock()

            response = test_client.post("/auth/register", json={
                "email" : "email@gmail.com",
                "password": "password123",
                "name": "John Doe"
            })

        data = response.json()
        assert "message" in data

    def test_register_dublicate_email_returns_409(self, test_client, registered_user):
        with patch("src.tasks.email_tasks.send_verification_email") as mock_task:
            mock_task.delay = MagicMock()

            response = test_client.post("/auth/register", json={
                "email" : "email@gmail.com",
                "password": "password123",
                "name": "John Boy"
            })
            
        assert response.status_code == 409

    def test_register_invalid_email_returns_422(self, test_client):
        response = test_client.post("/auth/register", json={
            "email" : "invalid-email",
            "password": "password123",
            "name": "John Doe"
        })

        assert response.status_code == 422

    def test_register_short_password_returns_422(self, test_client):
        response = test_client.post("/auth/register", json={
            "email" : "email@gmail.com",
            "password": "short",
            "name": "John Doe"
        })

        assert response.status_code == 422
        
    def test_register_missing_name_returns_422(self, test_client):
        response = test_client.post("/auth/register", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })

        assert response.status_code == 422


class TestLoginEndpoint:
    def test_login_active_user_returns_200(self, test_client, active_user):
        response = test_client.post("/auth/token", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })

        assert response.status_code == 200

    def test_login_returns_tokens(self, test_client, active_user):
        response = test_client.post("/auth/token", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, test_client, active_user):
        response = test_client.post("/auth/token", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })

        assert response.status_code == 401
    
    def test_login_non_existent_user_returns_401(self, test_client):
        response = test_client.post("/auth/token", json={
            "email" : "non_existent@gmail.com",
            "password": "password123",
        })

        assert response.status_code == 401

    def test_login_inactive_user_returns_401(self, test_client, registered_user):
        response = test_client.post("/auth/token", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })

        assert response.status_code == 401

class TestMeEndpoint:
    """Тестируем GET /auth/me — требует авторизации."""

    def test_get_me_with_valid_token_returns_200(self, client, auth_headers):
        """
        GET /auth/me с валидным Bearer токеном — 200 OK.
        auth_headers — фикстура которая автоматически логинится и возвращает заголовки.
        """
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200

    def test_get_me_returns_user_data(self, client, auth_headers, active_user):
        """Ответ /auth/me содержит данные пользователя."""
        response = client.get("/auth/me", headers=auth_headers)
        data = response.json()

        assert data["email"] == "active@example.com"
        assert data["name"] == "Active User"
        assert data["role"] == "user"
        assert data["is_active"] is True
        # Проверяем что пароль НЕ возвращается (это критично для безопасности!)
        assert "password" not in data

    def test_get_me_without_token_returns_401(self, client):
        """GET /auth/me без токена — 401 Unauthorized."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_with_invalid_token_returns_401(self, client):
        """GET /auth/me с невалидным токеном — 401."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_get_me_with_malformed_header_returns_401(self, client):
        """Неправильный формат заголовка (без 'Bearer ') — 401."""
        headers = {"Authorization": "invalid_format"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# POST /auth/verify-email — Верификация email
# ═════════════════════════════════════════════════════════════════════════════

class TestVerifyEmailEndpoint:
    """Тестируем POST /auth/verify-email."""

    def test_verify_correct_code_returns_200(self, client, registered_user, mock_redis):
        """
        Правильный OTP-код → 200 OK + токены.
        mock_redis настроен вернуть код "123456".
        """
        mock_redis.get_otp.return_value = "123456"

        response = client.post(
            "/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "123456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_verify_wrong_code_returns_400(self, client, registered_user, mock_redis):
        """Неправильный код → 400 Bad Request."""
        mock_redis.get_otp.return_value = "123456"

        response = client.post(
            "/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "999999",  # неверный
            },
        )
        assert response.status_code == 400

    def test_verify_expired_code_returns_410(self, client, registered_user, mock_redis):
        """Истёкший код (Redis вернул None) → 410 Gone."""
        mock_redis.get_otp.return_value = None  # TTL истёк

        response = client.post(
            "/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "123456",
            },
        )
        assert response.status_code == 410

    def test_verify_already_active_returns_409(self, client, active_user, mock_redis):
        """Уже активированный пользователь → 409 Conflict."""
        response = client.post(
            "/auth/verify-email",
            json={
                "email": "active@example.com",
                "code": "123456",
            },
        )
        assert response.status_code == 409

    def test_verify_invalid_code_format_returns_422(self, client):
        """Код не из 6 цифр → 422 Unprocessable Entity (Pydantic)."""
        response = client.post(
            "/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "ABC",  # буквы — не валидно
            },
        )
        assert response.status_code == 422

class TestUpdateToken:
    def test_refresh_with_valid_token_returns_200(self, client, active_user):
        login_response = client.post("/auth/token", json={
            "email" : "email@gmail.com",
            "password": "password123",
        })
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token_returns_401(self, client):
        response = client.post("/auth/refresh", json={
            "refresh_token": "invalid_token"
        })
        assert response.status_code == 401
        

    