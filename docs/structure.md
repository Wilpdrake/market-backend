# Структура backend и общей инфраструктуры

Backend организован как **модульный монолит** с разделением на доменный, прикладной,
инфраструктурный и HTTP-слои. Данные между слоями передаются типизированными Pydantic v2
моделями; бизнес-логика при этом не зависит от FastAPI, SQLAlchemy, PostgreSQL и Dishka.

При этом весь продукт является **polyrepo-системой**: backend, frontend и инфраструктура
имеют независимые Git-репозитории. Оркестрация production-окружения, reverse proxy,
PostgreSQL и общий Jenkins pipeline принадлежат репозиторию `market-infrastructure`, а не
backend-приложению.

## Структура всей системы

```text
GitProjects/
├── market-backend/          # FastAPI, бизнес-логика, ORM-модели и Alembic
├── market-frontend/         # Локальное имя checkout frontend-приложения
└── market-infrastructure/   # Compose, Nginx, Jenkins и deployment-документация
```

Репозитории остаются соседними. Это важно для Compose build contexts:
`market-infrastructure/docker-compose.yml` собирает backend из `../market-backend`, а
frontend — из `${FRONTEND_CONTEXT:-../market-frontend}`. Jenkins воспроизводит ту же
структуру workspace, явно создавая каталоги `market-infrastructure`, `market-backend` и
`market-frontend`.

Frontend в Jenkins загружается из репозитория `git@github.com:yushiri/market-order.git`, но
помещается в каталог `market-frontend`, чтобы путь совпадал с Compose-контекстом.

### Ответственность репозиториев

| Репозиторий | Ответственность |
|---|---|
| `market-backend` | HTTP API, бизнес-правила, DI, доступ к данным, ORM и миграции Alembic |
| `market-frontend` | Пользовательский и административный web-интерфейс |
| `market-infrastructure` | Сборка общей системы, Nginx, PostgreSQL, secrets binding, CI/CD, security scans и smoke tests |

Backend владеет кодом миграций и своим Dockerfile. Infrastructure определяет, когда и в
каком окружении образ запускается, как ему передаётся `DATABASE_URL` и каким публичным
маршрутом он доступен.

## Структура backend

```text
market-backend/
├── app/
│   ├── domain/                         # Доменные Pydantic-модели
│   │   ├── users/
│   │   │   └── models.py
│   │   └── products/
│   │       └── models.py
│   │
│   ├── application/                    # Сценарии, команды и абстрактные порты
│   │   ├── users/
│   │   │   ├── models.py              # Pydantic-команды
│   │   │   ├── exceptions.py
│   │   │   ├── ports.py
│   │   │   └── services.py
│   │   └── products/
│   │       ├── models.py              # Pydantic-команды
│   │       ├── ports.py
│   │       └── services.py
│   │
│   ├── infrastructure/                 # Реализации внешних зависимостей
│   │   ├── database/
│   │   │   ├── base.py                 # SQLAlchemy DeclarativeBase
│   │   │   ├── models.py               # ORM-модели
│   │   │   ├── repositories.py         # Репозитории пользователей
│   │   │   └── product_repositories.py # Репозитории товаров
│   │   ├── security/                    # JWT и хеширование паролей
│   │   └── notifications.py             # Отправка уведомлений
│   │
│   ├── presentation/                    # Внешний HTTP-интерфейс
│   │   └── api/
│   │       └── v1/
│   │           ├── router.py            # Корневой роутер /api/v1
│   │           ├── schemas.py           # Pydantic-схемы v1
│   │           ├── auth.py
│   │           ├── health.py
│   │           ├── users.py
│   │           ├── verifications.py
│   │           ├── telegram.py
│   │           └── admin/               # API административной панели
│   │
│   ├── models.py                       # Общие Pydantic base models
│   ├── core/
│   │   └── config.py                    # Настройки и DATABASE_URL
│   ├── ioc.py                           # Dishka providers и контейнер
│   └── main.py                          # Создание FastAPI-приложения
│
├── alembic/                             # Миграции базы данных
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── docs/                                # Документация backend и API
├── tests/                               # Автоматические тесты
├── alembic.ini
├── Dockerfile                           # Сборка образа backend
└── pyproject.toml
```

Production Compose и общий Jenkins pipeline находятся в `market-infrastructure`. Они не
должны дублироваться или расходиться с инфраструктурным репозиторием.

## Соответствие классической слоистой структуре

В проекте используются названия Clean Architecture. Их соответствие более простой
структуре `api/services/repositories/models/db` выглядит так:

| Классическое название | Расположение в проекте |
|---|---|
| `api/` | `app/presentation/api/` |
| `schemas/` | `app/presentation/api/v1/schemas.py` и схемы отдельных роутеров |
| `services/` | `app/application/<module>/services.py` |
| интерфейсы репозиториев | `app/application/<module>/ports.py` |
| реализации репозиториев | `app/infrastructure/database/*repositories.py` |
| доменные модели | `app/domain/<module>/models.py` |
| команды сервисов | `app/application/<module>/models.py` |
| SQLAlchemy-модели | `app/infrastructure/database/models.py` |
| `db/base.py` | `app/infrastructure/database/base.py` |
| DI providers | `app/ioc.py` |

## Направление зависимостей

```text
HTTP router
    ↓
application service
    ↓
application port (Protocol)
    ↑
repository / security / notification implementation
    ↓
PostgreSQL или внешний сервис
```

Основные правила:

1. `domain` использует Pydantic, но не импортирует FastAPI, Dishka или SQLAlchemy.
2. `application` работает с доменными моделями, Pydantic-командами и портами (`Protocol`), а не с ORM.
3. `infrastructure` реализует порты прикладного слоя.
4. `presentation` преобразует HTTP-модели в команды и доменные результаты в Pydantic-ответы.
5. Связывание интерфейсов с реализациями выполняется только в `app/ioc.py`.

Политики `EntityModel`, `CommandModel`, `ApiModel` и `ApiResponseModel`, правила `PATCH`
и ссылки на официальную документацию приведены в [`pydantic-models.md`](pydantic-models.md).

## Версионирование API

Версия размещается в URL. Текущий API доступен под префиксом:

```text
/api/v1
```

Корневой роутер находится в `app/presentation/api/v1/router.py`, а подключается в
`app/main.py`.

При появлении несовместимой версии структура расширяется без копирования всего проекта:

```text
app/presentation/api/
├── v1/
│   ├── router.py
│   ├── schemas.py
│   └── ...
└── v2/
    ├── router.py
    ├── schemas.py
    └── ...
```

В `app/main.py` одновременно подключаются роутеры обеих поддерживаемых версий:

```python
app.include_router(v1_router)
app.include_router(v2_router)
```

Версионируются только HTTP-контракты: роутеры и Pydantic-схемы запросов и ответов.
Домен, репозитории и существующие сервисы остаются общими. Если `v2` меняет только формат
ответа, его роутер вызывает тот же сервис и выполняет другое преобразование результата.
Отдельный метод или сервис нужен только при реальном изменении бизнес-правил.

Перед удалением старой версии её маршруты следует пометить `deprecated=True`, объявить
срок прекращения поддержки и сохранить обе версии на переходный период.

## Alembic

Alembic расположен отдельно от runtime-кода:

```text
app/infrastructure/database/
├── base.py       # Base
└── models.py     # SQLAlchemy-модели

alembic/
├── env.py
└── versions/     # Последовательные миграции
```

`alembic/env.py` использует:

- `Base.metadata` из `app.infrastructure.database.base`;
- ORM-модели из `app.infrastructure.database.models`;
- `DATABASE_URL` из общего объекта настроек `app.core.config`.

За счёт этого приложение и миграции используют один источник конфигурации подключения.

Рабочий цикл изменения схемы:

```text
изменить ORM-модель
    → создать alembic revision --autogenerate
    → проверить миграцию вручную
    → проверить upgrade/downgrade
    → закоммитить модель и миграцию вместе
```

Autogenerate нельзя принимать без проверки: отдельно контролируются индексы, ограничения,
переименования столбцов, PostgreSQL enum и операции с данными.

### Запуск миграций в общей инфраструктуре

В текущем `market-infrastructure/docker-compose.yml` backend запускается командой:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Контейнер начинает принимать запросы только после успешного применения миграций. Перед
этим Compose ожидает healthy-состояние PostgreSQL через `depends_on`.

Текущая схема рассчитана на один сервис `backend`. При горизонтальном масштабировании
миграцию необходимо вынести в отдельный одноразовый deployment step, чтобы несколько
реплик не выполняли `alembic upgrade head` параллельно:

```text
Build & test → Build image → one-shot alembic upgrade head → Deploy replicas
```

Изменения схемы должны быть обратно совместимыми с предыдущей версией приложения на время
rolling deploy.

## Dishka

Конфигурация Dishka сосредоточена в `app/ioc.py`.

```text
AppProvider
├── Scope.APP
│   ├── Settings
│   ├── AsyncEngine
│   ├── PasswordHasher
│   ├── AccessTokenService
│   └── VerificationNotifier
└── Scope.REQUEST
    ├── AsyncSession
    ├── UserRepository / ProductRepository
    └── UserService / AuthService / ProductService
```

`Scope.APP` применяется к объектам, которые безопасно разделять между запросами.
`Scope.REQUEST` создаёт одну сессию БД, репозитории и сервисы на HTTP-запрос и закрывает
сессию после его завершения.

Контейнер создаётся через `create_container()`, после чего `app/main.py` подключает его к
FastAPI вызовом `setup_dishka(container, app)`. Роутеры получают сервисы через
`FromDishka[...]`, поэтому не создают сессии и репозитории вручную.

Для тестов прикладной слой можно проверять без FastAPI и реальной БД, передавая сервису
тестовые реализации портов. Интеграционные тесты HTTP-слоя могут использовать отдельный
Dishka provider с тестовой БД или подменёнными зависимостями.

## Структура `market-infrastructure`

```text
market-infrastructure/
├── docker-compose.yml                  # Общий стек и build contexts
├── nginx.conf                          # Публичный gateway и маршрутизация
├── Jenkinsfile                         # Общий polyrepo CI/CD pipeline
├── .env.example                        # Только имена и безопасные примеры переменных
├── docs/
│   └── environment.md                  # Environment и Jenkins credentials
└── scripts/
    ├── jenkins_ai_security_review.sh
    └── jenkins_send_security_report.sh
```

Infrastructure не содержит копий исходного кода backend или frontend. Во время локальной
сборки используются соседние checkout-каталоги, а Jenkins сам загружает три репозитория в
один workspace.

### Runtime-топология

```text
                           публичный порт 80
                                  │
                                  ▼
                              ┌─────────┐
                              │  Nginx  │
                              └────┬────┘
                  ┌────────────────┴───────────────┐
                  │                                │
          / и frontend routes               /api и /openapi.json
                  │                                │
                  ▼                                ▼
            ┌──────────┐                     ┌──────────┐
            │ frontend │                     │ backend  │
            │  :7000   │                     │  :8000   │
            └──────────┘                     └────┬─────┘
                                                 │ DATABASE_URL
                                                 ▼
                                           ┌──────────┐
                                           │ postgres │
                                           │  :5432   │
                                           └────┬─────┘
                                                 │
                                           postgres_data
```

Compose создаёт четыре сервиса:

| Сервис | Назначение | Публичный доступ |
|---|---|---|
| `nginx` | Единая точка входа и reverse proxy | `80:80` |
| `frontend` | Production frontend | Только через Nginx |
| `backend` | FastAPI и Alembic | Только через Nginx |
| `postgres` | PostgreSQL 18 | Не публикуется наружу |

Backend и PostgreSQL не имеют `ports`, поэтому доступны только другим контейнерам внутри
Compose-сети. Данные PostgreSQL сохраняются в named volume `postgres_data`.

### Маршрутизация Nginx

| Внешний путь | Upstream | Назначение |
|---|---|---|
| `/` | `frontend:7000` | Frontend и его маршруты |
| `/api...` | `backend:8000` | Версионированный FastAPI API |
| `/openapi.json` | `backend:8000/openapi.json` | Точный маршрут OpenAPI JSON |

Проксирование `/api` сохраняет исходный URI, поэтому запрос
`/api/v1/health/live` приходит в backend с тем же путём. Это соответствует URL-версии API,
описанной выше. Отдельный exact-match для `/openapi.json` не позволяет SPA fallback
frontend вернуть HTML вместо OpenAPI JSON.

### Порядок запуска

1. PostgreSQL запускается и проходит `pg_isready` healthcheck.
2. Backend ожидает healthy PostgreSQL.
3. Backend применяет `alembic upgrade head`.
4. Backend запускает Uvicorn на внутреннем порту `8000`.
5. Healthcheck backend проверяет `/api/v1/health/live`.
6. Nginx принимает внешние запросы на порту `80` и направляет их нужному сервису.

В текущем Compose `nginx` зависит от запуска frontend и backend, но не ожидает их
healthcheck. Фактическую готовность всей системы после deployment проверяет Jenkins smoke
stage.

## Конфигурация окружения

Infrastructure передаёт backend следующие группы настроек:

| Группа | Переменные |
|---|---|
| PostgreSQL | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| Backend | `BACKEND_SECRET_KEY`, автоматически собранный `DATABASE_URL` |
| Первый администратор | `FIRST_SUPERUSER_EMAIL`, `FIRST_SUPERUSER_PASSWORD`, `FIRST_SUPERUSER_NAME`, `FIRST_SUPERUSER_SURNAME` |
| Сборка frontend | `FRONTEND_CONTEXT` |

Локально Compose читает значения из `market-infrastructure/.env`, созданного на основе
`.env.example`. Реальные секреты не должны попадать в Git.

В Jenkins секретные значения подключаются как Secret text credentials. Pipeline проверяет
их форму без вывода значений, создаёт временный `.env` с правами `0600`, запускает Compose и
удаляет файл через `trap`. Наличие переменных в `market-infrastructure` не меняет границу
ответственности: их формат должен соответствовать валидации `app/core/config.py` backend.

## Общий Jenkins pipeline

`market-infrastructure/Jenkinsfile` управляет поставкой всех трёх репозиториев:

```text
Checkout
  → Validate Compose
  → Build images
  → Trivy security scan
  → advisory AI security review
  → Security gate
  → Deploy
  → Smoke test
```

### Checkout

Pipeline отключает автоматический checkout (`skipDefaultCheckout(true)`) и явно создаёт
структуру:

```text
$WORKSPACE/
├── market-infrastructure/
├── market-backend/
└── market-frontend/
```

Это гарантирует, что относительные Compose build contexts работают одинаково локально и в
CI. Для каждого репозитория в Telegram-статусе фиксируются ветка, короткий SHA и заголовок
последнего коммита.

### Validate и Build

Compose-модель проверяется командой `docker compose ... config --quiet`, после чего
собираются production targets backend и frontend. Имя Compose-проекта закреплено как
`market`, чтобы смена Jenkins workspace не создавала второй параллельный стек.

### Security

Trivy сканирует общий workspace на уязвимости, секреты и ошибки конфигурации. Critical
уязвимости или найденные секреты блокируют deployment. AI review формирует дополнительный
advisory-отчёт: его сбой переводит сборку в `UNSTABLE`, но детерминированный security gate
остаётся отдельным этапом.

### Deploy и проверка готовности

Deployment выполняет `docker compose up -d --remove-orphans`. После него Jenkins проверяет
не только HTTP-код главной страницы, но и критический путь backend:

- `/` — доступность frontend;
- `/api/v1/health/live` — готовность FastAPI;
- `/api/v1/products` — запрос, использующий базу данных;
- `/openapi.json` — JSON содержит поле `openapi` и маршрут `/api/v1/health/live`.

Такая проверка не принимает HTML от SPA за корректный ответ backend. При неуспехе Jenkins
выводит только безопасный статус контейнеров, не раскрывая environment или секреты.

### Telegram-уведомление

Pipeline создаёт одно компактное Telegram-сообщение и редактирует его по мере прохождения
этапов. В нём отображаются инициатор, версии трёх репозиториев, текущая стадия, результаты
security-проверок и статус всех стадий. Ошибка уведомления не останавливает deployment.

## Текущие инфраструктурные ограничения

Текущий backend запускает Alembic внутри команды старта контейнера. Это допустимо для
одной реплики, но перед масштабированием миграции нужно сделать отдельным one-shot этапом.

## Добавление нового модуля

Для нового бизнес-модуля, например `orders`, рекомендуется добавлять один вертикальный
срез:

```text
app/domain/orders/models.py
app/application/orders/models.py
app/application/orders/ports.py
app/application/orders/services.py
app/infrastructure/database/order_repositories.py
app/presentation/api/v1/orders.py
```

После этого необходимо:

1. добавить ORM-модель и миграцию Alembic, если модулю нужна БД;
2. зарегистрировать реализацию репозитория и сервис в `app/ioc.py`;
3. подключить HTTP-роутер в `app/presentation/api/v1/router.py`;
4. добавить unit-тесты сервиса и контрактные тесты API.

Такой подход расширяет модульный монолит без дублирования слоёв и сохраняет возможность
выделить модуль в отдельный сервис позднее.
