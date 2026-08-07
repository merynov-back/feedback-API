from pydantic import BaseModel, Field, EmailStr


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

class VerifyEmailRequest(BaseModel):
    """Тело запроса для подтверждения email по OTP-коду"""
    email: EmailStr = Field(..., examples=["ivan@example.com"])
    code: str = Field(..., min_length=4, max_length=8, examples=["123456"])

class ResendVerificationRequest(BaseModel):
    """Тело запроса для повторной отправки кода подтверждения email"""
    email: EmailStr = Field(..., examples=["ivan@example.com"])

class MessageResponse(BaseModel):
    """Универсальный ответ с текстовым сообщением"""
    message: str = Field(..., examples=["Письмо с подтверждением отправлено"])
