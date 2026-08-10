from datetime import datetime

from app.application.audit.ports import AuditRepository
from app.domain.audit.models import AuditLogEntry
from app.domain.users.models import User


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    async def is_enabled(self) -> bool:
        return await self.repository.is_enabled()

    async def set_enabled(self, enabled: bool) -> bool:
        return await self.repository.set_enabled(enabled)

    async def record(
        self,
        *,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLogEntry | None:
        if not await self.repository.is_enabled():
            return None
        admin_name = " ".join(part for part in (actor.name, actor.surname) if part).strip()
        if not admin_name:
            admin_name = actor.username or actor.email
        return await self.repository.add(
            AuditLogEntry(
                admin_id=actor.id,
                admin_name=admin_name,
                admin_email=actor.email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address=ip_address,
            )
        )

    async def list(
        self, *, from_: datetime, to: datetime, offset: int = 0, limit: int = 100
    ) -> list[AuditLogEntry]:
        return await self.repository.list(from_=from_, to=to, offset=offset, limit=limit)
