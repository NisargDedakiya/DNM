import asyncio
from backend.database.session import AsyncSessionLocal
from backend.models.user import User
from sqlalchemy import select

async def check_user():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter_by(username='Nisarg13031'))
        user = result.scalar_one_or_none()
        print(f'User: {user.username if user else "NOT FOUND"}')

if __name__ == '__main__':
    asyncio.run(check_user())
