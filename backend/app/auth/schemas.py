"""Pydantic schemas for the auth module.

Defines request/response shapes for register, login, current-user and tokens.
Pydantic does most of the validation work (email format, password length, etc.).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """Public user representation (never exposes hashed_password)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """JWT response."""

    access_token: str
    token_type: str = "bearer"
