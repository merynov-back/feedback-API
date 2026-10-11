# Feedback API

REST API системы обратной связи с регистрацией по email, подтверждением через OTP-код и JWT-аутентификацией. В комплекте — веб-интерфейс на Next.js.

**Стек:** FastAPI · PostgreSQL · SQLAlchemy + Alembic · Redis · Celery + Flower · Next.js 16 · Docker Compose

---

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Сервисы и порты](#сервисы-и-порты)
- [Переменные окружения](#переменные-окружения)
- [Как работает авторизация](#как-работает-авторизация)
- [API](#api)
- [Разработка без Docker](#разработка-без-docker)
- [Тесты](#тесты)
- [Миграции](#миграции)
- [Структура проекта](#структура-проекта)
- [Полезные команды](#полезные-команды)

---

## Быстрый старт

Нужен только **Docker** с Compose.

**1. Создай `.env`** в корне проекта (шаблон — в разделе [Переменные окружения](#переменные-окружения)).

**2. Подними все сервисы:**

```bash
docker compose up -d --build
```

**3. Примени миграции** (один раз и после каждой новой миграции):

```bash
docker compose exec api alembic upgrade head
```

> `alembic.ini` не хранится в репозитории (он в `.gitignore`). Если его нет — создай командой `alembic init migrations` и пропиши `script_location = %(here)s/migrations`. Адрес БД Alembic берёт из `.env`, сам `sqlalchemy.url` в файле не используется.

**4. Открой:**

- Фронтенд — http://localhost:3000
- Swagger — http://localhost:8000/docs

Готово.

---

## Сервисы и порты

| Сервис | Контейнер | Адрес | Назначение |
|---|---|---|---|
| `frontend` | `feedback-frontend` | http://localhost:3000 | Веб-интерфейс (Next.js) |
| `api` | `feedback-api` | http://localhost:8000 | REST API (FastAPI) |
| `postgres` | `feedback` | `localhost:5433` | База данных |
| `redis` | `feedback-redis` | `localhost:6379` | OTP-коды и брокер Celery |
| `celery_worker` | `feedback-celery-worker` | — | Фоновая отправка писем |
| `flower` | `feedback-flower` | http://localhost:5555 | Мониторинг задач Celery |

Документация API: [Swagger UI](http://localhost:8000/docs) · [ReDoc](http://localhost:8000/redoc)

---

## Переменные окружения

Файл `.env` в корне проекта. Он в `.gitignore` — никогда не коммить его.

```dotenv
# --- PostgreSQL ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=feedback

# Адрес БД для запуска без Docker (в Docker подставляется автоматически)
BASE_URL=postgresql://postgres:postgres@localhost:5433/feedback

# --- JWT ---
JWT_SECRET_KEY=замени-на-длинную-случайную-строку
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# --- Redis / Celery (для запуска без Docker) ---
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# --- OTP ---
OTP_TTL_SECONDS=900                # срок жизни кода, сек
OTP_RESEND_COOLDOWN_SECONDS=120    # пауза между повторными отправками, сек

# --- SMTP (отправка кодов на почту) ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=пароль-приложения
EMAILS_FROM_NAME=Feedback API
EMAILS_FROM_EMAIL=you@gmail.com
```

> Сгенерировать `JWT_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
>
> Для Gmail в `SMTP_PASSWORD` нужен [пароль приложения](https://myaccount.google.com/apppasswords), а не обычный пароль от аккаунта.

В Docker Compose переменные `BASE_URL`, `REDIS_URL` и `CELERY_*` переопределяются на адреса внутри сети контейнеров — менять их для Docker не нужно.

---

## Как работает авторизация

```
Регистрация ──► письмо с 6-значным кодом ──► подтверждение email ──► вход ──► JWT
```

1. **Регистрация** — `POST /auth/register`. Аккаунт создаётся неактивным, Celery отправляет код на почту.
2. **Подтверждение** — `POST /auth/verify-email` с кодом. Код живёт 15 минут, хранится в Redis. Если не пришёл — `POST /auth/resend-verification` (не чаще раза в 2 минуты).
3. **Вход** — `POST /auth/token`, возвращает `access_token` и `refresh_token`.
4. **Запросы** — заголовок `Authorization: Bearer <access_token>`.
5. **Обновление** — когда access-токен истёк, `POST /auth/refresh` с refresh-токеном.

Во фронтенде это страницы `/register` → `/verify` → `/login` → `/dashboard`.

---

## API

| Метод | Путь | Тело | Описание |
|---|---|---|---|
| `GET` | `/` | — | Health check |
| `POST` | `/auth/register` | JSON: `name`, `email`, `password` | Регистрация (пароль от 8 символов) |
| `POST` | `/auth/verify-email` | JSON: `email`, `code` | Подтверждение email, возвращает токены |
| `POST` | `/auth/resend-verification` | JSON: `email` | Повторная отправка кода |
| `POST` | `/auth/token` | **form-data**: `username` (email), `password` | Вход, возвращает токены |
| `POST` | `/auth/refresh` | JSON: `refresh_token` | Новая пара токенов |
| `GET` | `/auth/me` | — 🔒 | Данные текущего пользователя |

🔒 — нужен заголовок `Authorization: Bearer <access_token>`.

<details>
<summary><b>Пример через curl</b></summary>

```bash
# Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Ivan Petrov", "email": "ivan@example.com", "password": "StrongPass1!"}'

# Подтверждение (код — из письма)
curl -X POST http://localhost:8000/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "ivan@example.com", "code": "123456"}'

# Вход — обрати внимание: form-data, email передаётся как username
curl -X POST http://localhost:8000/auth/token \
  -d "username=ivan@example.com&password=StrongPass1!"

# Профиль
curl http://localhost:8000/auth/me -H "Authorization: Bearer <access_token>"
```

</details>

Готовые запросы для Postman лежат в папке [`postman/`](postman/).

---

## Разработка без Docker

Удобно, когда правишь код и хочешь быстрый перезапуск. Postgres и Redis при этом проще оставить в Docker:

```bash
docker compose up -d postgres redis
```

### Бэкенд

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
uvicorn src.main:app --reload            # API на :8000
```

В отдельном терминале — воркер для отправки писем:

```bash
celery -A src.celery_app worker --loglevel=info
```

### Фронтенд

```bash
cd frontend
npm install
npm run dev                              # http://localhost:3000
```

Адрес API задан в [`frontend/src/services/api.ts`](frontend/src/services/api.ts) (`http://localhost:8000`).

---

## Тесты

Тесты используют SQLite в памяти и моки Redis — Postgres и Redis для них не нужны, но `.env` должен существовать.

```bash
source .venv/bin/activate
pip install pytest pytest-asyncio httpx   # тестовые зависимости, их нет в requirements.txt
pytest -v
```

| Файл | Что проверяет |
|---|---|
| `tests/test_api.py` | Эндпоинты целиком |
| `tests/test_services.py` | Бизнес-логику `AuthService` |
| `tests/test_repositories.py` | Работу с БД |
| `tests/test_schemas.py` | Валидацию Pydantic-схем |

> `pytest.ini` тоже не хранится в репозитории. Если его нет — создай с содержимым:
>
> ```ini
> [pytest]
> asyncio_mode = auto
> testpaths = tests
> ```

---

## Миграции

```bash
# Создать миграцию после изменения моделей
docker compose exec api alembic revision --autogenerate -m "описание изменений"

# Применить
docker compose exec api alembic upgrade head

# Откатить последнюю
docker compose exec api alembic downgrade -1
```

Без Docker — те же команды без `docker compose exec api`.

---

## Структура проекта

```
feedback-API/
├── src/
│   ├── main.py              # Точка входа FastAPI, CORS, роутеры
│   ├── config.py            # Настройки из .env
│   ├── database.py          # Подключение к БД
│   ├── celery_app.py        # Конфигурация Celery
│   ├── routers/             # HTTP-эндпоинты
│   ├── services/            # Бизнес-логика (auth, redis)
│   ├── repositories/        # Доступ к БД
│   ├── models/              # SQLAlchemy-модели
│   ├── schemas/             # Pydantic-схемы
│   ├── dependencies/        # Зависимости FastAPI (БД, текущий пользователь)
│   └── tasks/               # Задачи Celery (отправка писем)
├── migrations/              # Миграции Alembic
├── tests/                   # Pytest
├── postman/                 # Коллекции Postman
├── frontend/
│   ├── src/app/             # Страницы: login, register, verify, dashboard
│   ├── src/components/      # Формы
│   ├── src/services/api.ts  # HTTP-клиент к бэкенду
│   └── Dockerfile
├── Dockerfile               # Образ бэкенда (api, celery, flower)
├── docker-compose.yml
└── requirements.txt
```

---

## Полезные команды

```bash
docker compose ps                        # статус контейнеров
docker compose logs -f api               # логи сервиса в реальном времени
docker compose up -d --build frontend    # пересобрать один сервис
docker compose restart celery_worker     # перезапустить сервис
docker compose down                      # остановить всё
docker compose down -v                   # остановить и удалить данные БД и Redis ⚠️
```

Подключиться к базе:

```bash
docker compose exec postgres psql -U postgres -d feedback
```

---

## Частые проблемы

**Письмо с кодом не приходит.** Проверь `docker compose logs celery_worker` и SMTP-настройки в `.env`. Для Gmail нужен пароль приложения.

**`relation "users" does not exist`.** Не применены миграции — выполни `alembic upgrade head`.

**Фронтенд не может достучаться до API.** Убедись, что `api` запущен (`curl http://localhost:8000/`) и порт 8000 свободен.

**Порт уже занят.** Поменяй левую часть в `ports` в `docker-compose.yml`, например `"3001:3000"`.
