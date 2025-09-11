"""Test configuration and fixtures"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shared.models import Base
from shared.database import db_manager
from config import settings


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
def sample_llm_event():
    """Sample LLM event data for testing"""
    from shared.models.enums import ServiceType
    
    return {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "service_type": ServiceType.LLM_SERVICE,
        "service_provider": "openai",
        "event_type": "completion",
        "metadata_": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "metrics": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "latency_ms": 1500
        },
        "tags": ["test", "unit-test"],
        "session_id": "test-session",
        "request_id": "test-request"
    }


@pytest.fixture
def sample_document_event():
    """Sample document processing event for testing"""
    return {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "service_type": "document_processor",
        "service_provider": "document_ai",
        "event_type": "processing",
        "metadata_": {
            "document_type": "invoice",
            "processing_type": "data_extraction",
            "file_format": "pdf"
        },
        "metrics": {
            "pages_processed": 5,
            "characters_extracted": 10000,
            "processing_time_ms": 3000,
            "file_size_bytes": 2048000
        },
        "tags": ["test", "document"],
        "session_id": "test-session"
    }


@pytest.fixture
def sample_api_event():
    """Sample API event for testing"""
    return {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "service_type": "api_service",
        "service_provider": "payment_api",
        "event_type": "request",
        "metadata_": {
            "endpoint": "/api/v1/payments",
            "method": "POST",
            "api_version": "v1",
            "status_code": 201
        },
        "metrics": {
            "request_count": 1,
            "response_time_ms": 250,
            "payload_size_bytes": 1024,
            "response_size_bytes": 512
        },
        "tags": ["test", "api"]
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.lists = {}
        
        async def ping(self):
            return True
        
        async def get(self, key):
            return self.data.get(key)
        
        async def set(self, key, value):
            self.data[key] = value
        
        async def setex(self, key, ttl, value):
            self.data[key] = value  # Ignore TTL for testing
        
        async def lpush(self, key, *values):
            if key not in self.lists:
                self.lists[key] = []
            for value in values:
                self.lists[key].insert(0, value)
            return len(self.lists[key])
        
        async def rpop(self, key):
            if key in self.lists and self.lists[key]:
                return self.lists[key].pop()
            return None
        
        async def brpop(self, keys, timeout=0):
            for key in keys:
                if key in self.lists and self.lists[key]:
                    value = self.lists[key].pop()
                    return (key, value)
            return None
        
        async def close(self):
            pass
    
    return MockRedis()