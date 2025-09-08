from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DECIMAL, Integer, String, TIMESTAMP, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin
from .enums import AlertType, AlertStatus


class AlertConfiguration(Base, TenantMixin):
    """Alert configuration for monitoring thresholds"""
    
    __tablename__ = "alert_configurations"
    
    # Alert identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable alert name"
    )
    
    alert_type: Mapped[AlertType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of alert"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Alert description"
    )
    
    # Target criteria
    service_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Service type to monitor (null for all)"
    )
    
    service_provider: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Service provider to monitor (null for all)"
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Specific user to monitor (null for all)"
    )
    
    # Threshold configuration
    threshold_value: Mapped[float] = mapped_column(
        DECIMAL(12, 6),
        nullable=False,
        comment="Threshold value that triggers the alert"
    )
    
    threshold_operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=">=",
        comment="Comparison operator (>=, <=, ==, etc.)"
    )
    
    # Time window
    time_window_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Time window for evaluation in minutes"
    )
    
    # Evaluation settings
    evaluation_frequency_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="How often to evaluate the alert in minutes"
    )
    
    minimum_data_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Minimum data points needed to trigger alert"
    )
    
    # Notification settings
    notification_channels: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="List of notification channels (email, webhook, etc.)"
    )
    
    notification_settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Channel-specific notification settings"
    )
    
    # Cooldown to prevent spam
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Cooldown period between notifications"
    )
    
    # Status and metadata
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether alert is active"
    )
    
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional alert metadata"
    )
    
    __table_args__ = (
        Index("ix_alert_config_tenant_type", "tenant_id", "alert_type"),
        Index("ix_alert_config_service", "service_type", "service_provider"),
        Index("ix_alert_config_active", "is_active"),
    )


class AlertInstance(Base, TenantMixin):
    """Instances of fired alerts"""
    
    __tablename__ = "alert_instances"
    
    # Alert reference
    alert_config_id: Mapped[str] = mapped_column(
        String(36),  # UUID as string
        nullable=False,
        index=True,
        comment="Reference to alert configuration"
    )
    
    # Alert details
    alert_type: Mapped[AlertType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of alert that fired"
    )
    
    status: Mapped[AlertStatus] = mapped_column(
        String(20),
        nullable=False,
        default=AlertStatus.ACTIVE,
        index=True,
        comment="Current alert status"
    )
    
    # Trigger information
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        comment="When the alert was triggered"
    )
    
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the alert was resolved"
    )
    
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the alert was acknowledged"
    )
    
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Who acknowledged the alert"
    )
    
    # Alert values
    current_value: Mapped[float] = mapped_column(
        DECIMAL(12, 6),
        nullable=False,
        comment="Value that triggered the alert"
    )
    
    threshold_value: Mapped[float] = mapped_column(
        DECIMAL(12, 6),
        nullable=False,
        comment="Threshold value that was exceeded"
    )
    
    # Context information
    service_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Service type involved"
    )
    
    service_provider: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Service provider involved"
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User involved (if applicable)"
    )
    
    # Additional context
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional context about the alert"
    )
    
    # Notification tracking
    notifications_sent: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="List of notification channels that were notified"
    )
    
    last_notification_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When last notification was sent"
    )
    
    notification_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of notifications sent"
    )
    
    # Resolution details
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about alert resolution"
    )
    
    auto_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether alert was auto-resolved"
    )
    
    __table_args__ = (
        Index("ix_alert_instance_config", "alert_config_id"),
        Index("ix_alert_instance_triggered", "triggered_at"),
        Index("ix_alert_instance_status", "status"),
        Index("ix_alert_instance_tenant_status", "tenant_id", "status"),
        Index("ix_alert_instance_service", "service_type", "service_provider"),
    )