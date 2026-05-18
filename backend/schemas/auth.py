from __future__ import annotations

from datetime import timedelta, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_serializer


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: UUID | str
    username: str
    email: EmailStr
    is_active: bool
    created_at: Optional[datetime | str] = None
    updated_at: Optional[datetime | str] = None

    model_config = {"from_attributes": True}

    @field_serializer("id", when_used="json")
    def serialize_id(self, value: UUID | str) -> str:
        return str(value)

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, value: Optional[datetime | str]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat() if isinstance(value, datetime) else value

    @field_serializer("updated_at", when_used="json")
    def serialize_updated_at(self, value: Optional[datetime | str]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat() if isinstance(value, datetime) else value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int]
    user: Optional[UserResponse] = None
