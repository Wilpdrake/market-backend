from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.payments.exceptions import PaymentAlreadyExists
from app.domain.payments.models import (
    ConfirmationType,
    Payment,
    PaymentConfirmation,
    PaymentStatus,
)
from app.infrastructure.database.models import PaymentModel


def _to_entity(model: PaymentModel) -> Payment:
    confirmation = (
        PaymentConfirmation(
            type=cast(ConfirmationType, model.confirmation_type),
            url=model.confirmation_url,
        )
        if model.confirmation_type and model.confirmation_url
        else None
    )
    return Payment(
        id=model.id,
        order_id=model.order_id,
        provider=model.provider,
        provider_payment_id=model.provider_payment_id,
        payment_option_id=model.payment_option_id,
        idempotency_key=model.idempotency_key,
        status=cast(PaymentStatus, model.status),
        amount=model.amount,
        currency=model.currency,
        confirmation=confirmation,
        failure_message=model.failure_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, payment: Payment) -> Payment:
        model = PaymentModel(**self._values(payment))
        self.session.add(model)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise PaymentAlreadyExists from error
        await self.session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        model = await self.session.get(PaymentModel, payment_id)
        return _to_entity(model) if model else None

    async def get_by_idempotency_key(self, order_id: UUID, key: str) -> Payment | None:
        model = await self.session.scalar(
            select(PaymentModel).where(
                PaymentModel.order_id == order_id,
                PaymentModel.idempotency_key == key,
            )
        )
        return _to_entity(model) if model else None

    async def get_active_for_order(self, order_id: UUID) -> Payment | None:
        """Return the most recent payment for the order; checkout keeps at most one alive."""
        model = await self.session.scalar(
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.created_at.desc())
            .limit(1)
        )
        return _to_entity(model) if model else None

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        model = await self.session.scalar(
            select(PaymentModel).where(PaymentModel.provider_payment_id == provider_payment_id)
        )
        return _to_entity(model) if model else None

    async def save(self, payment: Payment) -> Payment:
        model = await self.session.get(PaymentModel, payment.id)
        if model is None:
            raise LookupError("Payment not found")
        for name, value in self._values(payment).items():
            setattr(model, name, value)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model)

    @staticmethod
    def _values(payment: Payment) -> dict[str, object]:
        return {
            "id": payment.id,
            "order_id": payment.order_id,
            "provider": payment.provider,
            "provider_payment_id": payment.provider_payment_id,
            "payment_option_id": payment.payment_option_id,
            "idempotency_key": payment.idempotency_key,
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "confirmation_type": payment.confirmation.type if payment.confirmation else None,
            "confirmation_url": payment.confirmation.url if payment.confirmation else None,
            "failure_message": payment.failure_message,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }
