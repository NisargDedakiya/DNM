from __future__ import annotations

from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import hash_password, verify_password
from backend.auth.jwt_handler import create_access_token
from backend.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    async def register_user(self, username: str, email: str, password: str) -> User:
        # Check duplicates
        if await self.get_by_email(email):
            raise ValueError("Email already registered")
        if await self.get_by_username(username):
            raise ValueError("Username already taken")

        hashed = hash_password(password)
        user = User(username=username, email=email, hashed_password=hashed)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = await self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None

        token = create_access_token(subject=str(user.id), expires_delta=timedelta(hours=8))
        return token
