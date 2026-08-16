from datetime import timedelta, datetime, timezone
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.auth import TokenData, TokenResponse
from src.schemas.user import UserCreate, UserRead
from src.services.redis_service import RedisService
from src.config import settings
from passlib.context import CryptContext
import hmac
import secrets
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, user_repository: UserRepository, redis_service: RedisService):
        self.user_repository = user_repository
        self.redis_service = redis_service

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
            return TokenData(user_id=int(user_id_str), role=role)

        except JWTError as exc:
            raise ValueError(f"Не валидный или истекший JWT-токен: {exc}") from exc

    def build_token_response(self, user_id: int, role: str) -> TokenResponse:
        return TokenResponse(
            access_token=self.create_access_token(user_id=user_id, role=role),
            refresh_token=self.create_refresh_token(user_id=user_id, role=role),
        )

    """Бизнес логика: регистрация и аутентификация"""

    def register_user(self, db: Session, data: UserCreate) -> UserRead:
        from src.tasks.email_tasks import send_verification_email

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
        
        code = str(secrets.randbelow(1000000)).zfill(6)
        self.redis_service.set_otp(data.email, code)

        self.redis_service.set_resend_cooldown(data.email)

        send_verification_email.delay(user_email=user.email, user_name=user.name, otp_code=code)
        
        logger.info(
            "Новый пользователь зарегистрирован (pending verification): id=%d email=%s",
            user.id,
            user.email,
        )
        
    def verify_email_code(self, db: Session, email: str, code: str) -> TokenResponse:
        user = self.user_repository.get_by_email(db, email)

        if user is None:
            raise ValueError("Неверный код верификации")

        if user.is_active:
            raise ValueError("Email уже подтвержден. Войдите в аккаунт")
        
        stored_code = self.redis_service.get_otp(email)

        if stored_code is None:
            raise ValueError("Код верификации истек. Запросите новый /auth/resend-verification") 
        
        if not hmac.compare_digest(stored_code, code):
            raise ValueError("Неверный код верификации")
        
        self.user_repository.update(db, user, {"is_active": True})
        self.redis_service.delete_otp(email)
        
        
        logger.info(
            "Пользователь подтвердил email (active): id=%d email=%s",
            user.id,
            user.email,
        )
        
        return self.build_token_response(user.id, user.role)

    def resend_verification_code(self, db: Session, email: str) -> None:
        from src.tasks.email_tasks import send_verification_email

        user = self.user_repository.get_by_email(db, email)

        if user is not None and user.is_active:
            raise ValueError("Email уже подтвержден, войдите в аккаунт.")

        if not self.redis_service.can_resend(email):
            cooldown_left = self.redis_service.get_cooldown_ttl(email)
            raise ValueError(f"Повторная попытка доступна через {cooldown_left} секунд.")
        
        if user is not None:
            code = str(secrets.randbelow(1000000)).zfill(6)
            self.redis_service.set_otp(email, code)
            self.redis_service.set_resend_cooldown(email)

            send_verification_email.delay(user_email=user.email, user_name=user.name, otp_code=code)
        
            logger.info(
                "Отправлен повторный код верификации: id=%d email=%s",
                user.id,
                user.email,
            )
            
        return 0

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        user = self.user_repository.get_by_email(db, email)

        if not user or not user.password:
            raise ValueError("Неверный email или пароль")

        if not self.verify_password(password, user.password):
            raise ValueError("Неверный email или пароль")

        if not user.is_active:
            raise ValueError("Аккаунт деактивирован, обратитесь к администратору")

        return user
