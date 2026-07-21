import logging

logger = logging.getLogger(__name__)


class LoggingVerificationNotifier:
    """Development adapter; replace with SMTP/SMS providers in production."""

    def __init__(self, *, expose_tokens: bool) -> None:
        self.expose_tokens = expose_tokens

    def _ensure_development(self) -> None:
        if not self.expose_tokens:
            raise RuntimeError("A production verification provider is not configured")

    async def send_email_verification(self, email: str, token: str) -> None:
        self._ensure_development()
        logger.info("Email verification requested for %s; token=%s", email, token)

    async def send_phone_verification(self, phone: str, token: str) -> None:
        self._ensure_development()
        logger.info("Phone verification requested for %s; code=%s", phone, token)
