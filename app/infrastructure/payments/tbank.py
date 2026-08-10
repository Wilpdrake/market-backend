"""T-Bank (Тинькофф) internet acquiring adapter.

Protocol notes that shape this module:

* Amounts travel to the provider in **kopecks** as integers (``3 руб. 12 коп.`` → ``312``).
* Every request is signed with ``Token``: take root-level scalar pairs only (no nested objects
  or arrays), add ``{"Password": ...}``, sort by key, concatenate the values and hash with
  SHA-256. See https://developer.tbank.ru/eacq/intro/developer/token
* Notifications are signed the same way, excluding ``Token`` itself and nested objects
  (``Data``, ``Receipt``); booleans must be lowercased (``true``/``false``) before hashing.
* A notification must be answered with the literal body ``OK``, otherwise T-Bank retries it
  hourly for 24 hours and then daily for a month.

``TBANK_TERMINAL_KEY``/``TBANK_PASSWORD`` are unset in development. In that case
``StubPaymentGateway`` is wired instead, so checkout stays runnable without provider credentials.
"""

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from app.application.payments.exceptions import PaymentProviderError
from app.application.payments.ports import InitPaymentCommand, ProviderPayment
from app.domain.payments.models import PaymentConfirmation, PaymentOption

PRODUCTION_API_URL = "https://securepay.tinkoff.ru/v2"


def to_kopecks(amount: Decimal) -> int:
    """Convert a major-unit decimal amount into the integer minor units T-Bank expects."""
    return int((amount * 100).quantize(Decimal("1")))


def sign(payload: dict[str, Any], password: str) -> str:
    """Build the T-Bank ``Token`` for a request or a notification payload."""
    pairs: dict[str, str] = {}
    for key, value in payload.items():
        if key == "Token" or isinstance(value, dict | list | type(None)):
            continue
        pairs[key] = "true" if value is True else "false" if value is False else str(value)
    pairs["Password"] = password
    concatenated = "".join(pairs[key] for key in sorted(pairs))
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()


class TBankPaymentGateway:
    """HTTP adapter for the T-Bank acquiring API."""

    def __init__(
        self,
        *,
        terminal_key: str,
        password: str,
        options: list[PaymentOption],
        api_url: str = PRODUCTION_API_URL,
        success_url: str | None = None,
        fail_url: str | None = None,
        notification_url: str | None = None,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.terminal_key = terminal_key
        self.password = password
        self._options = options
        self.api_url = api_url.rstrip("/")
        self.success_url = success_url
        self.fail_url = fail_url
        self.notification_url = notification_url
        self.timeout = timeout
        self._client = client

    def options(self) -> list[PaymentOption]:
        return list(self._options)

    async def init_payment(self, command: InitPaymentCommand) -> ProviderPayment:
        payload: dict[str, Any] = {
            "TerminalKey": self.terminal_key,
            "Amount": to_kopecks(command.amount),
            # ``OrderId`` must be unique per provider payment, so the local payment id is used:
            # a retried checkout attempt reuses the stored payment instead of calling Init again.
            "OrderId": str(command.payment_id),
            "Description": command.description,
            "PayType": "O",
            "Language": "ru",
        }
        if self.success_url:
            payload["SuccessURL"] = self.success_url
        if self.fail_url:
            payload["FailURL"] = self.fail_url
        if self.notification_url:
            payload["NotificationURL"] = self.notification_url

        payload["Token"] = sign(payload, self.password)
        # DATA is excluded from the signature by the protocol, so it is attached afterwards.
        payload["DATA"] = {"Email": command.customer_email, "Phone": command.customer_phone}

        response = await self._call("Init", payload)
        return self._to_provider_payment(
            response,
            confirmation=self._confirmation(response, command.option),
        )

    async def get_state(self, provider_payment_id: str) -> ProviderPayment:
        payload: dict[str, Any] = {
            "TerminalKey": self.terminal_key,
            "PaymentId": provider_payment_id,
        }
        payload["Token"] = sign(payload, self.password)
        return self._to_provider_payment(await self._call("GetState", payload))

    async def cancel(self, provider_payment_id: str) -> ProviderPayment:
        payload: dict[str, Any] = {
            "TerminalKey": self.terminal_key,
            "PaymentId": provider_payment_id,
        }
        payload["Token"] = sign(payload, self.password)
        return self._to_provider_payment(await self._call("Cancel", payload))

    def verify_notification(self, payload: dict[str, object]) -> bool:
        received = payload.get("Token")
        if not isinstance(received, str) or not received:
            return False
        if str(payload.get("TerminalKey", "")) != self.terminal_key:
            return False
        expected = sign(dict(payload), self.password)
        return hmac.compare_digest(received, expected)

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.api_url}/{method}"
        try:
            if self._client is not None:
                response = await self._client.post(url, json=payload, timeout=self.timeout)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
        except httpx.HTTPError as error:
            raise PaymentProviderError(f"T-Bank request failed: {error}") from error

        if response.status_code >= 500:
            raise PaymentProviderError(f"T-Bank returned HTTP {response.status_code}")
        try:
            body = response.json()
        except json.JSONDecodeError as error:
            raise PaymentProviderError("T-Bank returned a malformed response") from error
        if not isinstance(body, dict):
            raise PaymentProviderError("T-Bank returned a malformed response")
        return body

    def _to_provider_payment(
        self,
        body: dict[str, Any],
        *,
        confirmation: PaymentConfirmation | None = None,
    ) -> ProviderPayment:
        provider_payment_id = body.get("PaymentId")
        if body.get("Success") is False and provider_payment_id is None:
            raise PaymentProviderError(self._error_message(body))
        if provider_payment_id is None:
            raise PaymentProviderError("T-Bank response is missing PaymentId")
        return ProviderPayment(
            provider_payment_id=str(provider_payment_id),
            status=str(body.get("Status", "")),
            confirmation=confirmation,
            failure_message=None if body.get("Success") else self._error_message(body),
        )

    @staticmethod
    def _confirmation(
        body: dict[str, Any],
        option: PaymentOption,
    ) -> PaymentConfirmation | None:
        url = body.get("PaymentURL")
        if not url:
            return None
        return PaymentConfirmation(type="qr" if option.kind == "sbp" else "redirect", url=str(url))

    @staticmethod
    def _error_message(body: dict[str, Any]) -> str:
        code = body.get("ErrorCode", "")
        message = body.get("Message") or "T-Bank rejected the request"
        details = body.get("Details")
        text = f"{message} ({code})" if code else str(message)
        return f"{text}: {details}" if details else text


class StubPaymentGateway:
    """Deterministic in-memory gateway used when provider credentials are absent.

    It keeps the checkout flow exercisable end to end in development and tests: ``init_payment``
    returns a synthetic confirmation URL and payments settle as ``CONFIRMED`` on the next poll.
    """

    def __init__(
        self,
        options: list[PaymentOption],
        *,
        base_url: str = "https://sandbox.local",
    ) -> None:
        self._options = options
        self.base_url = base_url.rstrip("/")
        self._states: dict[str, str] = {}

    def options(self) -> list[PaymentOption]:
        return list(self._options)

    async def init_payment(self, command: InitPaymentCommand) -> ProviderPayment:
        provider_payment_id = str(uuid4().int % 10**10)
        self._states[provider_payment_id] = "NEW"
        return ProviderPayment(
            provider_payment_id=provider_payment_id,
            status="NEW",
            confirmation=PaymentConfirmation(
                type="qr" if command.option.kind == "sbp" else "redirect",
                url=f"{self.base_url}/pay/{provider_payment_id}",
            ),
        )

    async def get_state(self, provider_payment_id: str) -> ProviderPayment:
        current = self._states.get(provider_payment_id, "NEW")
        following = "CONFIRMED" if current == "NEW" else current
        self._states[provider_payment_id] = following
        return ProviderPayment(provider_payment_id=provider_payment_id, status=following)

    async def cancel(self, provider_payment_id: str) -> ProviderPayment:
        self._states[provider_payment_id] = "CANCELED"
        return ProviderPayment(provider_payment_id=provider_payment_id, status="CANCELED")

    def verify_notification(self, payload: dict[str, object]) -> bool:
        return "PaymentId" in payload


def default_payment_options() -> list[PaymentOption]:
    return [
        PaymentOption(id="tbank-card", title="Банковская карта", kind="card", enabled=True),
        PaymentOption(id="tbank-sbp", title="СБП", kind="sbp", enabled=True),
    ]


__all__ = [
    "PRODUCTION_API_URL",
    "StubPaymentGateway",
    "TBankPaymentGateway",
    "default_payment_options",
    "sign",
    "to_kopecks",
]
