import secrets

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Header, Response, status

from app.application.users.services import UserService
from app.core.config import Settings
from app.presentation.api.v1.schemas import TelegramUpdate

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def webhook(
    update: TelegramUpdate,
    users: FromDishka[UserService],
    settings: FromDishka[Settings],
    secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> Response:
    if settings.telegram_webhook_secret and not secrets.compare_digest(
        secret or "", settings.telegram_webhook_secret
    ):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    message = update.message
    if message and message.text and message.text.startswith("/start "):
        token = message.text.split(maxsplit=1)[1]
        sender = message.from_user
        telegram_id = sender.id if sender else message.chat.id
        await users.confirm_telegram(token, telegram_id, sender.username if sender else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
