from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Request, Response, status

from app.application.audit.services import AuditService
from app.application.tags.models import CreateTag, UpdateTag
from app.application.tags.services import TagService
from app.application.users.services import AuthService
from app.domain.tags.models import Tag
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import TagCreateRequest, TagResponse, TagUpdateRequest
from app.presentation.api.v1.auth import AuthorizationHeader as AuthHeader

router = APIRouter(prefix="/tags")


@router.get("", response_model=list[TagResponse])
@inject
async def list_tags(
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[TagService],
) -> list[Tag]:
    await current_admin(auth_header, auth)
    return await service.list()


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_tag(
    data: TagCreateRequest,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[TagService],
    audit: FromDishka[AuditService],
) -> Tag:
    actor = await current_admin(auth_header, auth)
    tag = await service.create(CreateTag(**data.model_dump()))
    await audit.record(
        actor=actor,
        action="tag.created",
        entity_type="tag",
        entity_id=str(tag.id),
        details=f"Created {tag.name} ({tag.slug})",
        ip_address=request.client.host if request.client else None,
    )
    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
@inject
async def update_tag(
    tag_id: UUID,
    data: TagUpdateRequest,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[TagService],
    audit: FromDishka[AuditService],
) -> Tag:
    actor = await current_admin(auth_header, auth)
    tag = await service.update(
        tag_id,
        UpdateTag(
            **data.model_dump(),
            clear_fields=frozenset(
                name for name in data.model_fields_set if getattr(data, name) is None
            ),
        ),
    )
    await audit.record(
        actor=actor,
        action="tag.updated",
        entity_type="tag",
        entity_id=str(tag.id),
        details=f"Updated {tag.name} ({tag.slug})",
        ip_address=request.client.host if request.client else None,
    )
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_tag(
    tag_id: UUID,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[TagService],
    audit: FromDishka[AuditService],
) -> Response:
    actor = await current_admin(auth_header, auth)
    tag = await service.get(tag_id)
    await service.delete(tag_id)
    await audit.record(
        actor=actor,
        action="tag.deleted",
        entity_type="tag",
        entity_id=str(tag.id),
        details=f"Deleted {tag.name} ({tag.slug})",
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
