from typing import Generator, Callable
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from starlette import status
from src.database import engine
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.services.auth_service import AuthService
from src.services.redis_service import RedisService
from src.dependencies.redis import get_redis_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def get_user_repository() -> UserRepository:
    return UserRepository()

def get_auth_service(
        user_repository: UserRepository = Depends(get_user_repository),
        redis_service: RedisService = Depends(get_redis_service)
) -> AuthService:
    return AuthService(user_repository, redis_service)


"""Зависимость: текущий пользователь из JWT"""
def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
        user_repository: UserRepository = Depends(get_user_repository)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        token_data = auth_service.decode_token(token)
    except ValueError:
        raise credentials_exception

    user = user_repository.get_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception

    return user

def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    return current_user

def require_role(
        *roles: str
) -> Callable:
    """
    Фабрика FastAPI-зависимостей для проверки роли пользователя.

    Пример использования:
        @router.delete("/users/{id}", dependencies=[Depends(require_role("admin"))])
    """
    def role_checker(
            current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется роль: {', '.join(roles)}"
            )
        return current_user
    return role_checker

