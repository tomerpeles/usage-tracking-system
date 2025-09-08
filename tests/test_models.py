"""Test database models"""

import pytest
import uuid
from datetime import datetime

from shared.models import (
    UsageEvent, UsageAggregate, BillingSummary,
    ServiceRegistry, BillingRule, Tenant,
    AlertConfiguration, AlertInstance
)
from shared.models.enums import ServiceType, EventStatus, AggregationPeriod, BillingUnit


class TestUsageEvent:
    """Test UsageEvent model"""
    
    @pytest.mark.asyncio
    async def test_create_usage_event(self, test_session, sample_llm_event):
        """Test creating a usage event"""
        
        # Create event
        event = UsageEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            **sample_llm_event
        )
        
        test_session.add(event)
        await test_session.commit()
        
        # Verify event was created
        assert event.id is not None
        assert event.event_id is not None
        assert event.tenant_id == "test-tenant"
        assert event.user_id == "test-user"
        assert event.service_type == ServiceType.LLM_SERVICE
        assert event.status == EventStatus.PENDING  # Default status
    
    @pytest.mark.asyncio
    async def test_usage_event_metrics(self, test_session, sample_llm_event):
        """Test usage event metrics storage"""
        
        event = UsageEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            **sample_llm_event
        )
        
        test_session.add(event)
        await test_session.commit()
        
        # Verify metrics are stored correctly
        assert event.metrics["input_tokens"] == 100
        assert event.metrics["output_tokens"] == 50
        assert event.metrics["total_tokens"] == 150
        assert event.metrics["latency_ms"] == 1500
    
    @pytest.mark.asyncio
    async def test_usage_event_tags(self, test_session, sample_llm_event):
        """Test usage event tags"""
        
        event = UsageEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            **sample_llm_event
        )
        
        test_session.add(event)
        await test_session.commit()
        
        # Verify tags
        assert "test" in event.tags
        assert "unit-test" in event.tags
        assert len(event.tags) == 2


class TestServiceRegistry:
    """Test ServiceRegistry model"""
    
    @pytest.mark.asyncio
    async def test_create_service_registry(self, test_session):
        """Test creating a service registry entry"""
        
        service = ServiceRegistry(
            service_type=ServiceType.LLM_SERVICE,
            service_name="LLM Service",
            description="Large Language Model service",
            providers=["openai", "anthropic"],
            required_fields=["model", "tokens"],
            optional_fields=["temperature", "max_tokens"],
            billing_config={
                "unit": "tokens",
                "calculation_method": "multiply"
            },
            aggregation_rules={
                "metrics_to_sum": ["input_tokens", "output_tokens"]
            }
        )
        
        test_session.add(service)
        await test_session.commit()
        
        # Verify service was created
        assert service.id is not None
        assert service.service_type == ServiceType.LLM_SERVICE
        assert service.is_active is True  # Default
        assert "openai" in service.providers
        assert "anthropic" in service.providers


class TestBillingRule:
    """Test BillingRule model"""
    
    @pytest.mark.asyncio
    async def test_create_billing_rule(self, test_session):
        """Test creating a billing rule"""
        
        rule = BillingRule(
            service_type=ServiceType.LLM_SERVICE,
            provider="openai",
            model_or_tier="gpt-4",
            billing_unit=BillingUnit.TOKENS,
            rate_per_unit=0.00003,
            calculation_method="multiply",
            effective_from=datetime.utcnow(),
            is_active=True
        )
        
        test_session.add(rule)
        await test_session.commit()
        
        # Verify rule was created
        assert rule.id is not None
        assert rule.service_type == ServiceType.LLM_SERVICE
        assert rule.provider == "openai"
        assert rule.billing_unit == BillingUnit.TOKENS
        assert rule.rate_per_unit == 0.00003


class TestTenant:
    """Test Tenant model"""
    
    @pytest.mark.asyncio
    async def test_create_tenant(self, test_session):
        """Test creating a tenant"""
        
        tenant = Tenant(
            tenant_id="test-tenant-123",
            name="Test Tenant",
            contact_email="test@example.com",
            settings={"timezone": "UTC", "currency": "USD"},
            is_active=True
        )
        
        test_session.add(tenant)
        await test_session.commit()
        
        # Verify tenant was created
        assert tenant.id is not None
        assert tenant.tenant_id == "test-tenant-123"
        assert tenant.name == "Test Tenant"
        assert tenant.settings["timezone"] == "UTC"


class TestUsageAggregate:
    """Test UsageAggregate model"""
    
    @pytest.mark.asyncio
    async def test_create_usage_aggregate(self, test_session):
        """Test creating a usage aggregate"""
        
        now = datetime.utcnow()
        
        aggregate = UsageAggregate(
            tenant_id="test-tenant",
            period_start=now,
            period_end=now,
            period_type=AggregationPeriod.HOUR,
            service_type=ServiceType.LLM_SERVICE,
            service_provider="openai",
            event_count=100,
            unique_users=5,
            total_cost=1.50,
            aggregated_metrics={
                "total_tokens": 15000,
                "avg_tokens": 150
            },
            error_count=2,
            error_rate=0.02
        )
        
        test_session.add(aggregate)
        await test_session.commit()
        
        # Verify aggregate was created
        assert aggregate.id is not None
        assert aggregate.tenant_id == "test-tenant"
        assert aggregate.event_count == 100
        assert aggregate.unique_users == 5
        assert aggregate.total_cost == 1.50
        assert aggregate.aggregated_metrics["total_tokens"] == 15000


class TestBillingSummary:
    """Test BillingSummary model"""
    
    @pytest.mark.asyncio
    async def test_create_billing_summary(self, test_session):
        """Test creating a billing summary"""
        
        summary = BillingSummary(
            tenant_id="test-tenant",
            billing_year=2024,
            billing_month=1,
            total_cost=150.00,
            cost_by_service={
                "llm_service": 100.00,
                "document_processor": 50.00
            },
            cost_by_user={
                "user1": 75.00,
                "user2": 75.00
            },
            total_events=1000,
            active_users=10,
            is_finalized=False
        )
        
        test_session.add(summary)
        await test_session.commit()
        
        # Verify summary was created
        assert summary.id is not None
        assert summary.tenant_id == "test-tenant"
        assert summary.billing_year == 2024
        assert summary.billing_month == 1
        assert summary.total_cost == 150.00
        assert summary.cost_by_service["llm_service"] == 100.00