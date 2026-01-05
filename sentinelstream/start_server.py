"""Start server with database initialization"""
import asyncio
import sys
import uvicorn
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db


async def initialize():
    """Initialize database before starting server"""
    print("[INFO] Initializing database...")
    try:
        await init_db()
    except Exception as e:
        print(f"[WARNING] Database initialization warning: {e}")
        print("Server will start but database operations may fail")


if __name__ == "__main__":
    # Initialize database
    asyncio.run(initialize())
    
    # Start server
    print("\n[INFO] Starting SentinelStream server...")
    print("[INFO] API Documentation: http://localhost:8000/docs")
    print("[INFO] Health Check: http://localhost:8000/health")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

