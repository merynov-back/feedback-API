# Исправление упавших тестов

**Итог:** было 13 упавших и 37 прошедших тестов, стало 50 прошедших и 0 упавших. Предупреждение `DeprecationWarning` про `datetime.utcnow()` тоже исчезло.

---

## 1. Ошибки 409/410 при подтверждении email не возвращались (баг в коде)

**Файл:** `src/routers/auth.py`

Роутер определял тип ошибки по подстроке в тексте исключения. В роутере подстроки написаны через «ё», а в сервисе (`auth_service.py`) — через «е». Поэтому совпадения не было, и любая ошибка превращалась в `400`. Та же проблема была в `/auth/resend-verification`.

**Было:**
```python
if "истёк" in error_msg:            # verify-email → 410
    ...
if "уже подтверждён" in error_msg:  # verify-email и resend-verification → 409
    ...
```

**Стало:**
```python
if "истек" in error_msg:
    ...
if "уже подтвержден" in error_msg:
    ...
```

**Чинит тесты:** `test_verify_expired_code_returns_410`, `test_verify_already_active_returns_409`.

> Сравнивать тексты сообщений всё равно ненадёжно: любая правка сообщения снова сломает эти проверки. Лучше завести отдельные классы исключений (`CodeExpiredError`, `AlreadyVerifiedError`).

---

## 2. Схема принимала некорректный OTP-код

**Файл:** `src/schemas/auth.py`

Сервис генерирует код ровно из 6 цифр, а схема принимала любую строку длиной от 4 до 8 символов, в том числе с буквами и пробелами.

**Было:**
```python
code: str = Field(..., min_length=4, max_length=8, examples=["123456"])
```

**Стало:**
```python
code: str = Field(..., pattern=r"^\d{6}$", examples=["123456"])
```

**Чинит тесты:** `TestVerifyEmailRequest::test_code_too_short`, `test_code_too_long`, `test_code_with_letters`, `test_code_with_spaces`.

---

## 3. Устаревший `datetime.utcnow()`

**Файл:** `src/services/auth_service.py`

**Было:**
```python
expire = datetime.utcnow() + expire_delta
```

**Стало:**
```python
expire = datetime.now(tz=timezone.utc) + expire_delta
```

Предупреждение `DeprecationWarning` больше не появляется. Кроме того, `exp` и `iat` в токене теперь считаются одинаково — во времени с явно заданной таймзоной.

---

## 4. Тесты логина отправляли запрос в неверном формате

**Файл:** `tests/test_api.py`

Эндпоинт `/auth/token` принимает `OAuth2PasswordRequestForm`, то есть данные формы с полями `username` и `password`. Тесты отправляли JSON с полем `email`, и сервер отвечал `422`. Кроме того, учётные данные в тестах не совпадали с фикстурами: `active_user` — это `active@example.com` / `TestPass123!`.

**Было:**
```python
response = client.post("/auth/token", json={
    "email" : "email@gmail.com",
    "password": "password123",
})
```

**Стало:**
```python
response = client.post("/auth/token", data={
    "username": "active@example.com",
    "password": "TestPass123!",
})
```

Отдельные исправления в тестах:

| Тест | Было | Стало |
|---|---|---|
| `test_login_wrong_password_returns_401` | отправлялся пароль, считавшийся верным | `WrongPass123!` — действительно неверный пароль |
| `test_login_inactive_user_returns_401` | `email@gmail.com` — такого пользователя нет, тест фактически проверял несуществующего | `test@example.com` — неактивный пользователь из фикстуры `registered_user` |
| `test_login_non_existent_user_returns_401` | JSON | данные формы, `non_existent@gmail.com` |
| `test_refresh_with_valid_token_returns_200` | логин через JSON, ответ без `refresh_token` → `KeyError` | логин через данные формы с учёткой `active_user` |

**Чинит тесты:** все 5 тестов из `TestLoginEndpoint` и `test_refresh_with_valid_token_returns_200`.

---

## 5. Тест повторной регистрации использовал свободный email

**Файл:** `tests/test_api.py`

Фикстура `registered_user` создаёт пользователя `test@example.com`, а тест регистрировал `email@gmail.com`. Этот email не был занят, поэтому сервер возвращал `201` вместо `409`.

**Было:**
```python
"email" : "email@gmail.com",
```

**Стало:**
```python
"email" : "test@example.com",
```

**Чинит тест:** `test_register_dublicate_email_returns_409`.
