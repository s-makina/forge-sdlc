"""Authentication and session routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import codec
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, OperatorStatus
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = auth.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = codec.create(user.id)
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return LoginResponse(email=user.email, display_name=user.display_name, is_operator=user.is_operator)


@router.post("/logout")
def logout(response: Response, settings: Settings = Depends(get_settings)) -> None:
    response.delete_cookie(settings.session_cookie_name)


@router.get("/me", response_model=OperatorStatus)
def me(user: User | None = Depends(get_current_user)) -> OperatorStatus:
    if user is None:
        return OperatorStatus(email=None, is_authenticated=False)
    return OperatorStatus(email=user.email, is_authenticated=True)
