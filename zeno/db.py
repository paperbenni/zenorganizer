from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = "sqlite+aiosqlite:///./data/zeno.db"
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    # imported here to avoid circular imports
    from .models import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
