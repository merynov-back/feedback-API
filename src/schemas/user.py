from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """Регистрация нового пользователя"""
    name: str = Field(..., min_length=2, max_length=100, examples=["Ivan Petrov"])
    email: EmailStr = Field(..., examples=["ivan@exampl.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["StrongPass1!"])

class UserUpdate(BaseModel):
    """Обновление профиля пользователя"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

class UserRead(BaseModel):
    """Публичные данные пользователя"""
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    model_config = {"from_attributes": True}





