# Feedback API — что сейчас происходит в проекте

Снимок фактического состояния репозитория. В отличие от `ARCHITECTURE.md`
(который местами описывает *желаемую/будущую* архитектуру с сущностями, которых в коде ещё нет)
здесь фиксируется только то, что реально есть в файлах сейчас.

## Что уже реализовано

Проект — REST API на FastAPI с JWT-аутентификацией и OTP-верификацией email. Реализован модуль `auth`:

- `POST /auth/register` — регистрация (email + пароль, хэш через bcrypt/passlib). Пользователь
  создаётся неактивным (`is_active=False`), на почту уходит письмо с 6-значным OTP-кодом.
- `POST /auth/verify-email` — подтверждение email по коду, активирует аккаунт и сразу выдаёт
  access/refresh токены.
- `POST /auth/resend-verification` — повторная отправка кода с cooldown (защита от спама) и
  единым ответом независимо от того, существует email или нет (защита от enumeration).
- `POST /auth/token` — вход (OAuth2 password flow), выдаёт access + refresh токены.
- `POST /auth/refresh` — обновление access-токена по refresh-токену.
- `GET /auth/me` — данные текущего пользователя.

Слоистая архитектура (API → Service → Repository), как описано в `api-service-repository.md`:
- `src/routers/auth.py` — контроллеры.
- `src/services/auth_service.py` — бизнес-логика, JWT (через `python-jose`), хэширование паролей,
  генерация и проверка OTP-кода (`hmac.compare_digest`), делегирует хранение кода `RedisService`
  и отправку письма Celery-задаче `send_verification_email`.
- `src/services/redis_service.py` — новый сервис: хранение OTP-кода и cooldown повторной отправки
  в Redis через `setex`, с TTL из конфига (`OTP_TTL_SECONDS`, `OTP_RESEND_COOLDOWN_SECONDS`).
- `src/tasks/email_tasks.py` — сборка MIME-письма (`_build_verification_email`); HTML-шаблон вынесен
  в отдельный файл `src/templates/verification_email.html` и подставляется через `str.format()`.
- `src/repositories/{base_repository,user_repository}.py` — доступ к БД через SQLAlchemy 2.0
  (`Mapped`/`mapped_column`).
- `src/models/user.py` — таблица `users` (id, name, email, password, role, is_active).
- `src/models/category/category.py` — новая модель `Category` (id, name, description, is_active),
  роутеров/схем/репозитория под неё пока нет — только таблица.
- `src/schemas/{auth,user}.py` — Pydantic-схемы, включая `VerifyEmailRequest`/`ResendVerificationRequest`.
- `src/dependencies/auth.py` — DI: сессия БД, текущий пользователь, `require_role(...)` для ролей.

Инфраструктура (`docker-compose.yml`): Postgres, Redis, Celery worker и Flower добавлены как сервисы.

Сущности `Feedback` и `Reply` из `ARCHITECTURE.md` в коде всё ещё не существуют. Несмотря на название
проекта "Feedback API", самой обратной связи в системе пока нет — реализована авторизация и (частично)
категории.

Миграции: Alembic переехал из `alembic/` в `migrations/`. Есть миграция создания таблицы `users`
и миграция `is_active` default false.

## Известные баги в текущем коде

1. **Несогласованные импорты — приложение, вероятно, не запускается.**
   `src/main.py` и `migrations/env.py` импортируют с префиксом `src.` (`from src.routers.auth import ...`),
   а `src/dependencies/auth.py`, `src/repositories/*.py`, `src/routers/auth.py`, `src/services/auth_service.py`
   вперемешку используют голые импорты (`from database import engine`, `from models.user import User`),
   хотя эти модули физически лежат в `src/`. При запуске `uvicorn src.main:app` из корня проекта такие
   импорты упадут с `ModuleNotFoundError`.

2. **`get_auth_service` не передаёт `redis_service`.** `AuthService.__init__` теперь требует
   `(user_repository, redis_service)`, но `src/dependencies/auth.py` всё ещё создаёт
   `AuthService(user_repository)` без второго аргумента — `TypeError` при любом запросе к `/auth/*`.

3. **Celery-задача `send_verification_email` не существует.** `auth_service.py` импортирует её из
   `src.tasks.email_tasks`, но в этом файле определена только вспомогательная функция
   `_build_verification_email` — самой задачи (декоратор `@celery_app.task`, отправка через SMTP) нет.

4. **Модуль `src.celery_app` отсутствует.** `docker-compose.yml` запускает
   `celery -A src.celery_app worker` и `celery -A src.celery_app flower`, но файла `src/celery_app.py`
   с инициализацией `Celery(...)` в проекте нет — контейнеры `celery_worker`/`flower` не поднимутся.

5. **`settings.EMAILS_FROM_NAME` / `EMAILS_FROM_EMAIL` не определены в `Settings`.**
   `email_tasks.py` на них ссылается, а в `src/config.py` таких полей нет — `AttributeError` при сборке письма.

6. **Опечатка в `src/database.py:6`** — `sessionmaker(auticommit=False, ...)` вместо `autocommit`.
   В SQLAlchemy 2.0 `sessionmaker` вообще не принимает `autocommit`, так что лишний неизвестный
   параметр (`auticommit`) приведёт к ошибке при создании `SessionLocal`.

7. **`src/routers/_init__.py`** — файл называется `_init__.py` (один underscore в начале), а не
   `__init__.py`. Пакет `src/routers` формально не размечен как положено (хотя пока работает,
   потому что `main.py` импортирует `auth.py` напрямую, а не через пакет).

8. **`src/main.py` CORS-настройки бессмысленны**: `allow_origins=[""]` и `allow_methods=[""]` —
   пустая строка не матчит ни один origin/метод, то есть CORS фактически ничего не разрешает,
   несмотря на `allow_credentials=True`.

9. **`Dockerfile` не имеет отношения к приложению** — образ `ubuntu:latest` с `ENTRYPOINT ["top", "-b"]`.
   Похоже на заготовку/плейсхолдер, а не рабочий образ для FastAPI-сервиса.

10. **`SessionLocal` не используется** — весь код (`get_db` в `dependencies/auth.py`) открывает сессии
    через `Session(engine)` напрямую, а не через фабрику `SessionLocal` из `database.py`.

## Что дальше (по `ARCHITECTURE.md`)

Прежде чем расширять функциональность до модели `Feedback` (категории, статусы, ответы администраторов),
стоит закрыть баги выше — особенно несогласованные импорты и отсутствующие `celery_app`/
`send_verification_email`, из-за которых приложение и фоновая отправка писем в текущем виде,
вероятно, не работают.
