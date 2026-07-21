# Архитектура проекта Feedback API

Этот документ содержит подробный анализ текущей архитектуры проекта, выявленные ошибки/недочеты в кодовой базе и детальный план расширения архитектуры базы данных, связей и API.

---

## 1. Текущая архитектура проекта

### Структура каталогов
```text
feedback-API/
├── alembic/                  # Миграции базы данных (Alembic)
│   └── versions/             # Файлы версий миграций
├── src/                      # Исходный код приложения
│   ├── models/               # SQLAlchemy модели (база данных)
│   ├── routers/              # Эндпоинты FastAPI (контроллеры)
│   ├── schemas/              # Pydantic модели (валидация данных)
│   ├── config.py             # Настройки приложения (Pydantic Settings)
│   ├── database.py           # Инициализация подключения к БД (Engine)
│   └── main.py               # Точка входа приложения FastAPI
├── .env                      # Конфигурационные переменные окружения
├── docker-compose.yml        # Контейнеризация PostgreSQL базы данных
├── Dockerfile                # Инструкция сборки Docker-образа проекта
└── requirements.txt          # Список зависимостей проекта (в данный момент пуст)
```

### Технологический стек
*   **Язык**: Python 3.10+
*   **Веб-фреймворк**: FastAPI
*   **ORM**: SQLAlchemy 2.0 (используется новый декларативный стиль с `Mapped` и `mapped_column`)
*   **Миграции**: Alembic
*   **База данных**: PostgreSQL 15 (развертывается через Docker Compose)
*   **Безопасность**: bcrypt (для хеширования паролей)
*   **Валидация конфигурации**: Pydantic v2 & Pydantic Settings

---

## 2. Анализ текущего состояния и критические проблемы (Баги)

В ходе анализа текущей кодовой базы были обнаружены следующие архитектурные несоответствия и ошибки, которые приведут к сбоям при запуске или масштабировании:

### ⚠️ Ошибка связи Foreign Key в `src/models/feedback.py`
В модели `Feedback` связь с пользователем объявлена следующим образом:
```python
user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
```
Однако в модели `User` (`src/models/user.py`) имя таблицы задано как:
```python
__tablename__ = 'users'  # Во множественном числе
```
**Проблема**: При попытке SQLAlchemy связать таблицы или при генерации новой миграции Alembic возникнет ошибка `NoReferencedTableError`, так как таблицы с именем `user` не существует (есть `users`).
**Решение**: Исправить на `ForeignKey('users.id')`.

### ⚠️ Ошибка вычисления времени в `src/models/feedback.py`
Поля дат созданы так:
```python
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
```
**Проблема**: `datetime.now()` вызывается ровно **один раз** — в момент импорта файла при старте сервера. Все последующие записи фидбеков будут получать абсолютно одинаковое время создания и обновления (время запуска приложения).
**Решение**: Передавать саму функцию в качестве коллбека `default=datetime.now` (без скобок) или использовать функции базы данных `server_default=sa.func.now()`.

### ⚠️ Несоответствие типов данных поля `rating`
В модели `Feedback`:
```python
rating: Mapped[str] = mapped_column(String, default=0)
```
**Проблема**: Тип поля объявлен как `String` (строка), но значение по умолчанию задано как `0` (число).
**Решение**: Логичнее сделать поле рейтинга числовым (`Integer` или `Float`) для возможности математического вычисления среднего рейтинга (например, средняя оценка 4.5), либо изменить `default` на строку `"0"`.

### ⚠️ Ошибки импорта и структуры в `src/main.py`
```python
from src.routers.user import router as feedback_router
...
app.include_router(feedback_router)
```
**Проблема**: Роутер пользователей импортируется под именем `feedback_router`. Это создает путаницу в коде. Эндпоинты обратной связи (`routers/feedback.py`) в данный момент отсутствуют и никак не подключены.

### ⚠️ Пустые файлы заглушек
*   `requirements.txt` пуст. Для развертывания проекта необходимо зафиксировать зависимости (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic-settings`, `bcrypt`, `psycopg2-binary`).
*   `src/routers/feedback.py` и `src/schemas/feedback.py` полностью пусты, функционал работы с отзывами через API еще не реализован.
*   Таблица `feedback` не создана в миграциях Alembic (в папку миграций добавлено только создание таблицы `users`).

---

## 3. Текущие классы моделей SQLAlchemy (После исправления ошибок)

Ниже представлены актуальные и исправленные Python-классы SQLAlchemy, которые уже есть в проекте:

### Класс User (`src/models/user.py`)
```python
from typing import List
from sqlalchemy import String, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship
from src.models.base import Base

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    
    # Связи
    feedbacks: Mapped[List["Feedback"]] = relationship(back_populates="user")
```

### Класс Feedback (`src/models/feedback.py`)
```python
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base

class Feedback(Base):
    __tablename__ = 'feedback'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Связи
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    user: Mapped["User"] = relationship(back_populates="feedbacks")
```

---

## 4. Перспективная архитектура моделей SQLAlchemy (Что будет составлять далее)

Для создания полноценной корпоративной системы обработки обратной связи предлагается расширить архитектуру, добавив **категории отзывов**, **статусы обработки**, **ответы администраторов** и **систему авторизации**.

### Новые сущности и таблицы:

1. **`categories` (Категории отзывов)**
   * Позволяет группировать отзывы (например: *"Баги"*, *"Предложения по улучшению"*, *"Вопросы по оплате"*, *"Общие вопросы"*).
   * Связь с `feedback`: **Один-ко-многим** (одна категория может содержать много отзывов).

2. **`replies` (Ответы администраторов на отзывы)**
   * Хранит ответы сотрудников на полученную обратную связь.
   * Связь с `feedback`: **Один-ко-многим** (для поддержки переписки/треда обсуждения на один отзыв).
   * Связь с `users`: **Многие-к-одному** (ответ оставляет конкретный администратор/модератор).

3. **`roles` / Поле `role` в `users`**
   * Добавление поля `role` в таблицу `users` (значения: `user`, `moderator`, `admin`).
   * Необходимо для ограничения доступа к эндпоинтам (например, только администратор/модератор может оставлять ответы в `replies` или управлять категориями).

4. **`FeedbackStatus` (Статусы отзывов)**
   * Поле `status` в таблице `feedback` со значениями: `NEW` (Новый), `IN_PROGRESS` (В обработке), `RESOLVED` (Решено), `CLOSED` (Закрыто).

---

### Python-классы моделей, которые необходимо внедрить:

### Расширенный класс User (`src/models/user.py`)
```python
from typing import List
from sqlalchemy import String, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship
from src.models.base import Base

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    role: Mapped[str] = mapped_column(String, default="user")  # Роли: user, moderator, admin
    
    # Связи
    feedbacks: Mapped[List["Feedback"]] = relationship(back_populates="user")
    replies: Mapped[List["Reply"]] = relationship(back_populates="admin")
```

### Расширенный класс Feedback (`src/models/feedback.py`)
```python
from datetime import datetime
from typing import List
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base

class Feedback(Base):
    __tablename__ = 'feedback'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="NEW")  # Статусы: NEW, IN_PROGRESS, RESOLVED, CLOSED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Связи
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('categories.id'), nullable=True, default=None)
    
    user: Mapped["User"] = relationship(back_populates="feedbacks")
    category: Mapped["Category | None"] = relationship(back_populates="feedbacks")
    replies: Mapped[List["Reply"]] = relationship(
        back_populates="feedback", 
        cascade="all, delete-orphan"
    )
```

### Новый класс Category (`src/models/category.py`)
```python
from typing import List
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base

class Category(Base):
    __tablename__ = 'categories'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    
    # Связи
    feedbacks: Mapped[List["Feedback"]] = relationship(back_populates="category")
```

### Новый класс Reply (`src/models/reply.py`)
```python
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base

class Reply(Base):
    __tablename__ = 'replies'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Связи
    feedback_id: Mapped[int] = mapped_column(Integer, ForeignKey('feedback.id'))
    admin_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    
    feedback: Mapped["Feedback"] = relationship(back_populates="replies")
    admin: Mapped["User"] = relationship(back_populates="replies")
```

---

## 5. Проектирование новых API эндпоинтов

Для поддержки новой архитектуры будут разработаны следующие маршруты:

### 🔑 Авторизация (`/auth`)
*   `POST /auth/register` — Регистрация нового пользователя.
*   `POST /auth/token` — Авторизация и получение JWT-токена (вход).
*   `GET /auth/me` — Получение информации о текущем вошедшем пользователе.

### 📝 Обратная связь (`/feedbacks`)
*   `POST /feedbacks` — Создание нового отзыва (доступно авторизованным пользователям, включает выбор `category_id`).
*   `GET /feedbacks` — Получение списка отзывов (с пагинацией и фильтрацией по `category_id`, `status` и `rating`).
*   `GET /feedbacks/{id}` — Получение деталей конкретного отзыва вместе со всеми ответами (`replies`).
*   `PATCH /feedbacks/{id}/status` — Изменение статуса отзыва (доступно модераторам и администраторам).
*   `DELETE /feedbacks/{id}` — Удаление отзыва (владелец отзыва или администратор).

### 🏷️ Категории (`/categories`)
*   `GET /categories` — Получение списка всех категорий.
*   `POST /categories` — Создание новой категории (только для администраторов).
*   `DELETE /categories/{id}` — Удаление категории (только для администраторов).

### 💬 Ответы на отзывы (`/replies`)
*   `POST /feedbacks/{id}/replies` — Добавить ответ на отзыв (только для модераторов и администраторов).

---

## 6. Пошаговый план реализации новой архитектуры

### Шаг 1: Фикс багов и обновление существующих моделей
1.  Привести в соответствие внешний ключ в `src/models/feedback.py` (`users.id`).
2.  Исправить поведение `datetime.now()` на `datetime.utcnow` (или передать как объект функции).
3.  Сделать `rating` целочисленным (`Integer`) полем.
4.  Внести изменения в `requirements.txt` и зафиксировать основные библиотеки.

### Шаг 2: Генерация корректных миграций Alembic
1.  Запустить Docker-контейнер с PostgreSQL.
2.  Создать новую миграцию, которая корректно сгенерирует таблицы `users` и `feedback`.
```bash
alembic revision --autogenerate -m "create_users_and_feedback_tables"
alembic upgrade head
```

### Шаг 3: Реализация базового функционала отзывов
1.  Описать Pydantic схемы для отзывов в `src/schemas/feedback.py`.
2.  Создать CRUD-функции для работы с таблицей `feedback` в `src/models/crud.py` (добавление отзыва, получение списка, удаление).
3.  Написать логику эндпоинтов в `src/routers/feedback.py` и подключить роутер в `src/main.py`.

### Шаг 4: Внедрение JWT-авторизации
1.  Добавить поле `role` в таблицу `users`.
2.  Создать утилиты для работы с JWT (генерация токенов, валидация, зависимости получения текущего пользователя).
3.  Защитить эндпоинты создания отзывов требованием авторизации.

### Шаг 5: Добавление Категорий и Ответов
1.  Создать SQLAlchemy-модели `Category` и `Reply`.
2.  Сгенерировать миграцию Alembic для новых таблиц.
3.  Реализовать CRUD и API роутеры для категорий и ответов.
4.  Добавить логику разграничения ролей (проверка `user.role == 'admin'` для админских действий).
