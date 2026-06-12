"""Pydantic schemas for authentication."""

from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    email: str
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(schemas.BaseUserCreate):
    email: str
    password: str
