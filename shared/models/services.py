from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, String, Text, Index, UniqueConstraint, TIMESTAMP
# from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import ServiceType, BillingUnit
from .types import JSONType


class ServiceRegistry(Base):
    """Registry of available services and their configurations"""
    
    __tablename__ = "service_registry"
    
    # Service identification
    service_type: Mapped[ServiceType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of service"
    )
    
    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable service name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Service description"
    )
    
    # Configuration
    providers: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        comment="List of supported providers"
    )
    
    required_fields: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        comment="Required fields in event metadata"
    )
    
    optional_fields: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        comment="Optional fields in event metadata"
    )
    
    # Billing configuration
    billing_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        comment="Billing configuration"
    )
    
    # Aggregation rules
    aggregation_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        comment="Rules for aggregating metrics"
    )
    
    # Validation schema
    validation_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="JSON schema for validating events"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether service is active"
    )
    
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0",
        comment="Configuration version"
    )
    
    __table_args__ = (
        UniqueConstraint("service_type", name="uq_service_registry_type"),
        Index("ix_service_registry_active", "is_active"),
    )


class BillingRule(Base):
    """Billing rules for different services and providers"""
    
    __tablename__ = "billing_rules"
    
    # Service identification
    service_type: Mapped[ServiceType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Service type this rule applies to"
    )
    
    provider: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Service provider"
    )
    
    model_or_tier: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Specific model or pricing tier"
    )
    
    # Billing configuration
    billing_unit: Mapped[BillingUnit] = mapped_column(
        String(50),
        nullable=False,
        comment="Unit of billing (tokens, requests, etc.)"
    )
    
    rate_per_unit: Mapped[float] = mapped_column(
        nullable=False,
        comment="Cost per billing unit"
    )
    
    # Advanced pricing
    tiered_rates: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="Tiered pricing structure"
    )
    
    minimum_charge: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Minimum charge per event/request"
    )
    
    # Calculation rules
    calculation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="multiply",
        comment="How to calculate cost (multiply, sum, custom)"
    )
    
    calculation_expression: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Custom calculation expression"
    )
    
    # Validity period
    effective_from: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="When this rule becomes effective"
    )
    
    effective_until: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When this rule expires"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether rule is active"
    )
    
    __table_args__ = (
        Index("ix_billing_rules_service_provider", "service_type", "provider"),
        Index("ix_billing_rules_effective", "effective_from", "effective_until"),
        Index("ix_billing_rules_active", "is_active"),
    )


class Tenant(Base):
    """Tenant information for multi-tenancy"""
    
    __tablename__ = "tenants"
    
    # Tenant identification
    tenant_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique tenant identifier"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Tenant name"
    )
    
    # Contact information
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email"
    )
    
    # Configuration
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        comment="Tenant-specific settings"
    )
    
    # Limits and quotas
    rate_limits: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="Rate limits for this tenant"
    )
    
    usage_quotas: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="Usage quotas and limits"
    )
    
    # Billing
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Billing contact email"
    )
    
    billing_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
        comment="Billing configuration"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether tenant is active"
    )
    
    __table_args__ = (
        Index("ix_tenants_active", "is_active"),
    )