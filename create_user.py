import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import AsyncSessionLocal, init_db
from backend.services.auth_service import AuthService
from backend.core.config import settings

async def create_user():
    await init_db()
    async with AsyncSessionLocal() as db:
        svc = AuthService(db)
        
        # Check if user already exists
        existing_user = await svc.get_by_username("Nisarg13031")
        if not existing_user:
            try:
                user = await svc.register_user(
                    username="Nisarg13031", 
                    email="nisarg13031@nisarghunter.com", 
                    password="123456789"
                )
                print(f"✓ User created successfully: {user.username}")
                print(f"  Email: {user.email}")
                print(f"  ID: {user.id}")
            except Exception as e:
                print(f"✗ Failed to create user: {e}")
        else:
            print(f"✓ User 'Nisarg13031' already exists")

if __name__ == "__main__":
    asyncio.run(create_user())
