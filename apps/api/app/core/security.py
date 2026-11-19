"""Password hashing and session token signing."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain, hashed)


class SessionCodec:
    """Signs and verifies opaque session tokens stored in a cookie."""

    def __init__(self) -> None:
        settings = get_settings()
        self._serializer = URLSafeTimedSerializer(
            settings.session_secret_key, salt="forgesdlc-session"
        )
        self._max_age = settings.session_max_age_seconds

    def create(self, user_id: int) -> str:
        return self._serializer.dumps({"user_id": user_id})

    def read(self, token: str) -> int | None:
        try:
            data = self._serializer.loads(token, max_age=self._max_age)
        except (BadSignature, SignatureExpired):
            return None
        return int(data["user_id"])


codec = SessionCodec()
