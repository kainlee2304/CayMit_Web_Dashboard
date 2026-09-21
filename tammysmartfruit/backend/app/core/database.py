"""
Database Connection & Async Session Lifecycle Module
Configures Async SQLAlchemy 2.0 Engine with multi-database support:
Tries PostgreSQL 16 first, and seamlessly falls back to SQLite (aiosqlite)
with automatic schema creation and canonical seed data.
"""

import os
import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.logging import logger
from app.shared.base_model import Base

# Import all domain models for SQLAlchemy metadata registration
import app.modules.identity.models
import app.modules.organization.models
import app.modules.master_data.models
import app.modules.growing_area.models
import app.modules.farm.models
import app.modules.claims.models
import app.modules.season.models
import app.modules.material.models
import app.modules.farm_activity.models
import app.modules.audit.models
import app.modules.outbox.models

# Path for SQLite database fallback
SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tammysmartfruit.db"))
SQLITE_ASYNC_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH.replace(os.sep, '/')}"

_active_db_url = settings.DATABASE_URL
_is_sqlite = False

def create_app_engine(db_url: str) -> AsyncEngine:
    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=NullPool
        )
    return create_async_engine(
        db_url,
        echo=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True
    )

# Primary Engine
engine: AsyncEngine = create_app_engine(_active_db_url)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

def create_worker_engine(db_url: str) -> AsyncEngine:
    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=NullPool
        )
    return create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool
    )

# Worker Engine
_worker_engine: AsyncEngine = create_worker_engine(_active_db_url)
WorkerAsyncSessionLocal = async_sessionmaker(
    bind=_worker_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def check_db_health() -> bool:
    """Execute probe query to verify connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            result = await asyncio.wait_for(session.execute(text("SELECT 1;")), timeout=1.5)
            return result.scalar() == 1
    except Exception:
        return False

async def switch_to_sqlite():
    """Switch primary and worker engines to SQLite fallback."""
    global engine, AsyncSessionLocal, _worker_engine, WorkerAsyncSessionLocal, _is_sqlite, _active_db_url
    logger.warning(f"Switching database engine to SQLite fallback: {SQLITE_ASYNC_URL}")
    _is_sqlite = True
    _active_db_url = SQLITE_ASYNC_URL
    
    engine = create_app_engine(SQLITE_ASYNC_URL)
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    _worker_engine = engine
    WorkerAsyncSessionLocal = AsyncSessionLocal

async def init_database_schema_and_seeds():
    """Ensure database schema is created and canonical seed data is present."""
    global engine, _is_sqlite
    
    # 1. Test primary PostgreSQL connection if not already using SQLite
    if not _is_sqlite and "sqlite" not in _active_db_url:
        pg_ok = await check_db_health()
        if not pg_ok:
            await switch_to_sqlite()
        
    # 2. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema validated and synchronized.")
    
    # 3. Seed canonical data if not already present
    await seed_canonical_data_if_needed()

async def seed_canonical_data_if_needed():
    """Check if users exist, otherwise run seed script."""
    from app.modules.identity.models import User
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).limit(1))
            if res.scalar_one_or_none() is not None:
                logger.info("Database already contains records. Skipping seed.")
                return
    except Exception as e:
        logger.warning(f"Checking existing data failed: {e}")

    logger.info("Seeding database with canonical roles, users, master data, and agricultural assets...")
    try:
        from scripts.seed_dev_data import seed_all
        await seed_all()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        logger.error(f"Seeding database failed: {e}", exc_info=True)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing isolated AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_worker_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for standalone / worker tasks."""
    async with WorkerAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

get_db_context = get_worker_db_context
