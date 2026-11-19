"""Authentication service: bootstrap operator and credential checks."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User

_INSECURE_DEFAULT_PASSWORD = "change-me"


def bootstrap_operator(db: Session) -> None:
    """Ensure the configured bootstrap operator account exists.

    Refuses to create the operator with the insecure default password outside
    development, so a production deploy can never ship a known credential.
    """
    settings = get_settings()
    stmt = select(User).where(User.email == settings.bootstrap_operator_email)
    if db.scalar(stmt) is not None:
        return
    if (
        settings.environment != "development"
        and settings.bootstrap_operator_password == _INSECURE_DEFAULT_PASSWORD
    ):
        raise RuntimeError(
            "Refusing to bootstrap the operator with the default password outside "
            "development. Set BOOTSTRAP_OPERATOR_PASSWORD."
        )
    db.add(
        User(
            email=settings.bootstrap_operator_email,
            password_hash=hash_password(settings.bootstrap_operator_password),
            display_name="Operator",
            is_active=True,
            is_operator=True,
        )
    )
    db.commit()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None."""
    stmt = select(User).where(User.email == email, User.is_active.is_(True))
    user = db.scalar(stmt)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
