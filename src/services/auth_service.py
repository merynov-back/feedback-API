from datetime import timedelta, datetime, timezone
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from models.user import User
from repositories.user_repository import UserRepository
from schemas.auth import TokenData, TokenResponse
from schemas.user import UserCreate, UserRead
from src.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)


    def _create_token(self, data: dict, expire_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expire_delta
        to_encode.update({"exp": expire, "iat": datetime.now(tz=timezone.utc)})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_access_token(self, user_id: int, role: str) -> str:
        return self._create_token(
            data={"sub": str(user_id), "role": role, "type": "access"},
            expire_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

    def create_refresh_token(self, user_id: int, role: str) -> str:
        return self._create_token(
            data={"sub": str(user_id), "role": role, "type": "refresh"},
            expire_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    def decode_token(self, token: str) -> TokenData:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id_str: Optional[str] = payload.get("sub")
            role: Optional[str] = payload.get("role")

            if user_id_str is None or role is None:
                raise ValueError("Токен не содержит обязательных полей 'sub', 'role'")
            return TokenData(user_id=user_id_str, role=role)

        except JWTError as exc:
            raise ValueError(f"Не валидный или истекший JWT-токен: {exc}") from exc

    def build_token_response(self, user_id: int, role: str) -> TokenResponse:
        return TokenResponse(
            access_token=self.create_access_token(user_id=user_id, role=role),
            refresh_token=self.create_refresh_token(user_id=user_id, role=role),
        )

    """Бизнес логика: регистрация и аутентификация"""

    def register_user(self, db: Session, data: UserCreate) -> UserRead:
        existing = self.user_repository.get_by_email(db, data.email)
        if existing:
            raise ValueError(f"Пользователь с email {data.email} уже существует")

        user_in = {
            "name": data.name,
            "email": data.email,
            "password": self.hash_password(data.password),
            "role": "user"
        }
        user = self.user_repository.create(db, user_in)
        return UserRead.model_validate(user)

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        user = self.user_repository.get_by_email(db, email)

        if not user or not user.password:
            raise ValueError("Неверный email или пароль")

        if not self.verify_password(password, user.password):
            raise ValueError("Неверный email или пароль")

        if not user.is_active:
            raise ValueError("Аккаунт деактивирован, обратитесь к администратору")

        return user
