from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Ответ при успешной аутентификации"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Данные, извлеченные из JWT-токена"""
    user_id: str
    role: str

class RefreshRequest(BaseModel):
    """Тело запроса для обновления Access Token"""
    refresh_token: str = Field(..., examples=["eyJhbGci..."])

class LoginRequest(BaseModel):
    """Альтернативная схема для JSON-логина (не OAuth2-форм)."""
    email: str = Field(..., examples=["ivan@example.com"])
    password: str = Field(..., min_length=8, examples=["strongPass1!"])
