from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.models import AuditLogEntry
from app.infrastructure.database.models import AuditLogModel, AuditSettingModel

AUDIT_SETTING_KEY = "audit_logging"


def _to_entity(model: AuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=model.id,
        admin_id=model.admin_id,
        admin_name=model.admin_name,
        admin_email=model.admin_email,
        action=model.action,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        details=model.details,
        ip_address=model.ip_address,
        created_at=model.created_at,
    )


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_enabled(self) -> bool:
        setting = await self.session.get(AuditSettingModel, AUDIT_SETTING_KEY)
        return True if setting is None else setting.enabled

    async def set_enabled(self, enabled: bool) -> bool:
        statement = insert(AuditSettingModel).values(key=AUDIT_SETTING_KEY, enabled=enabled)
        statement = statement.on_conflict_do_update(
            index_elements=[AuditSettingModel.key], set_={"enabled": enabled}
        )
        await self.session.execute(statement)
        await self.session.commit()
        return enabled

    async def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        model = AuditLogModel(
            id=entry.id,
            admin_id=entry.admin_id,
            admin_name=entry.admin_name,
            admin_email=entry.admin_email,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            details=entry.details,
            ip_address=entry.ip_address,
            created_at=entry.created_at,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model)

    async def list(
        self, *, from_: datetime, to: datetime, offset: int, limit: int
    ) -> list[AuditLogEntry]:
        models = await self.session.scalars(
            select(AuditLogModel)
            .where(AuditLogModel.created_at >= from_, AuditLogModel.created_at < to)
            .order_by(AuditLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_entity(model) for model in models]
