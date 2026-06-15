"""User manager for FastAPI Users."""

from __future__ import annotations

import logging
import os

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase

from app.db.database import get_user_db
from app.db.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

logger = logging.getLogger(__name__)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.info("User %s has registered.", user.id)

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        logger.debug("User %s forgot password. Token: %s", user.id, token)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)
