from app.application.users.exceptions import PermissionDeniedError
from app.application.users.services import AuthService
from app.domain.users.models import User
from app.presentation.api.v1.auth import current_user


async def current_admin(authorization: str | None, auth: AuthService) -> User:
    user = await current_user(authorization, auth)
    if not user.is_superuser:
        raise PermissionDeniedError("Administrator privileges required")
    return user
