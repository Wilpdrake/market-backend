from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query

from app.application.audit.services import AuditService
from app.application.users.services import AuthService
from app.domain.audit.models import AuditLogEntry
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import AuditLogResponse
from app.presentation.api.v1.auth import AuthorizationHeader as AuthHeader

router = APIRouter(prefix="/audit-log")


@router.get("", response_model=list[AuditLogResponse])
@inject
async def list_audit_log(
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[AuditService],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[AuditLogEntry]:
    await current_admin(auth_header, auth)
    from_ = datetime.combine(from_date, time.min, tzinfo=UTC)
    to = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=UTC)
    return await service.list(from_=from_, to=to, offset=offset, limit=limit)
