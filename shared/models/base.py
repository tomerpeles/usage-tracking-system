import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import TIMESTAMP, String, Text, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .types import UUIDType, JSONType


class Base(DeclarativeBase):
    """Base class for all database models"""
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class TimestampMixin:
    """Mixin for models that need timestamp fields"""
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class TenantMixin:
    """Mixin for models that belong to a tenant"""
    
    tenant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )


class MetadataMixin:
    """Mixin for models that store flexible metadata"""
    
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONType,
        nullable=True,
        default=dict
    )
    
    tags: Mapped[Optional[list[str]]] = mapped_column(
        JSONType,
        nullable=True,
        default=list
    )