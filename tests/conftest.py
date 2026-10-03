from src.models.base import Base
from src.database import engine
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session



TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session() -> Session: 
    """
    Создаёт async engine для тестовой SQLite БД.
    scope="session" — один engine на весь прогон тестов.

    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = TestingSessionLocal()
    yield session

    session.close()
    engine.dispose()
    

@pytest.fixture(scope="function")
def mock_redis() -> MagicMock:
    """
    Поддельный RedisService — не требует реального Redis-сервера.

    MagicMock(spec=RedisService) создаёт объект который:
    - Имеет все те же методы что и RedisService
    - Но они ничего не делают (возвращают MagicMock)
    - Мы настраиваем возвращаемые значения через .return_value

    Паттерн: Mock Object — заменяем внешние зависимости на контролируемые дубли.
    """
    mock = MagicMock(spec=RedisService)
    # Разумные дефолты
    mock.can_resend.return_value = True
    mock.get_cooldown_ttl.return_value = 0
    mock.get_otp.return_value = None
    mock.get_otp_ttl.return_value = -2
    return mock


@pytest.fixture(scope="function")
def user_repository() -> UserRepository:
    """Реальный репозиторий — работает с тестовой SQLite БД."""
    return UserRepository()


@pytest.fixture(scope="function")
def auth_service(user_repository, mock_redis) -> AuthService:
    """
    Реальный AuthService с реальным репозиторием и поддельным Redis.

    Это позволяет тестировать бизнес-логику (хеширование паролей, JWT)
    без зависимости от Redis-сервера.
    """
    return AuthService(
        user_repository=user_repository,
        redis_service=mock_redis,
    )


@pytest.fixture(scope="function")
def client(db_session, mock_redis):
    """
    Тестовый HTTP клиент FastAPI (синхронный TestClient).

    Ключевая техника — Dependency Override:
    FastAPI позволяет подменять зависимости в тестах.
    Мы подменяем get_db и get_redis_service на тестовые версии.
    """
    from starlette.testclient import TestClient

    # Переопределяем зависимости FastAPI на тестовые
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis_service] = lambda: mock_redis

    with TestClient(app) as test_client:
        yield test_client

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def registered_user(db_session) -> User:
    """
    Создаёт пользователя напрямую в БД (минуя HTTP и email верификацию).
    Пользователь НЕ активирован — is_active=False.

    Используй когда нужно протестировать логику,
    которая требует существующего юзера, но не активированного.
    """
    import bcrypt
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")

    user = User(
        name="Test User",
        email="test@example.com",
        password=hashed,
        role="user",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client, active_user) -> dict:
    """
    Возвращает заголовки авторизации для активного пользователя.

    Использование в тестах:
        def test_get_me(client, auth_headers):
            response = client.get("/auth/me", headers=auth_headers)
            assert response.status_code == 200
    """
    response = client.post(
        "/auth/token",
        data={"username": "active@example.com", "password": "TestPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}