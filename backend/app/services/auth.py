from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import TokenPair
from app.services import audit

# Verified against when the email is unknown, so response time doesn't reveal
# which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    # A deactivated institution keeps its certificates verifiable, but its
    # people can no longer sign in.
    if user.institution is not None and not user.institution.is_active:
        return None
    return user


def _email_domain(email: str) -> str:
    """Only the domain of a failed attempt is kept: enough to spot a pattern,
    not enough to build a list of who tried to sign in."""
    _, _, domain = normalize_email(email).partition("@")
    return domain or "unknown"


def login(db: Session, email: str, password: str) -> TokenPair:
    """Authenticate, record the attempt, and return a token pair.

    Raises `AppError` with the same message whether the email is unknown or the
    password is wrong. Never records the email or the password.
    """
    user = authenticate(db, email, password)
    if user is None:
        audit.record(
            db,
            actor_id=None,
            action="auth.login_failed",
            entity="user",
            meta={"email_domain": _email_domain(email)},
        )
        db.commit()
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")

    audit.record(
        db,
        actor_id=user.id,
        action="auth.login",
        entity="user",
        entity_id=str(user.id),
        meta={"role": user.role},
    )
    db.commit()
    return issue_tokens(user)


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
        access_expires_in=settings.access_token_minutes * 60,
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    """Exchange a valid refresh token for a new pair. Raises TokenError."""
    user_id = decode_token(refresh_token, expected_type="refresh")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise TokenError("invalid_token", "User not found or inactive.")
    return issue_tokens(user)
