"""Database type compatibility layer for testing"""

import uuid
from typing import Any

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.types import CHAR


class DatabaseTypeAdapter:
    """Adapter for database-specific types"""
    
    @staticmethod
    def get_uuid_type():
        """Get UUID type compatible with current database"""
        return postgresql.UUID(as_uuid=True).with_variant(
            CHAR(36), "sqlite"
        )
    
    @staticmethod
    def get_json_type():
        """Get JSON type compatible with current database"""
        return postgresql.JSONB().with_variant(
            Text(), "sqlite"
        )


class UUIDType(TypeDecorator):
    """UUID type that works with both PostgreSQL and SQLite"""
    
    impl = CHAR
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL and SQLite"""
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.JSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            import json
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value