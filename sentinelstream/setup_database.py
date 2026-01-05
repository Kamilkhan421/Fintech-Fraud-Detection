"""Setup script to initialize the database"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db, engine, Base
from app.models import *  # Import all models to register them


async def setup():
    """Initialize database with all tables"""
    print("Initializing database...")
    print(f"Database URL: {engine.url}")
    
    try:
        await init_db()
        print("\n[SUCCESS] Database setup completed successfully!")
        print("\nYou can now start the server with:")
        print("  python start_server.py")
        print("  or")
        print("  python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n[ERROR] Database setup failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup())

