class PaymentAlreadyExists(Exception):
    """A unique payment invariant won a concurrent checkout race."""


class PaymentProviderError(Exception):
    """The acquiring provider rejected the request or is unavailable.

    Mapped to HTTP 502 so the storefront can distinguish an upstream failure from a business
    rule violation.
    """
