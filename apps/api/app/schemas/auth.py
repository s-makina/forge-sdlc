"""Authentication schemas."""

from pydantic import BaseModel

from app.schemas.email import EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    email: EmailStr
    display_name: str | None
    is_operator: bool


class OperatorStatus(BaseModel):
    email: EmailStr | None = None
    is_authenticated: bool
