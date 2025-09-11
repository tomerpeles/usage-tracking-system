from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import DECIMAL, Integer, String, TIMESTAMP, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, MetadataMixin
from .enums import ServiceType, EventStatus
from .types import UUIDType, JSONType


class UsageEvent(Base, TenantMixin, MetadataMixin):
    """Main usage events table - partitioned by month for TimescaleDB"""
    
    __tablename__ = "usage_events"
    
    # Core event fields
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        unique=True,
        nullable=False,
        index=True,
        comment="Unique event identifier for deduplication"
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        comment="Event timestamp"
    )
    
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User who triggered the event"
    )
    
    # Service information
    service_type: Mapped[ServiceType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of service (llm, document_processor, etc.)"
    )
    
    service_provider: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Service provider (openai, anthropic, etc.)"
    )
    
    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Specific event type within the service"
    )
    
    # Quantifiable measurements
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        default=dict,
        comment="Quantifiable measurements (tokens, pages, etc.)"
    )
    
    # Billing information
    billing_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        default=dict,
        comment="Billing calculations and cost information"
    )
    
    # Processing status
    status: Mapped[EventStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EventStatus.PENDING,
        index=True,
        comment="Event processing status"
    )
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Error message if processing failed"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )
    
    # Calculated costs
    total_cost: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 6),
        nullable=True,
        comment="Total calculated cost for this event"
    )
    
    # Session tracking
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Session identifier for grouping related events"
    )
    
    # Request tracking
    request_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Request identifier for tracing"
    )
    
    __table_args__ = (
        # Composite indexes for common query patterns
        Index("ix_usage_events_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_usage_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_usage_events_service_timestamp", "service_type", "timestamp"),
        Index("ix_usage_events_provider_timestamp", "service_provider", "timestamp"),
        Index("ix_usage_events_tenant_service", "tenant_id", "service_type"),
        Index("ix_usage_events_tenant_user", "tenant_id", "user_id"),
        
        # GIN indexes for JSONB columns
        Index("ix_usage_events_metadata_gin", "metadata", postgresql_using="gin"),
        Index("ix_usage_events_metrics_gin", "metrics", postgresql_using="gin"),
        Index("ix_usage_events_billing_gin", "billing_info", postgresql_using="gin"),
        Index("ix_usage_events_tags_gin", "tags", postgresql_using="gin"),
        
        # Partial indexes for performance
        Index("ix_usage_events_pending", "status", postgresql_where=f"status = '{EventStatus.PENDING}'"),
        Index("ix_usage_events_failed", "status", postgresql_where=f"status = '{EventStatus.FAILED}'"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<UsageEvent("
            f"event_id={self.event_id}, "
            f"tenant_id={self.tenant_id}, "
            f"service_type={self.service_type}, "
            f"timestamp={self.timestamp}"
            f")>"
        )