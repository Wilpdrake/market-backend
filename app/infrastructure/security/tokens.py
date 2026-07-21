from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class JwtTokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expires_minutes: int = 30,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expires_minutes = expires_minutes

    def create(self, user_id: UUID) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=self.expires_minutes)},
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid token") from error
