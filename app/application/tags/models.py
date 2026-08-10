from app.models import CommandModel


class CreateTag(CommandModel):
    name: str
    slug: str
    description: str | None = None


class UpdateTag(CommandModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    clear_fields: frozenset[str] = frozenset()
