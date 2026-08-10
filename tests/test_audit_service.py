from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.application.audit.services import AuditService
from app.domain.audit.models import AuditLogEntry
from app.domain.users.models import User

ADMIN_ID = UUID("00000000-0000-0000-0000-000000000001")


class InMemoryAuditRepository:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.entries: list[AuditLogEntry] = []

    async def is_enabled(self) -> bool:
        return self.enabled

    async def set_enabled(self, enabled: bool) -> bool:
        self.enabled = enabled
        return enabled

    async def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        self.entries.append(entry)
        return entry

    async def list(
        self, *, from_: datetime, to: datetime, offset: int, limit: int
    ) -> list[AuditLogEntry]:
        return [entry for entry in self.entries if from_ <= entry.created_at <= to][
            offset : offset + limit
        ]


def admin() -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        password_hash="hash",
        name="Ada",
        surname="Admin",
        role="admin",
        is_superuser=True,
    )


async def test_audit_record_snapshots_actor_and_filters_date_range() -> None:
    repository = InMemoryAuditRepository()
    service = AuditService(repository)

    entry = await service.record(
        actor=admin(),
        action="crm.status_changed",
        entity_type="order",
        entity_id="order-1",
        details="payment_verification → assembling",
        ip_address="127.0.0.1",
    )

    assert entry is not None
    assert entry.admin_name == "Ada Admin"
    assert entry.admin_email == "admin@example.com"
    assert entry.ip_address == "127.0.0.1"
    now = datetime.now(UTC)
    assert await service.list(from_=now - timedelta(days=1), to=now, offset=0, limit=100) == [entry]


async def test_disabled_audit_logging_does_not_persist_actions() -> None:
    repository = InMemoryAuditRepository(enabled=False)
    service = AuditService(repository)

    result = await service.record(
        actor=admin(), action="tag.created", entity_type="tag", entity_id="tag-1"
    )

    assert result is None
    assert repository.entries == []


async def test_audit_logging_setting_can_be_toggled() -> None:
    repository = InMemoryAuditRepository(enabled=True)
    service = AuditService(repository)

    assert await service.set_enabled(False) is False
    assert await service.is_enabled() is False
