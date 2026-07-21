from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status
from dependencies.auth import get_db, get_auth_service, get_current_active_user, get_user_repository
from models.user import User
from repositories.user_repository import UserRepository
from schemas.auth import TokenResponse, RefreshRequest
from schemas.user import UserRead, UserCreate
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["🔑 Auth"])

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register(
        data: UserCreate,
        db: Session = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service)
):
    try:
        user = auth_service.register_user(db, data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Вход и получение JWT-токена"
)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service)
):
    try:
        user = auth_service.authenticate_user(db, email=form_data.username, password=form_data.password)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_service.build_token_response(user.id, user.role)

@router.get(
    "/me",
    response_model=UserRead,
    summary="Данные текущего авторизованого пользователя"
)
async def get_me(
        current_user: User = Depends(get_current_active_user)
):
    return UserRead.model_validate(current_user)

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновить access-токен через refresh-токен"
)
async def refresh_token(
        body: RefreshRequest,
        db: Session = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
        user_repository: UserRepository = Depends(get_user_repository)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не валидный или истекший refresh-токен",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        token_data = auth_service.decode_token(body.refresh_token)

    except ValueError:
        raise credentials_exception
    user = user_repository.get_by_id(db, token_data.user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return auth_service.build_token_response(user.id, user.role)


