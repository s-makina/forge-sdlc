"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None
    is_active: bool
    is_operator: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
