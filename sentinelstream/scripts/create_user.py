"""Script to create a test user"""
import asyncio
import sys
from app.db import AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash


async def create_user(email: str, password: str, user_id: str):
    """Create a new user"""
    async with AsyncSessionLocal() as session:
        # Check if user exists
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"User with email {email} already exists!")
            return
        
        # Create new user
        user = User(
            email=email,
            user_id=user_id,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        
        session.add(user)
        await session.commit()
        print(f"User created successfully!")
        print(f"Email: {email}")
        print(f"User ID: {user_id}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_user.py <email> <password> <user_id>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    user_id = sys.argv[3]
    
    asyncio.run(create_user(email, password, user_id))

