"""Pytest configuration and fixtures"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db import get_db, Base
from app.config import settings

# Test database - use in-memory SQLite for testing if PostgreSQL not available
import os
if os.getenv("TEST_DATABASE_URL"):
    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
else:
    # Fallback to PostgreSQL default
    TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/frauddb_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create test database tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_transaction_request():
    """Sample transaction request data"""
    return {
        "user_id": "user123",
        "amount": 100.0,
        "currency": "USD",
        "location": "New York, NY",
        "merchant_id": "merchant456",
        "transaction_type": "purchase",
        "idempotency_key": "test-key-123",
        "metadata": {}
    }

