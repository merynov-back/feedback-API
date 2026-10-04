from src.repositories.user_repository import UserRepository
from src.models.user import User
import pytest
from pytest_asyncio import fixture
from typing import Generator


class TestBaseRepository:
    """
    Тестируем BaseRepository через UserRepository (наследует BaseRepository[User]).
    Это тестирует CRUD методы: create, get_by_id, get_all, update, delete.
    """

    def test_create_user(self, db_session):
        """create() должен добавить запись в БД и вернуть объект с id."""
        repo = UserRepository()

        user = repo.create(db_session, {
            "name": "Тест Создания",
            "email": "create@test.com",
            "password": "hashed_password",
            "role": "user",
            "is_active": False,
        })

        # После create объект должен получить id (автоинкремент)
        assert user.id is not None
        assert user.id > 0
        assert user.name == "Тест Создания"
        assert user.email == "create@test.com"

    def test_get_by_id_existing(self, db_session, registered_user):
        """get_by_id() должен найти существующего пользователя."""
        repo = UserRepository()

        found = repo.get_by_id(db_session, registered_user.id)

        assert found is not None
        assert found.id == registered_user.id
        assert found.email == registered_user.email

    def test_get_by_id_nonexistent(self, db_session):
        """get_by_id() с несуществующим id должен вернуть None."""
        repo = UserRepository()

        result = repo.get_by_id(db_session, 99999)

        assert result is None

    def test_get_all_returns_list(self, db_session, registered_user, active_user):
        """
        get_all() должен вернуть список пользователей.
        В тесте есть registered_user и active_user — итого 2 пользователя.
        """
        repo = UserRepository()

        users = repo.get_all(db_session)

        assert isinstance(users, list)
        assert len(users) >= 2  # как минимум наши два юзера

    def test_get_all_with_limit(self, db_session, registered_user, active_user):
        """get_all() с limit=1 должен вернуть не больше 1 записи."""
        repo = UserRepository()

        users = repo.get_all(db_session, limit=1)

        assert len(users) <= 1

    def test_update_user(self, db_session, registered_user):
        """update() должен изменить атрибуты объекта в БД."""
        repo = UserRepository()

        updated = repo.update(db_session, registered_user, {
            "name": "Обновлённое Имя",
            "is_active": True,
        })

        assert updated.name == "Обновлённое Имя"
        assert updated.is_active is True

        # Проверяем что изменения действительно сохранились в БД
        refetched = repo.get_by_id(db_session, registered_user.id)
        assert refetched.name == "Обновлённое Имя"

    def test_delete_existing_user(self, db_session):
        """delete() должен удалить пользователя и вернуть его."""
        repo = UserRepository()

        # Создаём пользователя специально для удаления
        user = repo.create(db_session, {
            "name": "Удаляемый",
            "email": "todelete@test.com",
            "password": "pass",
            "role": "user",
            "is_active": False,
        })
        user_id = user.id

        deleted = repo.delete(db_session, user_id)

        # Метод должен вернуть удалённый объект
        assert deleted is not None
        assert deleted.id == user_id

        # Теперь в БД этого пользователя нет
        assert repo.get_by_id(db_session, user_id) is None

    def test_delete_nonexistent_user(self, db_session):
        """delete() несуществующего id должен вернуть None (не падать)."""
        repo = UserRepository()

        result = repo.delete(db_session, 99999)

        assert result is None