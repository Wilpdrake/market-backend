# Структура backend и общей инфраструктуры

Backend организован как **модульный монолит** с разделением на доменный, прикладной,
инфраструктурный и HTTP-слои. Данные между слоями передаются типизированными Pydantic v2
моделями; бизнес-логика при этом не зависит от FastAPI, SQLAlchemy, PostgreSQL и Dishka.

При этом весь продукт является **polyrepo-системой**: backend, frontend, bot и инфраструктура
имеют независимые Git-репозитории. Оркестрация production-окружения, reverse proxy,
PostgreSQL и общий Jenkins pipeline принадлежат репозиторию `market-infrastructure`, а не
backend-приложению. Локально backend также имеет собственные `compose.yaml` и `Jenkinsfile`
для разработки и CI отдельного сервиса.

## Структура всей системы

```text
GitProjects/
├── market-backend/          # FastAPI, бизнес-логика, ORM-модели и Alembic
├── market-frontend/         # Локальное имя checkout frontend-приложения
├── market-bot/              # Telegram бот
└── market-infrastructure/   # Compose, Nginx, Jenkins и deployment-документация
```

Репозитории остаются соседними. Это важно для Compose build contexts:
`market-infrastructure/docker-compose.yml` собирает backend из `../market-backend`,
frontend — из `${FRONTEND_CONTEXT:-../market-frontend}`, а bot — из `${BOT_CONTEXT:-../market-bot}`.
Jenkins воспроизводит ту же структуру workspace, явно клонируя четыре репозитория
(`market-infrastructure`, `market-backend`, `market-bot`, `market-frontend`) в соседние
каталоги.

Frontend в Jenkins загружается из репозитория `git@github.com:yushiri/market-order.git`, но
помещается в каталог `market-frontend`, чтобы путь совпадал с Compose-контекстом.

### Ответственность репозиториев

| Репозиторий | Ответственность |
|---|---|
| `market-backend` | HTTP API, бизнес-правила, DI, доступ к данным, ORM и миграции Alembic |
| `market-frontend` | Пользовательский и административный web-интерфейс |
| `market-bot` | Telegram-бот (polling) |
| `market-infrastructure` | Сборка общей системы, Nginx, PostgreSQL, secrets binding и CI/CD (Jenkins) |

Backend владеет кодом миграций, своим `Dockerfile`, локальным `compose.yaml` и
собственным `Jenkinsfile` (Ruff/mypy/pytest). Infrastructure определяет, когда и в
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
├── openapi/                             # Документация backend и API
├── tests/                               # Автоматические тесты (пока не создан)
├── alembic.ini
├── compose.yaml                         # Локальный стек backend + PostgreSQL
├── Dockerfile                           # Сборка образа backend
├── Jenkinsfile                          # Собственный CI: Ruff, mypy, pytest, build, deploy
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

### Запуск миграций вручную

В текущем `market-infrastructure/docker-compose.yml` миграции не прогоняются автоматически.
Перед первым деплоем схему применяет оператор одноразовым запуском контейнера backend:

```bash
docker compose run --rm backend alembic upgrade head
```

Контейнер начинает принимать запросы только после успешного применения миграций вручную.
Перед этим Compose ожидает healthy-состояние PostgreSQL через `depends_on`.

Текущая схема рассчитана на один сервис `backend`. При горизонтальном масштабировании
миграцию необходимо вынести в отдельный one-shot deployment step, чтобы несколько
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
          / и frontend routes               /api, /uploads и контракт FastAPI
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

Compose создаёт пять сервисов:

| Сервис | Назначение | Публичный доступ |
|---|---|---|
| `nginx` | Единая точка входа и reverse proxy | `${HTTP_PORT:-80}:80` |
| `frontend` | Production frontend | Только через Nginx (`expose 7000`) |
| `backend` | FastAPI | Только через Nginx (`expose 8000`) |
| `bot` | Telegram-бот (polling) | Только внутри сети |
| `postgres` | PostgreSQL 18 | Не публикуется наружу |

Backend, frontend и bot не имеют опубликованных портов, поэтому доступны только другим
контейнерам внутри Compose-сети. Данные PostgreSQL сохраняются в named volume
`postgres_data`, загруженные файлы товаров — в `product_uploads`.

### Маршрутизация Nginx

| Внешний путь | Upstream | Назначение |
|---|---|---|
| `/` | `frontend:7000` | Frontend и его маршруты |
| `/api/...` | `backend:8000` | Версионированный FastAPI API |
| `/uploads/...` | `backend:8000` | Загруженные файлы товаров |
| `^/(docs\|redoc\|openapi\.json)$` | `backend:8000` | Интерактивный контракт FastAPI |

Проксирование `/api` сохраняет исходный URI, поэтому запрос
`/api/v1/health/live` приходит в backend с тем же путём. Это соответствует URL-версии API,
описанной выше. Регулярный маршрут `^/(docs|redoc|openapi\.json)$` охватывает и точный
`/openapi.json`, и документацию, поэтому SPA fallback frontend не может вернуть HTML вместо
OpenAPI JSON. Публичная проверка всего пути прокси вынесена в отдельный `location = /healthz`,
который проксирует `backend:8000/api/v1/health/live`.

### Порядок запуска

1. PostgreSQL запускается и проходит `pg_isready` healthcheck.
2. Backend ожидает healthy PostgreSQL.
3. Nginx ожидает healthy-состояния backend и frontend (`depends_on` с `condition: service_healthy`)
   перед тем, как начать принимать внешние запросы на порту `${HTTP_PORT:-80}`.
4. Backend запускает Uvicorn на внутреннем порту `8000` (команда `CMD` образа).
5. Healthcheck backend проверяет `/api/v1/health/live`.

Фактическую готовность всей системы после deployment проверяет внешний `/healthz`
(Nginx → `backend:8000/api/v1/health/live`).

## Запуск миграций

Production-образ backend (собирается из `Dockerfile`, используется в
`market-infrastructure`) запускает только Uvicorn:
`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Alembic в команде
старта контейнера **не выполняется** — в текущем `market-infrastructure/docker-compose.yml`
миграции не прогоняются автоматически перед подъёмом сервиса. Применение схемы лежит на
операторе (отдельный `alembic upgrade head` в контейнере backend перед первым деплоем) либо
должно быть добавлено как one-shot шаг.

Локальный `compose.yaml` самого backend-репозитория ведёт себя иначе: его сервис `api`
стартует командой `alembic upgrade head && uvicorn app.main:app ...`, то есть применяет
миграции сам при запуске. Этот файл предназначен только для разработки/локальной отладки и
не используется продакшн-стеком из `market-infrastructure`.

Контейнер начинает принимать запросы сразу после старта Uvicorn; готовность БД к моменту
запуска обеспечивается порядком `depends_on` (backend ждёт healthy PostgreSQL).

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

`market-infrastructure/Jenkinsfile` управляет поставкой всех трёх репозиториев (backend,
frontend, bot) плюс собственной инфраструктуры. Текущий pipeline содержит пять стадий:

```text
Checkout
  → Validate (docker compose config --quiet)
  → Build (docker compose build)
  → Deploy (docker compose up -d --remove-orphans)
  → Status (docker compose ps)
```

Безопасность и проверки кода не входят в текущий Jenkinsfile: сканирование уязвимостей,
AI security review, security gate и smoke-тесты были удалены из пайплайна. Локальную
проверку качества (Ruff, mypy, pytest) выполняет разработчик перед коммитом, а не CI.

### Checkout

Pipeline отключает автоматический checkout (`skipDefaultCheckout(true)`,
`disableConcurrentBuilds()`) и явно создаёт структуру:

```text
$WORKSPACE/
├── market-infrastructure/   # git@github.com:Wilpdrake/market-infrastructure.git
├── market-backend/          # git@github.com:Wilpdrake/market-backend.git
├── market-bot/              # git@github.com:Wilpdrake/market-bot.git
└── market-frontend/         # git@github.com:yushiri/market-order.git
```

Это гарантирует, что относительные Compose build contexts работают одинаково локально и в
CI. Для каждого репозитория Jenkins клонирует ветку `*/main`. Frontend загружается из
репозитория `git@github.com:yushiri/market-order.git`, но помещается в каталог
`market-frontend`, чтобы путь совпадал с Compose-контекстом.

### Validate и Build

Compose-модель проверяется командой `docker compose config --quiet`, после чего
собираются production targets (`target: production`) backend, frontend и bot. Имя
Compose-проекта закреплено как `market` (`COMPOSE_PROJECT_NAME = 'market'`), чтобы смена
Jenkins workspace не создавала второй параллельный стек.

### Deploy и Status

Deployment выполняет `docker compose up -d --remove-orphans`, после чего стадия `Status`
выводит `docker compose ps`. В текущем pipeline отдельной проверки готовности
(HTTP-запросов к `/healthz` или `/api/v1/health/live`) нет — за готовностью наблюдает
оператор.

## Текущие инфраструктурные ограничения

Продакшн-стек в `market-infrastructure` не запускает Alembic автоматически — схема
применяется оператором вручную (`docker compose run --rm backend alembic upgrade head`)
перед первым деплоем. Это приемлемо для одной реплики, но перед масштабированием миграции
нужно вынести в отдельный one-shot этап. Локальный `compose.yaml` backend-репозитория,
напротив, стартует миграции сам (`alembic upgrade head && uvicorn`).

Собственный `Jenkinsfile` backend-репозитория выполняет Ruff, mypy и `pytest -q`, однако
каталог `tests/` пока отсутствует, поэтому шаг `Tests` и проверка `ruff ... tests` падают —
перед сборкой production-образа нужно добавить тесты. Общий `market-infrastructure/Jenkinsfile`
ограничивается Checkout → Validate → Build → Deploy → Status и не содержит проверок
готовности, сканирования уязвимостей или тестов.

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
4. покрыть сервис unit-тестами, а API — контрактными тестами (каталог `tests/` пока не
   создан; новые модули следует сопровождать тестами в нём).

Такой подход расширяет модульный монолит без дублирования слоёв и сохраняет возможность
выделить модуль в отдельный сервис позднее.
