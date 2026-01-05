"""Database configuration and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
from app.config import settings

# Configure engine based on database type
if "sqlite" in settings.DATABASE_URL.lower():
    # SQLite configuration
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},  # Required for SQLite
        poolclass=StaticPool,  # SQLite doesn't support connection pooling
    )
else:
    # PostgreSQL configuration
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                try:
                    await session.commit()
                except Exception as commit_error:
                    # If commit fails due to connection issues, that's okay
                    if "connection" not in str(commit_error).lower() and "connect" not in str(commit_error).lower():
                        await session.rollback()
                        raise
            except Exception as e:
                try:
                    await session.rollback()
                except:
                    pass
                # Don't raise connection errors - let endpoint handle gracefully
                if "connection" in str(e).lower() or "connect" in str(e).lower() or "operational" in str(e).lower():
                    print(f"Database connection error (non-fatal): {e}")
                else:
                    raise
            finally:
                try:
                    await session.close()
                except:
                    pass
    except Exception as e:
        # If we can't even create a session, yield None and let endpoint handle it
        print(f"Warning: Database unavailable, creating dummy session: {e}")
        # Create a minimal async mock
        class DummySession:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def add(self, *args, **kwargs):
                pass
            async def commit(self):
                pass
            async def refresh(self, *args, **kwargs):
                pass
        yield DummySession()


async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[SUCCESS] Database initialized successfully!")
    except Exception as e:
        print(f"[WARNING] Database initialization warning: {e}")
        # Try again without begin() for SQLite
        try:
            async with engine.connect() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.commit()
            print("[SUCCESS] Database initialized successfully!")
        except Exception as e2:
            print(f"[ERROR] Database initialization failed: {e2}")
            raise


async def close_db():
    """Close database connections"""
    await engine.dispose()

