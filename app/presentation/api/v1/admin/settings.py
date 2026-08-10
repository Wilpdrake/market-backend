from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Request

from app.application.audit.services import AuditService
from app.application.users.services import AuthService
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import AuditLoggingSetting
from app.presentation.api.v1.auth import AuthorizationHeader as AuthHeader

router = APIRouter(prefix="/settings")


@router.get("/audit-logging", response_model=AuditLoggingSetting)
@inject
async def get_audit_logging(
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    audit: FromDishka[AuditService],
) -> AuditLoggingSetting:
    await current_admin(auth_header, auth)
    return AuditLoggingSetting(enabled=await audit.is_enabled())


@router.patch("/audit-logging", response_model=AuditLoggingSetting)
@inject
async def set_audit_logging(
    data: AuditLoggingSetting,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    audit: FromDishka[AuditService],
) -> AuditLoggingSetting:
    actor = await current_admin(auth_header, auth)
    ip_address = request.client.host if request.client else None
    if not data.enabled:
        await audit.record(
            actor=actor,
            action="audit.disabled",
            entity_type="settings",
            details="Audit logging disabled",
            ip_address=ip_address,
        )
    enabled = await audit.set_enabled(data.enabled)
    if enabled:
        await audit.record(
            actor=actor,
            action="audit.enabled",
            entity_type="settings",
            details="Audit logging enabled",
            ip_address=ip_address,
        )
    return AuditLoggingSetting(enabled=enabled)
