# Pydantic-модели

Проект использует **Pydantic v2** во всех слоях, где данные передаются между границами
приложения. SQLAlchemy-модели при этом остаются отдельными: они описывают таблицы и не
являются HTTP- или доменным контрактом.

## Расположение моделей

| Назначение | Расположение | Базовый класс |
|---|---|---|
| Общая политика конфигурации | `app/models.py` | `BaseModel` |
| Доменные модели | `app/domain/<module>/models.py` | `EntityModel` |
| Команды прикладного слоя | `app/application/<module>/models.py` | `CommandModel` |
| HTTP-запросы и webhook payload | `app/presentation/api/.../schemas.py` | `ApiModel` |
| HTTP-ответы | `app/presentation/api/.../schemas.py` | `ApiResponseModel` |
| ORM-модели | `app/infrastructure/database/models.py` | SQLAlchemy `Base` |
| Настройки окружения | `app/core/config.py` | `BaseSettings` |

Модели называются по назначению: `User` и `Product` представляют доменное состояние,
`CreateUser` и `UpdateProduct` — команды use case, а `RegisterRequest` и `UserResponse` —
публичный HTTP-контракт. Запрос FastAPI не передаётся напрямую в репозиторий.

## Политики конфигурации

### `EntityModel`

Доменные модели допускают изменение полей, но включают `validate_assignment=True` и
`extra="forbid"`. Поэтому Pydantic проверяет типы при создании и последующем присваивании,
а неизвестные поля считаются ошибкой. Для copy-on-write обновлений сервисы используют
`model_copy(update=...)` через типизированную функцию `replace_model`.

### `CommandModel`

Команды прикладного слоя имеют `frozen=True` и `extra="forbid"`. Сервис получает
неизменяемый снимок входных данных: обработчик не может случайно изменить команду после
валидации, а опечатка в имени поля не игнорируется.

### `ApiModel` и `ApiResponseModel`

HTTP-модели запрещают неизвестные JSON-поля. `ApiResponseModel` дополнительно включает
`from_attributes=True`, поэтому FastAPI может сериализовать доменные объекты без связи с
ORM. Публичные request/response-схемы остаются отдельными: пароль существует только во
входной модели и не попадает в модель ответа.

Для `PATCH` значение `None` не заменяет признак присутствия поля. Роутер проверяет
`model_fields_set`: отсутствующее поле означает «не изменять», явно переданный `null` —
«очистить», если контракт разрешает очистку.

## Правила добавления модели

1. Выберите границу данных: domain, application command или HTTP contract.
2. Наследуйте соответствующий базовый класс из `app/models.py`.
3. Используйте конкретные типы (`list[str]`, `dict[str, ...]`), `UUID`, `datetime` и
   `Decimal`; ограничения публичного ввода задавайте через `Field`.
4. Не возвращайте request-модель как response-модель, если она содержит секретные или
   служебные поля.
5. Не используйте Pydantic-модель вместо SQLAlchemy declarative model и наоборот.
6. Зафиксируйте в тестах валидацию, сериализацию и OpenAPI-контракт.

## Пример потока данных

```text
JSON
  → RegisterRequest (ApiModel)
  → CreateUser (CommandModel)
  → UserService
  → User (EntityModel)
  → SqlAlchemyUserRepository / UserModel
  → UserResponse (ApiResponseModel)
  → JSON
```

## Проверка

```bash
uv run pytest -q tests/test_pydantic_models.py
uv run pytest -q tests/test_api_contract.py
uv run mypy app
uv run ruff check app tests alembic
```

OpenAPI доступен по `/openapi.json`, Swagger UI — по `/docs`.

## Официальная документация

- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic ConfigDict](https://docs.pydantic.dev/latest/api/config/)
- [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/)
- [FastAPI Request Body](https://fastapi.tiangolo.com/tutorial/body/)
- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
