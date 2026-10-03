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

    