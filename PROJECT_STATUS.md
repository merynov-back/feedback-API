# Feedback API — что сейчас происходит в проекте

Снимок фактического состояния репозитория на 2026-07-28. В отличие от `ARCHITECTURE.md`
(который местами описывает *желаемую/будущую* архитектуру с сущностями, которых в коде ещё нет)
здесь фиксируется только то, что реально есть в файлах сейчас.

## Что уже реализовано

Проект — REST API на FastAPI с JWT-аутентификацией. Реализован только модуль `auth`:

- `POST /auth/register` — регистрация (email + пароль, хэш через bcrypt/passlib)
- `POST /auth/token` — вход (OAuth2 password flow), выдаёт access + refresh токены
- `POST /auth/refresh` — обновление access-токена по refresh-токену
- `GET /auth/me` — данные текущего пользователя

Слоистая архитектура (API → Service → Repository), как описано в `api-service-repository.md`:
- `src/routers/auth.py` — контроллеры
- `src/services/auth_service.py` — бизнес-логика, JWT (через `python-jose`), хэширование паролей
- `src/repositories/{base_repository,user_repository}.py` — доступ к БД через SQLAlchemy 2.0 (`Mapped`/`mapped_column`)
- `src/models/user.py` — единственная модель, таблица `users` (id, name, email, password, role, is_active)
- `src/schemas/{auth,user}.py` — Pydantic-схемы
- `src/dependencies/auth.py` — DI: сессия БД, текущий пользователь, `require_role(...)` для ролей

Сущности из `ARCHITECTURE.md` — `Feedback`, `Category`, `Reply` — **в коде не существуют**.
Их нет ни в `src/models`, ни в `src/routers`, ни в `src/schemas`. Несмотря на название проекта
"Feedback API", самой обратной связи в системе пока нет — реализована только авторизация пользователей.

Миграции: Alembic переехал из папки `alembic/` в `migrations/` (в git status старая папка удалена,
новая ещё не закоммичена). Есть одна миграция — создание таблицы `users`.

## Известные баги в текущем коде

1. **Несогласованные импорты — приложение, вероятно, не запускается.**
   `src/main.py` и `migrations/env.py` импортируют с префиксом `src.` (`from src.routers.auth import ...`),
   а `src/dependencies/auth.py`, `src/repositories/*.py`, `src/routers/auth.py`, `src/services/auth_service.py`
   вперемешку используют голые импорты (`from database import engine`, `from models.user import User`),
   хотя эти модули физически лежат в `src/`. При запуске `uvicorn src.main:app` из корня проекта такие
   импорты упадут с `ModuleNotFoundError`.

2. **Опечатка в `src/database.py:6`** — `sessionmaker(auticommit=False, ...)` вместо `autocommit`.
   В SQLAlchemy 2.0 `sessionmaker` вообще не принимает `autocommit`, так что лишний неизвестный
   параметр (`auticommit`) приведёт к ошибке при создании `SessionLocal`.

3. **`src/routers/_init__.py`** — файл называется `_init__.py` (один underscore в начале), а не
   `__init__.py`. Пакет `src/routers` формально не размечен как положено (хотя пока работает,
   потому что `main.py` импортирует `auth.py` напрямую, а не через пакет).

4. **`src/main.py` CORS-настройки бессмысленны**: `allow_origins=[""]` и `allow_methods=[""]` —
   пустая строка не матчит ни один origin/метод, то есть CORS фактически ничего не разрешает,
   несмотря на `allow_credentials=True`.

5. **`Dockerfile` не имеет отношения к приложению** — образ `ubuntu:latest` с `ENTRYPOINT ["top", "-b"]`.
   Похоже на заготовку/плейсхолдер, а не рабочий образ для FastAPI-сервиса.

6. **`SessionLocal` не используется** — весь код (`get_db` в `dependencies/auth.py`) открывает сессии
   через `Session(engine)` напрямую, а не через фабрику `SessionLocal` из `database.py`.

## Незакоммиченные изменения (`git status`)

- Удалена старая папка `alembic/` (README, env.py, script.py.mako, первая версия миграции) —
  заменена на `migrations/` с новым `alembic.ini` в корне.
- Изменены: `docker-compose.yml`, `src/models/user.py`, `src/services/auth_service.py`.
- Новые неотслеживаемые файлы: `.gitignore`, `alembic.ini`, `migrations/`, `postman/`, `.postman/`,
  `api-service-repository.md`, `help.txt`.
- `help.txt` и `api-service-repository.md` — по содержанию это личные конспекты (про Alembic,
  хэширование, Docker Compose, слоистую архитектуру), а не документация проекта как такового.

## Что дальше (по `ARCHITECTURE.md`)

Согласно плану в `ARCHITECTURE.md`, следующие шаги — реализация самой модели `Feedback`
(с категориями, статусами, ответами администраторов) и подключение соответствующих роутеров.
Но прежде чем расширять функциональность, стоит закрыть баги выше — особенно несогласованные
импорты, из-за которых приложение в текущем виде, вероятно, не стартует.