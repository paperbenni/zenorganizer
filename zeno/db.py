from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import os

# Centralized database URL. Can be overridden via `DATABASE_URL` env var.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/zeno.db")

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)
