from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Создание async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии базы данных
    
    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Инициализация базы данных: создание всех таблиц
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
