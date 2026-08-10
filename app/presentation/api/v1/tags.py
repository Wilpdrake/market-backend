from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from app.application.tags.services import TagService
from app.domain.tags.models import Tag
from app.presentation.api.v1.admin.schemas import TagResponse

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
@inject
async def list_tags(service: FromDishka[TagService]) -> list[Tag]:
    return await service.list()
