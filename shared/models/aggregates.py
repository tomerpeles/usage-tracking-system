from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DECIMAL, Integer, String, TIMESTAMP, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin
from .enums import ServiceType, AggregationPeriod


class UsageAggregate(Base, TenantMixin):
    """Pre-calculated usage aggregations for fast querying"""
    
    __tablename__ = "usage_aggregates"
    
    # Time dimension
    period_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        comment="Start of the aggregation period"
    )
    
    period_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        comment="End of the aggregation period"
    )
    
    period_type: Mapped[AggregationPeriod] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Type of aggregation period (hour, day, month)"
    )
    
    # Service dimensions
    service_type: Mapped[Optional[ServiceType]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Service type (null for all services)"
    )
    
    service_provider: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Service provider (null for all providers)"
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User ID (null for all users)"
    )
    
    # Aggregated metrics
    event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of events"
    )
    
    unique_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of unique users"
    )
    
    total_cost: Mapped[Optional[float]] = mapped_column(
        DECIMAL(12, 6),
        nullable=True,
        comment="Total cost for the period"
    )
    
    # Service-specific metrics (stored as JSONB for flexibility)
    aggregated_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Service-specific aggregated metrics"
    )
    
    # Statistical metrics
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True,
        comment="Average latency in milliseconds"
    )
    
    p95_latency_ms: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True,
        comment="95th percentile latency in milliseconds"
    )
    
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of failed events"
    )
    
    error_rate: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
        comment="Error rate (0.0 to 1.0)"
    )
    
    __table_args__ = (
        # Unique constraint to prevent duplicate aggregates
        UniqueConstraint(
            "tenant_id",
            "period_start", 
            "period_type",
            "service_type",
            "service_provider",
            "user_id",
            name="uq_usage_aggregates_unique"
        ),
        
        # Composite indexes for common queries
        Index("ix_usage_agg_tenant_period", "tenant_id", "period_start", "period_type"),
        Index("ix_usage_agg_service_period", "service_type", "period_start", "period_type"),
        Index("ix_usage_agg_user_period", "user_id", "period_start", "period_type"),
        
        # GIN index for aggregated metrics
        Index("ix_usage_agg_metrics_gin", "aggregated_metrics", postgresql_using="gin"),
    )


class BillingSummary(Base, TenantMixin):
    """Monthly billing summaries for invoicing"""
    
    __tablename__ = "billing_summaries"
    
    # Billing period
    billing_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Billing month (1-12)"
    )
    
    billing_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Billing year"
    )
    
    # Cost breakdown
    total_cost: Mapped[float] = mapped_column(
        DECIMAL(12, 2),
        nullable=False,
        comment="Total cost for the billing period"
    )
    
    cost_by_service: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Cost breakdown by service type"
    )
    
    cost_by_user: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Cost breakdown by user"
    )
    
    # Usage statistics
    total_events: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total events in billing period"
    )
    
    active_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of active users"
    )
    
    # Billing status
    is_finalized: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Whether billing is finalized"
    )
    
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When billing was finalized"
    )
    
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", 
            "billing_year", 
            "billing_month",
            name="uq_billing_summary_unique"
        ),
        Index("ix_billing_summary_period", "billing_year", "billing_month"),
    )