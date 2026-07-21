from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateUser:
    email: str
    password: str
    phone: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateUser:
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class AccessToken:
    access_token: str
    token_type: str = "bearer"
