from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from app.models import EntityModel


class AuditLogEntry(EntityModel):
    admin_id: UUID | None
    admin_name: str = Field(min_length=1, max_length=201)
    admin_email: str = Field(min_length=3, max_length=320)
    action: str = Field(min_length=1, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    id: UUID = Field(default_factory=uuid4)
    entity_id: str | None = Field(default=None, max_length=100)
    details: str | None = Field(default=None, max_length=2000)
    ip_address: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
