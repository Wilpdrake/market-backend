class ApplicationError(Exception):
    """Base error safe to expose through the API."""


class ConflictError(ApplicationError):
    pass


class NotFoundError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class InvalidVerificationTokenError(ApplicationError):
    pass


class PermissionDeniedError(ApplicationError):
    pass
