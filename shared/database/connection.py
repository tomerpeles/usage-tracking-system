import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine, 
    AsyncSession, 
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool

from config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager with async support"""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def create_engine(self) -> AsyncEngine:
        """Create async database engine with optimized settings"""
        if self._engine is None:
            self._engine = create_async_engine(
                settings.database.database_url,
                echo=settings.logging.level == "DEBUG",
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,  # 1 hour
                # Use NullPool for high-concurrency scenarios
                poolclass=NullPool,
                # Connection arguments for PostgreSQL
                connect_args={
                    "server_settings": {
                        "application_name": "usage_tracking_system",
                        "jit": "off",  # Disable JIT for faster connection setup
                    },
                    "command_timeout": 60,
                    "prepared_statement_cache_size": 0,  # Disable prepared statement cache
                }
            )
        return self._engine
    
    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Create session factory for database sessions"""
        if self._session_factory is None:
            engine = self.create_engine()
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=True
            )
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session with automatic cleanup"""
        session_factory = self.create_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
def get_session():
    """Get a database session - convenience function"""
    return db_manager.get_session()


def get_engine() -> AsyncEngine:
    """Get the database engine"""
    return db_manager.create_engine()


async def create_tables():
    """Create all database tables"""
    from shared.models import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        # Enable TimescaleDB extension if not exists
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Convert usage_events to hypertable for TimescaleDB
        try:
            await conn.execute("""
                SELECT create_hypertable(
                    'usage_events',
                    'timestamp',
                    chunk_time_interval => INTERVAL '1 month',
                    if_not_exists => TRUE
                );
            """)
            logger.info("Created TimescaleDB hypertable for usage_events")
        except Exception as e:
            logger.warning(f"Could not create hypertable (TimescaleDB may not be available): {e}")
        
        # Create retention policy for usage_events
        try:
            retention_days = settings.retention.event_retention_days
            await conn.execute(f"""
                SELECT add_retention_policy(
                    'usage_events',
                    INTERVAL '{retention_days} days',
                    if_not_exists => TRUE
                );
            """)
            logger.info(f"Created retention policy for usage_events ({retention_days} days)")
        except Exception as e:
            logger.warning(f"Could not create retention policy: {e}")


async def drop_tables():
    """Drop all database tables (for testing/development)"""
    from shared.models import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def health_check() -> bool:
    """Check database connectivity"""
    try:
        async with db_manager.get_session() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False