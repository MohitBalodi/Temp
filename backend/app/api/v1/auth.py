from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.core.security import TokenError
from app.models import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: DbSession) -> TokenPair:
    """Both outcomes are written to the audit log; a failure keeps only the
    email's domain."""
    return auth_service.login(db, body.email, body.password)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        return auth_service.refresh_tokens(db, body.refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
