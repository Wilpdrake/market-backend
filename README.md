
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
- локальный `compose.yaml` (backend + PostgreSQL) и собственный `Jenkinsfile` (Ruff, mypy,
  pytest, build и deploy). Качество кода проверяет CI до сборки production-образа.

Единый контракт публичного, административного и планируемого HTTP API находится в
[`openapi/openapi.yaml`](openapi/openapi.yaml).

Расположение и правила Pydantic-моделей описаны в
[`openapi/pydantic-models.md`](openapi/pydantic-models.md), полная архитектура — в
[`openapi/structure.md`](openapi/structure.md).

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

Локальный стек (backend + PostgreSQL) описан в собственном `compose.yaml` репозитория.
Он стартует миграции и Uvicorn командой `alembic upgrade head && uvicorn app.main:app`.
Переменные окружения (например `SECRET_KEY`, `POSTGRES_PASSWORD`) передаются из shell —
отдельного `.env.example` в backend-репозитории нет:

```bash
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')"
export POSTGRES_PASSWORD="change_me_strong_password"
docker compose up --build
```

Проверка (compose публикует порт `${APP_PORT:-80}` → backend `8000`):

```bash
curl http://localhost/api/v1/health/live
```

Без Docker (требуется локальный PostgreSQL):

```bash
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

При таком запуске API доступен напрямую на `http://localhost:8000/api/v1/health/live`.

Полный продакшн-стек (Nginx + frontend + backend + bot + PostgreSQL) собирается из
репозитория `market-infrastructure`, где лежат общий `docker-compose.yml` и `.env.example`.

## Проверки

```bash
uv run ruff check app tests alembic
uv run ruff format --check app tests alembic
uv run mypy app
uv run pytest -q
uv run alembic upgrade head --sql
```

Внимание: каталог `tests/` в репозитории **пока отсутствует**. Из-за этого локальный
`uv run pytest -q` и шаг `Tests` в `Jenkinsfile` (`uv run pytest -q`, а также
`ruff check ... tests`) сейчас завершаются ошибкой. Новые изменения следует сопровождать
тестами в `tests/`, иначе CI не пройдёт.

## Подтверждения

`LoggingVerificationNotifier` предназначен для development: он выводит email/SMS токены
в журнал приложения. Для production нужно реализовать порты `VerificationNotifier` через
выбранные SMTP и SMS-провайдеры. Telegram webhook принимает секрет в заголовке
`X-Telegram-Bot-Api-Secret-Token`; задайте `TELEGRAM_WEBHOOK_SECRET` в Jenkins credentials
или production `.env`.

## Jenkins

Собственный `Jenkinsfile` репозитория запускает четыре стадии: сборка development-образа,
`Quality` (параллельно Ruff, mypy и `pytest -q` через `docker run`), сборка production-образа
(`docker compose build api`) и, для ветки `main`, `docker compose up -d --remove-orphans`.
Тестовый образ удаляется в `post`-шаге.

Из-за отсутствия каталога `tests/` шаг `Tests` (`uv run pytest -q`) и проверка
`ruff check ... tests` сейчас падают — их нужно починить добавлением тестов.

Production-секреты (`SECRET_KEY`, `POSTGRES_PASSWORD`, `TELEGRAM_BOT_TOKEN` и др.) задаются
в shell/credentials перед `docker compose up`; в репозиторий они не добавляются. Полный
многосервисный деплой (Nginx, frontend, bot) выполняется отдельным пайплайном в
`market-infrastructure`.
