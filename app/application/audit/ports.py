from datetime import datetime
from typing import Protocol

from app.domain.audit.models import AuditLogEntry


class AuditRepository(Protocol):
    async def is_enabled(self) -> bool: ...

    async def set_enabled(self, enabled: bool) -> bool: ...

    async def add(self, entry: AuditLogEntry) -> AuditLogEntry: ...

    async def list(
        self, *, from_: datetime, to: datetime, offset: int, limit: int
    ) -> list[AuditLogEntry]: ...
