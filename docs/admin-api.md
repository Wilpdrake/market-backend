# API административной панели

## Базовые настройки

- Base URL: `/api/v1/admin`
- Формат: JSON
- Авторизация: `Authorization: Bearer <access_token>`
- Swagger: `/docs`

Административный JWT выдаётся пользователям с административной ролью. `developer` является
самой высокой ролью. Обычный пользователь
получит `401` на `/admin/auth/token` и `403` при обращении к защищённым admin endpoints.

## Создание первого разработчика

При первом запуске передайте переменные окружения:

```dotenv
FIRST_SUPERUSER_EMAIL=developer@example.com
FIRST_SUPERUSER_USERNAME=wilpdrake
FIRST_SUPERUSER_ROLE=developer
FIRST_SUPERUSER_PASSWORD=replace-with-a-strong-password
FIRST_SUPERUSER_NAME=Admin
FIRST_SUPERUSER_SURNAME=Administrator
```

Backend создаст разработчика, если пользователя с таким email ещё нет. Для существующего
административного пользователя bootstrap синхронизирует username, роль и пароль с текущими
переменными окружения. Если email принадлежит обычному пользователю, приложение завершит
запуск с ошибкой и не повысит его права автоматически.

## Авторизация

### `POST /api/v1/admin/auth/token`

```json
{
  "email": "wilpdrake",
  "password": "replace-with-a-strong-password"
}
```

Ответ:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### `GET /api/v1/admin/auth/me`

Возвращает профиль текущего администратора.

## Пользователи

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/v1/admin/users?offset=0&limit=100` | Список пользователей |
| `POST` | `/api/v1/admin/users` | Создать пользователя или администратора |
| `GET` | `/api/v1/admin/users/{uuid}` | Получить пользователя |
| `PATCH` | `/api/v1/admin/users/{uuid}` | Изменить пользователя |
| `DELETE` | `/api/v1/admin/users/{uuid}` | Удалить пользователя |

Администратор не может удалить собственную учётную запись или снять у себя роль admin.

### Запрос создания пользователя

```typescript
export interface AdminUserCreate {
  name: string;
  surname: string;
  patronymic?: string | null;
  email: string;
  password: string;
  password_confirmation: string;
  contact_number?: string | null;
  telegram_username?: string | null;
  comment?: string | null;
  avatar_image?: string | null;
  header_image?: string | null;
  role?: "user" | "admin";
}
```

`password` и `password_confirmation` должны совпадать. Пароль никогда не возвращается в
ответах API.

### Ответ пользователя

```typescript
export interface AdminUser {
  uuid: string;
  name: string;
  surname: string;
  patronymic: string | null;
  email: string;
  contact_number: string | null;
  telegram_username: string | null;
  comment: string | null;
  avatar_image: string | null;
  header_image: string | null;
  role: "user" | "admin";
  created_by: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  created_at: string;
  updated_at: string;
}
```

## Продукция

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/v1/admin/products?offset=0&limit=100` | Список продукции |
| `POST` | `/api/v1/admin/products` | Создать карточку |
| `GET` | `/api/v1/admin/products/{uuid}` | Получить карточку |
| `PATCH` | `/api/v1/admin/products/{uuid}` | Изменить карточку |
| `DELETE` | `/api/v1/admin/products/{uuid}` | Удалить карточку |

### Запрос создания или редактирования

```typescript
export interface ProductInput {
  title: string;
  description?: string | null;
  images?: string[] | null;
  header_image?: string | null;
  price?: string | null;
  ozon_price?: string | null;
  wb_price?: string | null;
}
```

Цены передаются десятичными строками, например `"2500.00"`, чтобы не терять точность.
При создании обязательным является только `title`.

### Ответ карточки продукции

```typescript
export interface ProductCard {
  uuid: string;
  title: string;
  description: string | null;
  images: string[] | null;
  header_image: string | null;
  price: string | null;
  ozon_price: string | null;
  wb_price: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}
```

`created_by` и `updated_by` backend заполняет UUID администратора из JWT. Frontend не должен
передавать эти поля.

## Статусы ошибок

| HTTP | Значение |
|---|---|
| `400` | Некорректная операция |
| `401` | Неверные credentials или отсутствует JWT |
| `403` | JWT принадлежит обычному пользователю |
| `404` | Пользователь или товар не найден |
| `409` | Email уже зарегистрирован |
| `422` | Ошибка валидации полей |

Прикладные ошибки имеют вид:

```json
{
  "detail": "Описание ошибки"
}
```
