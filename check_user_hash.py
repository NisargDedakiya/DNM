import asyncio
import sys
import os

sys.path.append(os.getcwd())

from backend.database.session import AsyncSessionLocal
from backend.models.user import User
from sqlalchemy import select

async def check_user():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "Nisarg13031"))
        user = result.scalars().first()
        if user:
            print(f"Username: {user.username}")
            print(f"Hashed Password: {user.hashed_password}")
            length = len(user.hashed_password) if user.hashed_password else "None"
            print(f"Hash Length: {length}")
        else:
            print("User not found")

if __name__ == "__main__":
    asyncio.run(check_user())
