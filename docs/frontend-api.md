# API-контракт для фронтенда

Отдельный контракт административной панели: [`admin-api.md`](admin-api.md).

Документ описывает текущий HTTP API backend версии `v1`.

- Base URL: `/api/v1`
- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`
- Формат запросов и ответов: `application/json`
- Даты: строки ISO 8601 в UTC, например `2026-07-21T09:30:00Z`
- Идентификатор пользователя: UUID-строка

## Авторизация

Для защищённых методов передавайте JWT access token:

```http
Authorization: Bearer <access_token>
```

Если токен отсутствует, просрочен или некорректен, API возвращает `401`.

## Общие типы TypeScript

```ts
export interface User {
  id: string;
  email: string;
  phone: string | null;
  telegram_id: number | null;
  telegram_username: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer" | string;
}

export interface ApiError {
  detail: string | Array<{
    loc: Array<string | number>;
    msg: string;
    type: string;
  }>;
}
```

### Значение полей `User`

| Поле | Тип | Описание |
|---|---|---|
| `id` | `string` | UUID пользователя |
| `email` | `string` | Email пользователя |
| `phone` | `string \| null` | Номер телефона; отдельный строгий формат пока не задан, максимум 32 символа |
| `telegram_id` | `number \| null` | Числовой ID Telegram после привязки |
| `telegram_username` | `string \| null` | Username Telegram без гарантии наличия `@` |
| `is_active` | `boolean` | Разрешён ли вход пользователя |
| `is_superuser` | `boolean` | Администраторские права |
| `is_email_verified` | `boolean` | Подтверждён ли email |
| `is_phone_verified` | `boolean` | Подтверждён ли телефон |
| `created_at` | `string` | Дата создания в ISO 8601 |
| `updated_at` | `string` | Дата последнего обновления в ISO 8601 |

Хеш пароля и хеши verification-токенов никогда не возвращаются клиенту.

## Auth

### Регистрация

`POST /api/v1/auth/register`

Авторизация не нужна.

```ts
export interface RegisterRequest {
  email: string;
  password: string; // от 8 до 128 символов
  phone?: string | null; // максимум 32 символа
}
```

Пример:

```json
{
  "email": "user@example.com",
  "password": "strong-password",
  "phone": "+79990000000"
}
```

Успешный ответ: `201 Created`, объект `User`.

Возможные ошибки:

- `409` — пользователь с таким email уже существует;
- `422` — некорректный email, короткий пароль или невалидный JSON.

### Вход

`POST /api/v1/auth/token`

Авторизация не нужна.

```ts
export interface LoginRequest {
  email: string;
  password: string;
}
```

Успешный ответ: `200 OK`.

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Ошибка `401` означает неверный email, пароль либо неактивного пользователя.

Backend пока выдаёт только access token. Refresh token отсутствует.

## Users

Все методы раздела требуют заголовок `Authorization`.

### Текущий пользователь

`GET /api/v1/users/me`

Ответ: `200 OK`, объект `User`.

Этот endpoint удобно вызывать после входа, чтобы получить профиль и права пользователя.

### Список пользователей

`GET /api/v1/users?offset=0&limit=100`

Доступен только пользователю с `is_superuser=true`.

Query-параметры:

| Поле | Тип | По умолчанию | Описание |
|---|---:|---:|---|
| `offset` | `number` | `0` | Смещение |
| `limit` | `number` | `100` | Размер страницы; backend ограничивает результат до 100 записей |

Ответ: `200 OK`, массив `User[]`.

Ошибка `403` — текущий пользователь не администратор.

### Получить пользователя

`GET /api/v1/users/{user_id}`

Пользователь может получить собственный профиль. Администратор может получить любой.

Ответ: `200 OK`, объект `User`.

Ошибки: `403` — недостаточно прав, `404` — пользователь не найден, `422` — некорректный UUID.

### Обновить пользователя

`PATCH /api/v1/users/{user_id}`

Передавайте только изменяемые поля:

```ts
export interface UpdateUserRequest {
  email?: string | null;
  phone?: string | null;
  is_active?: boolean | null;
}
```

Пример:

```json
{
  "phone": "+79990000000"
}
```

Ответ: `200 OK`, обновлённый объект `User`.

Пользователь может менять свой профиль; администратор — любой профиль.

> В текущем API поле `is_active` доступно в общей PATCH-схеме. На фронтенде обычного пользователя не следует показывать его как редактируемое поле.

### Удалить пользователя

`DELETE /api/v1/users/{user_id}`

Ответ: `204 No Content`, тело ответа отсутствует.

Пользователь может удалить себя; администратор — любого пользователя.

## Подтверждение email

### Запросить токен

`POST /api/v1/verifications/email/request`

Требует авторизацию. Тело не требуется.

Ответ: `202 Accepted`.

```json
{
  "status": "accepted"
}
```

### Подтвердить email

`POST /api/v1/verifications/email/confirm`

Авторизация не нужна: секретом является одноразовый токен.

```ts
export interface VerificationTokenRequest {
  token: string;
}
```

```json
{
  "token": "<token-from-email>"
}
```

Ответ: `200 OK`, объект `User` с `is_email_verified=true`.

## Подтверждение телефона

### Запросить код

`POST /api/v1/verifications/phone/request`

Требует авторизацию. Тело не требуется.

Ответ: `202 Accepted`.

```json
{
  "status": "accepted"
}
```

### Подтвердить телефон

`POST /api/v1/verifications/phone/confirm`

Требует авторизацию.

```json
{
  "token": "123456"
}
```

Ответ: `200 OK`, объект `User` с `is_phone_verified=true`.

## Привязка Telegram

### Получить ссылку на бота

`POST /api/v1/verifications/telegram/request`

Требует авторизацию. Тело не требуется.

Ответ: `200 OK`.

```ts
export interface TelegramLinkResponse {
  deep_link: string;
}
```

```json
{
  "deep_link": "https://t.me/market_bot?start=<one-time-token>"
}
```

Фронтенд должен открыть `deep_link` во внешнем приложении или новой вкладке. После команды `/start` Telegram webhook привяжет аккаунт. Затем фронтенд может повторно вызвать `GET /api/v1/users/me` и проверить поля `telegram_id` и `telegram_username`.

### Telegram webhook

`POST /api/v1/telegram/webhook`

Это служебный endpoint для Telegram, а не для браузерного клиента. Telegram передаёт секрет в заголовке:

```http
X-Telegram-Bot-Api-Secret-Token: <webhook-secret>
```

Успешный ответ: `204 No Content`.

## Health check

`GET /api/v1/health/live`

Авторизация не нужна.

```json
{
  "status": "ok",
  "service": "market-backend",
  "version": "0.1.0"
}
```

## Статусы ошибок

| Статус | Значение |
|---:|---|
| `400` | Ошибка бизнес-валидации или неверный verification token |
| `401` | Нет корректной авторизации или неверные данные входа |
| `403` | Недостаточно прав |
| `404` | Ресурс не найден |
| `409` | Конфликт, например повторный email |
| `422` | FastAPI/Pydantic не приняли параметры или JSON |

Обычная бизнес-ошибка:

```json
{
  "detail": "User not found"
}
```

Ошибка валидации `422` содержит массив объектов в `detail`; frontend должен уметь обработать оба варианта.

## Рекомендуемый frontend flow

1. Зарегистрировать пользователя через `POST /auth/register`.
2. Выполнить вход через `POST /auth/token`.
3. Сохранить `access_token` и передавать его как Bearer token.
4. Получить профиль через `GET /users/me`.
5. По флагам `is_email_verified` и `is_phone_verified` показать нужные шаги подтверждения.
6. Для Telegram получить `deep_link`, открыть бота и периодически либо после возврата обновить `/users/me`.
7. При `401` очистить локальную сессию и отправить пользователя на экран входа.

Полные машинно-читаемые схемы всегда доступны через `/openapi.json`; Swagger UI — через `/docs`.
