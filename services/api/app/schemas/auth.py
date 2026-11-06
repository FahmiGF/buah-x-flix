from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # Length policy lives in services.security so the API can return the
    # specific `weak_password` code instead of a generic validation error.
    password: str = Field(max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class StorageUsage(BaseModel):
    used_bytes: int
    limit_bytes: int
    percent: float


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    is_admin: bool
    storage: StorageUsage
