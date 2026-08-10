from uuid import UUID

import pytest

from app.application.tags.models import CreateTag, UpdateTag
from app.application.tags.services import TagService
from app.application.users.exceptions import ConflictError, NotFoundError
from app.domain.tags.models import Tag


class InMemoryTagRepository:
    def __init__(self) -> None:
        self.tags: dict[UUID, Tag] = {}

    async def add(self, tag: Tag) -> Tag:
        self.tags[tag.id] = tag
        return tag

    async def get_by_id(self, tag_id: UUID) -> Tag | None:
        return self.tags.get(tag_id)

    async def get_by_slug(self, slug: str) -> Tag | None:
        return next((tag for tag in self.tags.values() if tag.slug == slug), None)

    async def list(self) -> list[Tag]:
        return sorted(self.tags.values(), key=lambda tag: tag.name.casefold())

    async def save(self, tag: Tag) -> Tag:
        self.tags[tag.id] = tag
        return tag

    async def delete(self, tag_id: UUID) -> None:
        self.tags.pop(tag_id, None)


async def test_tag_crud_normalizes_slug_and_preserves_identity() -> None:
    repository = InMemoryTagRepository()
    service = TagService(repository)

    created = await service.create(
        CreateTag(name="  Home Decor  ", slug=" HOME--Decor ", description="  Handmade  ")
    )
    updated = await service.update(
        created.id,
        UpdateTag(name="Decor", description=None, clear_fields=frozenset({"description"})),
    )

    assert created.slug == "home-decor"
    assert updated.id == created.id
    assert updated.name == "Decor"
    assert updated.description is None
    assert await service.list() == [updated]


async def test_tag_slug_must_be_unique_for_create_and_update() -> None:
    repository = InMemoryTagRepository()
    service = TagService(repository)
    first = await service.create(CreateTag(name="First", slug="same"))
    second = await service.create(CreateTag(name="Second", slug="other"))

    with pytest.raises(ConflictError, match="slug"):
        await service.create(CreateTag(name="Duplicate", slug="same"))
    with pytest.raises(ConflictError, match="slug"):
        await service.update(second.id, UpdateTag(slug=first.slug))


async def test_missing_tag_cannot_be_updated_or_deleted() -> None:
    service = TagService(InMemoryTagRepository())
    missing = UUID("00000000-0000-0000-0000-000000000099")

    with pytest.raises(NotFoundError, match="Tag"):
        await service.update(missing, UpdateTag(name="Missing"))
    with pytest.raises(NotFoundError, match="Tag"):
        await service.delete(missing)
