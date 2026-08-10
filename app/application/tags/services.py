import re
from datetime import UTC, datetime
from unicodedata import normalize
from uuid import UUID

from app.application.tags.models import CreateTag, UpdateTag
from app.application.tags.ports import TagRepository
from app.application.users.exceptions import ConflictError, NotFoundError
from app.domain.tags.models import Tag
from app.models import replace_model as replace


def normalize_slug(value: str) -> str:
    slug = normalize("NFKC", value).strip().casefold()
    slug = re.sub(r"[^\w]+", "-", slug, flags=re.UNICODE).replace("_", "-").strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        raise ValueError("Tag slug must contain letters or numbers")
    return slug


class TagService:
    def __init__(self, repository: TagRepository) -> None:
        self.repository = repository

    async def create(self, data: CreateTag) -> Tag:
        slug = normalize_slug(data.slug)
        await self._ensure_slug_available(slug)
        return await self.repository.add(
            Tag(
                name=data.name.strip(),
                slug=slug,
                description=data.description.strip() if data.description else None,
            )
        )

    async def get(self, tag_id: UUID) -> Tag:
        tag = await self.repository.get_by_id(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found")
        return tag

    async def list(self) -> list[Tag]:
        return await self.repository.list()

    async def update(self, tag_id: UUID, data: UpdateTag) -> Tag:
        tag = await self.get(tag_id)
        slug = normalize_slug(data.slug) if data.slug is not None else tag.slug
        if slug != tag.slug:
            await self._ensure_slug_available(slug, excluding=tag.id)
        return await self.repository.save(
            replace(
                tag,
                name=data.name.strip() if data.name is not None else tag.name,
                slug=slug,
                description=(
                    None
                    if "description" in data.clear_fields
                    else data.description.strip()
                    if data.description is not None
                    else tag.description
                ),
                updated_at=datetime.now(UTC),
            )
        )

    async def delete(self, tag_id: UUID) -> None:
        await self.get(tag_id)
        await self.repository.delete(tag_id)

    async def _ensure_slug_available(self, slug: str, *, excluding: UUID | None = None) -> None:
        existing = await self.repository.get_by_slug(slug)
        if existing is not None and existing.id != excluding:
            raise ConflictError("Tag slug already exists")
