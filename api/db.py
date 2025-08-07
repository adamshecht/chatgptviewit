"""
Database configuration and session management
"""

import os
import sys
from typing import AsyncGenerator
import asyncpg
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/cityscrape")
# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base for models
Base = declarative_base()

# Direct asyncpg connection pool for raw queries
pg_pool = None

async def init_db():
    """Initialize database connection pool"""
    global pg_pool
    try:
        # Use original DATABASE_URL for asyncpg (not the async version)
        original_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/cityscrape")
        pg_pool = await asyncpg.create_pool(
            original_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        print("✓ Database pool initialized successfully", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Database pool initialization failed: {e}", file=sys.stderr)
        pg_pool = None

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_pg_connection():
    """Get a raw asyncpg connection from the pool"""
    if not pg_pool:
        try:
            await init_db()
        except Exception as e:
            print(f"⚠️  Failed to initialize database pool: {e}", file=sys.stderr)
            raise HTTPException(
                status_code=500,
                detail="Database connection unavailable"
            )
    
    if not pg_pool:
        raise HTTPException(
            status_code=500,
            detail="Database connection unavailable"
        )
    
    async with pg_pool.acquire() as connection:
        yield connection

@asynccontextmanager
async def get_connection():
    """Context manager for raw asyncpg connections"""
    if not pg_pool:
        await init_db()
    async with pg_pool.acquire() as connection:
        yield connection