from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from app.models import EntityModel


class Tag(EntityModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    id: UUID = Field(default_factory=uuid4)
    description: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
