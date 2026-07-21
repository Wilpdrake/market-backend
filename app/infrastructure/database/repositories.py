from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.exceptions import ConflictError
from app.domain.users.entities import User
from app.infrastructure.database.models import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        phone=model.phone,
        name=model.name,
        surname=model.surname,
        patronymic=model.patronymic,
        comment=model.comment,
        avatar_image=model.avatar_image,
        header_image=model.header_image,
        created_by=model.created_by,
        telegram_id=model.telegram_id,
        telegram_username=model.telegram_username,
        is_active=model.is_active,
        is_superuser=model.is_superuser,
        is_email_verified=model.is_email_verified,
        is_phone_verified=model.is_phone_verified,
        email_verification_token_hash=model.email_verification_token_hash,
        phone_verification_token_hash=model.phone_verification_token_hash,
        telegram_verification_token_hash=model.telegram_verification_token_hash,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user: User) -> User:
        model = UserModel(**self._values(user))
        self.session.add(model)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError("A user with this email already exists") from error
        await self.session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self.session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        model = await self.session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_entity(model) if model else None

    async def list(self, *, offset: int, limit: int) -> list[User]:
        models = await self.session.scalars(
            select(UserModel).order_by(UserModel.created_at).offset(offset).limit(limit)
        )
        return [_to_entity(model) for model in models]

    async def save(self, user: User) -> User:
        model = await self.session.get(UserModel, user.id)
        if model is None:
            raise LookupError("User not found")
        for name, value in self._values(user).items():
            setattr(model, name, value)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model)

    async def delete(self, user_id: UUID) -> None:
        await self.session.execute(delete(UserModel).where(UserModel.id == user_id))
        await self.session.commit()

    @staticmethod
    def _values(user: User) -> dict[str, object]:
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "phone": user.phone,
            "name": user.name,
            "surname": user.surname,
            "patronymic": user.patronymic,
            "comment": user.comment,
            "avatar_image": user.avatar_image,
            "header_image": user.header_image,
            "created_by": user.created_by,
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
            "email_verification_token_hash": user.email_verification_token_hash,
            "phone_verification_token_hash": user.phone_verification_token_hash,
            "telegram_verification_token_hash": user.telegram_verification_token_hash,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
