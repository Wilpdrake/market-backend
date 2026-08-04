А вооб# Draft API: Google Auth и T‑Bank

> Статус: **контракт для разработки frontend**. Эти endpoints ещё не реализованы на backend.
> До реализации названия полей можно согласовать, но frontend уже может строить типы,
> экраны и mock-ответы по этому документу.

## Общие правила

- Base URL: `/api/v1`.
- Формат: `application/json`, кроме webhook T‑Bank.
- Авторизация приложения: заголовок `Authorization: Bearer MARKET_JWT`.
- UUID передаются строками.
- Деньги передаются **строками с двумя знаками после точки**, например `"1490.00"`.
- Даты передаются в ISO 8601 UTC, например `2026-08-03T12:30:00Z`.
- Ошибка приложения: `{ "detail": "Описание ошибки" }`.
- Ошибка валидации `422`: стандартный массив FastAPI в поле `detail`.

## TypeScript-типы

```ts
export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface ApiError {
  detail: string | Array<{
    loc: Array<string | number>;
    msg: string;
    type: string;
  }>;
}

export type Money = string;
```

---

# Google Auth

## Принятый frontend flow

Используем Google Identity Services на frontend. Google возвращает ID token в поле
`credential`; frontend отправляет его backend. Backend проверяет подпись, `aud`, `iss`,
срок действия и подтверждённый email, после чего выдаёт обычный JWT Market Backend.

Google access token и Google refresh token frontend в Market Backend не отправляет.

## Вход или регистрация через Google

`POST /api/v1/auth/google`

Авторизация Market Backend не нужна.

### Request

```ts
export interface GoogleAuthRequest {
  credential: string; // Google ID token (JWT) из Google Identity Services
}
```

```json
{
  "credential": "<google-id-token>"
}
```

### Response

`200 OK`

```json
{
  "access_token": "<market-jwt>",
  "token_type": "bearer"
}
```

После ответа frontend сохраняет `access_token` так же, как после
`POST /api/v1/auth/token`, и получает пользователя через:

`GET /api/v1/users/me`

### Поведение backend

- Если Google-аккаунт уже привязан — вход в существующий аккаунт.
- Если привязки нет, но пользователь с подтверждённым Google email уже существует —
  Google identity безопасно привязывается к нему.
- Если пользователя нет — создаётся новый активный пользователь без локального пароля.
- Email нового пользователя считается подтверждённым только при `email_verified=true`
  в проверенном Google ID token.
- Неактивный локальный пользователь не может войти через Google.

### Ошибки

| HTTP | Причина |
|---:|---|
| `401` | ID token отсутствует, испорчен, просрочен, выпущен для другого Google Client ID или email не подтверждён |
| `409` | Google identity или email уже связан с другим локальным аккаунтом |
| `422` | Невалидный JSON или отсутствует `credential` |

### Что нужно frontend

- Google OAuth Client ID хранится в публичной frontend-конфигурации — это не секрет.
- После получения `credential` вызвать `/auth/google` только один раз.
- Google ID token не хранить как пользовательскую сессию; сессия приложения — JWT из ответа backend.
- При `401` показать повторный вход через Google.

---

# Заказы и T‑Bank

## Принятые допущения

Контракт рассчитан на интернет-эквайринг T‑Bank и несколько настроенных на backend
терминалов. `TerminalKey`, пароль терминала и токены подписи никогда не передаются в браузер.
Frontend работает только с публичным `payment_option_id`; конкретный терминал выбирает backend.

Сумму заказа вычисляет backend по актуальным ценам товаров. Frontend не передаёт итоговую
сумму и не может её подменить.

## Типы

```ts
export interface CreateOrderItemRequest {
  product_id: string;
  quantity: number; // целое число, минимум 1
}

export interface CreateOrderRequest {
  items: CreateOrderItemRequest[];
  customer: {
    name: string;
    email: string;
    phone: string;
  };
  comment?: string | null;
}

export type OrderStatus =
  | "new"
  | "awaiting_payment"
  | "paid"
  | "payment_failed"
  | "cancelled"
  | "refunded";

export interface OrderItem {
  product_id: string;
  title: string;       // snapshot названия на момент заказа
  quantity: number;
  unit_price: Money;   // snapshot цены
  total: Money;
}

export interface Order {
  id: string;
  status: OrderStatus;
  items: OrderItem[];
  total: Money;
  currency: "RUB";
  customer: {
    name: string;
    email: string;
    phone: string;
  };
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export type PaymentKind = "card" | "sbp";

export interface TBankPaymentOption {
  id: string;          // стабильный публичный ID, не TerminalKey
  title: string;       // например «Банковская карта»
  kind: PaymentKind;
  enabled: boolean;
}

export type PaymentStatus =
  | "pending"
  | "authorized"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "refunded";

export interface PaymentConfirmation {
  type: "redirect" | "qr";
  url: string;
}

export interface Payment {
  id: string;                    // UUID платежа Market Backend
  order_id: string;
  provider: "tbank";
  payment_option_id: string;
  status: PaymentStatus;
  amount: Money;
  currency: "RUB";
  confirmation: PaymentConfirmation | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
}
```

## 1. Получить доступные способы оплаты

`GET /api/v1/payments/tbank/options`

Авторизация не нужна. Endpoint возвращает только публичные варианты, доступные витрине.

### Response

`200 OK`

```json
[
  {
    "id": "tbank-card",
    "title": "Банковская карта",
    "kind": "card",
    "enabled": true
  },
  {
    "id": "tbank-sbp",
    "title": "СБП",
    "kind": "sbp",
    "enabled": true
  }
]
```

Frontend не должен хардкодить наличие СБП или карты: показывать только элементы с
`enabled=true`.

## 2. Создать заказ

`POST /api/v1/orders`

Требует авторизацию Market Backend.

### Request

```json
{
  "items": [
    {
      "product_id": "3d9640d0-0de8-48d7-91b1-f4acd452cbe8",
      "quantity": 2
    }
  ],
  "customer": {
    "name": "Иван Иванов",
    "email": "ivan@example.com",
    "phone": "+79990000000"
  },
  "comment": "Позвонить перед отправкой"
}
```

### Response

`201 Created`, объект `Order`.

```json
{
  "id": "8c3ba424-bf2a-4bc5-9cca-e1879329cc1a",
  "status": "new",
  "items": [
    {
      "product_id": "3d9640d0-0de8-48d7-91b1-f4acd452cbe8",
      "title": "Керамическая кружка",
      "quantity": 2,
      "unit_price": "1490.00",
      "total": "2980.00"
    }
  ],
  "total": "2980.00",
  "currency": "RUB",
  "customer": {
    "name": "Иван Иванов",
    "email": "ivan@example.com",
    "phone": "+79990000000"
  },
  "comment": "Позвонить перед отправкой",
  "created_at": "2026-08-03T12:30:00Z",
  "updated_at": "2026-08-03T12:30:00Z"
}
```

Возможные ошибки:

- `400` — пустой заказ или товар нельзя купить;
- `401` — пользователь не авторизован;
- `404` — товар не найден;
- `409` — цена/доступность изменилась и заказ нужно пересобрать;
- `422` — ошибка формата полей.

## 3. Инициализировать платёж T‑Bank

`POST /api/v1/orders/{order_id}/payments/tbank`

Требует авторизацию. Пользователь может оплачивать только собственный заказ.

Для защиты от двойного клика frontend создаёт UUID `idempotency_key` один раз на попытку
оплаты и повторно использует его при сетевом retry.

### Request

```ts
export interface CreateTBankPaymentRequest {
  payment_option_id: string;
  idempotency_key: string; // UUID
}
```

```json
{
  "payment_option_id": "tbank-card",
  "idempotency_key": "a451325c-65e5-44da-bf1b-0ab7bb15eb2b"
}
```

### Response

`201 Created` для первой попытки или `200 OK` для повтора с тем же
`idempotency_key`. Тело в обоих случаях — объект `Payment`.

```json
{
  "id": "50353e60-9483-4679-8d46-e42481af3cf0",
  "order_id": "8c3ba424-bf2a-4bc5-9cca-e1879329cc1a",
  "provider": "tbank",
  "payment_option_id": "tbank-card",
  "status": "pending",
  "amount": "2980.00",
  "currency": "RUB",
  "confirmation": {
    "type": "redirect",
    "url": "https://securepayments.tbank.ru/..."
  },
  "failure_message": null,
  "created_at": "2026-08-03T12:31:00Z",
  "updated_at": "2026-08-03T12:31:00Z"
}
```

Для СБП `confirmation.type` может быть `"qr"`; frontend открывает или отображает URL из
`confirmation.url`. Формат URL не следует разбирать вручную.

Возможные ошибки:

- `400` — заказ нельзя оплатить в текущем статусе;
- `401` — нет авторизации;
- `403` — заказ принадлежит другому пользователю;
- `404` — заказ или `payment_option_id` не найден;
- `409` — заказ уже оплачен или для него уже есть активный платёж;
- `502` — T‑Bank временно не принял запрос; разрешён retry с тем же `idempotency_key`.

## 4. Получить заказ

`GET /api/v1/orders/{order_id}`

Требует авторизацию. Ответ `200 OK`: объект `Order`.

Frontend использует endpoint после возврата со страницы банка. Источник истины — статус
backend, а не query-параметры страницы возврата.

Ошибки: `401`, `403`, `404`.

## 5. Получить текущий платёж заказа

`GET /api/v1/orders/{order_id}/payment`

Требует авторизацию. Ответ `200 OK`: объект `Payment`.

Если webhook ещё не пришёл, backend может дополнительно сверить статус с T‑Bank. Frontend
может опрашивать endpoint раз в 2 секунды не дольше 60 секунд, затем предложить обновить
страницу позже.

Ошибки: `401`, `403`, `404`, `502`.

## 6. Отменить неоплаченный платёж

`POST /api/v1/orders/{order_id}/payment/cancel`

Требует авторизацию. Тело не требуется.

Ответ `200 OK`: обновлённый объект `Payment` со статусом `"cancelled"`.

Оплаченный заказ этим endpoint не возвращается. Возврат денег является отдельной
административной операцией и не входит в первый frontend-контракт.

Ошибки: `400`, `401`, `403`, `404`, `409`, `502`.

## 7. Webhook T‑Bank

`POST /api/v1/payments/tbank/webhook`

Это служебный endpoint T‑Bank, **не endpoint браузерного клиента**. Backend проверяет подпись
уведомления, находит терминал по публичным данным уведомления, идемпотентно обновляет платёж
и заказ. В ответ T‑Bank получает `200 OK` с телом `OK` (`text/plain`).

Frontend не вызывает webhook и не моделирует его provider-specific JSON.

---

# Рекомендуемые frontend-сценарии

## Google

1. Получить `credential` через Google Identity Services.
2. Отправить его в `POST /auth/google`.
3. Сохранить Market JWT из `TokenResponse`.
4. Вызвать `GET /users/me`.
5. Дальше использовать обычную авторизованную сессию приложения.

## T‑Bank

1. Загрузить `GET /payments/tbank/options`.
2. Создать заказ через `POST /orders`.
3. Создать один `idempotency_key` и вызвать `POST /orders/{id}/payments/tbank`.
4. Открыть `payment.confirmation.url`.
5. После возврата банка не доверять URL-параметрам, а запросить `/orders/{id}` и
   `/orders/{id}/payment`.
6. Пока платёж `pending`/`authorized`, недолго опрашивать статус.
7. Показывать успех только при `payment.status === "succeeded"` и `order.status === "paid"`.

## Mock-режим до готовности backend

Frontend может временно перехватывать перечисленные URL через MSW или аналогичный mock layer.
Не добавляйте в production-код fallback, который считает платёж успешным только по возврату
на success page.

---

# Вопросы перед реализацией backend

Эти решения не блокируют frontend-моки, но должны быть согласованы до миграций и реальных
запросов в T‑Bank:

- обязательна ли авторизация для покупки или нужен guest checkout;
- доставка, адрес, промокоды, остатки и состав итоговой модели заказа;
- двухстадийная или одностадийная оплата T‑Bank;
- какие терминалы соответствуют карте и СБП;
- нужны ли чеки/54‑ФЗ и какие данные позиции отправлять в `Receipt`;
- разрешены ли частичные возвраты и кто выполняет их в административной панели;
- точные success/fail страницы frontend;
- один или несколько Google OAuth Client ID (production/staging/local).
