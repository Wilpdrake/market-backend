
# Market Backend

Версионированный REST API на FastAPI для пользователей и аутентификации. Проект сделан
как модульный монолит: Pydantic-модели домена не зависят от FastAPI, PostgreSQL или Dishka,
поэтому модули можно выделять в микросервисы только после появления реальной необходимости.

## Возможности

- API под единым префиксом `/api/v1` и OpenAPI по `/docs`;
- CORS-запросы разрешены только с `https://woodandclay.ru`;
- CRUD пользователей с проверкой доступа к собственному профилю и admin-only списком;
- регистрация, Argon2-хеширование паролей, JWT-аутентификация;
- подтверждение email и телефона одноразовыми токенами (в БД хранится только SHA-256);
- привязка Telegram через deep link и защищённый webhook;
- PostgreSQL, SQLAlchemy 2 async, Alembic, Dishka;
- Docker Compose и Jenkins pipeline с Ruff, mypy, pytest, build и deploy.

Контракт для frontend-разработчика с TypeScript-интерфейсами, полями и примерами
запросов находится в [`docs/frontend-api.md`](docs/frontend-api.md).

Контракт авторизации и CRUD административной панели находится в
[`docs/admin-api.md`](docs/admin-api.md).

Расположение и правила Pydantic-моделей описаны в
[`docs/pydantic-models.md`](docs/pydantic-models.md), полная архитектура — в
[`docs/structure.md`](docs/structure.md).

## Структура

```text
app/models.py              общие политики Pydantic-моделей
app/domain                 доменные Pydantic-модели
app/application            команды, сценарии и порты
app/infrastructure         PostgreSQL, JWT, Argon2, уведомления
app/presentation/api/v1    HTTP API версии v1
app/ioc.py                 Dishka container
alembic                    миграции
```

## Локальный запуск

```bash
cp .env.example .env
# Обязательно замените SECRET_KEY и POSTGRES_PASSWORD.
docker compose up --build
```

Проверка: `curl http://localhost/api/v1/health/live`.

Без Docker:

```bash
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Проверки

```bash
uv run ruff check app tests alembic
uv run ruff format --check app tests alembic
uv run mypy app
uv run pytest -q
uv run alembic upgrade head --sql
```

## Подтверждения

`LoggingVerificationNotifier` предназначен для development: он выводит email/SMS токены
в журнал приложения. Для production нужно реализовать порты `VerificationNotifier` через
выбранные SMTP и SMS-провайдеры. Telegram webhook принимает секрет в заголовке
`X-Telegram-Bot-Api-Secret-Token`; задайте `TELEGRAM_WEBHOOK_SECRET` в Jenkins credentials
или production `.env`.

## Jenkins

Pipeline запускает проверки в одноразовом development image, собирает production image и
для ветки `main` выполняет `docker compose up -d`. Jenkins agent должен иметь доступ к Docker,
а production secrets должны быть созданы на узле Jenkins в `.env` — в репозиторий они не
добавляются.
