from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.exceptions import ConflictError
from app.domain.tags.models import Tag
from app.infrastructure.database.models import TagModel


def _to_entity(model: TagModel) -> Tag:
    return Tag(
        id=model.id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, tag: Tag) -> Tag:
        model = TagModel(**self._values(tag))
        self.session.add(model)
        await self._commit_unique_slug()
        await self.session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, tag_id: UUID) -> Tag | None:
        model = await self.session.get(TagModel, tag_id)
        return _to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Tag | None:
        model = await self.session.scalar(select(TagModel).where(TagModel.slug == slug))
        return _to_entity(model) if model else None

    async def list(self) -> list[Tag]:
        models = await self.session.scalars(select(TagModel).order_by(TagModel.name.asc()))
        return [_to_entity(model) for model in models]

    async def list_by_ids(self, tag_ids: tuple[UUID, ...]) -> Sequence[Tag]:
        if not tag_ids:
            return []
        models = list(await self.session.scalars(select(TagModel).where(TagModel.id.in_(tag_ids))))
        by_id = {model.id: _to_entity(model) for model in models}
        return [by_id[tag_id] for tag_id in tag_ids if tag_id in by_id]

    async def save(self, tag: Tag) -> Tag:
        model = await self.session.get(TagModel, tag.id)
        if model is None:
            raise LookupError("Tag not found")
        for name, value in self._values(tag).items():
            setattr(model, name, value)
        await self._commit_unique_slug()
        await self.session.refresh(model)
        return _to_entity(model)

    async def delete(self, tag_id: UUID) -> None:
        await self.session.execute(delete(TagModel).where(TagModel.id == tag_id))
        await self.session.commit()

    async def _commit_unique_slug(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError("Tag slug already exists") from error

    @staticmethod
    def _values(tag: Tag) -> dict[str, object]:
        return {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
        }
