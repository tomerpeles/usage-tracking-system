import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import and_, desc, func, select, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from shared.models import (
    UsageEvent,
    UsageAggregate, 
    BillingSummary,
    ServiceRegistry,
    BillingRule,
    Tenant,
    AlertConfiguration,
    AlertInstance,
    ServiceType,
    EventStatus,
    AggregationPeriod,
)


class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session


class UsageEventRepository(BaseRepository):
    """Repository for usage events"""
    
    async def create_event(self, event_data: Dict[str, Any]) -> UsageEvent:
        """Create a new usage event"""
        event = UsageEvent(**event_data)
        self.session.add(event)
        await self.session.flush()
        return event
    
    async def create_events_batch(self, events_data: List[Dict[str, Any]]) -> List[UsageEvent]:
        """Create multiple usage events in a batch"""
        events = [UsageEvent(**data) for data in events_data]
        self.session.add_all(events)
        await self.session.flush()
        return events
    
    async def upsert_event(self, event_data: Dict[str, Any]) -> UsageEvent:
        """Upsert event (insert or update based on event_id)"""
        stmt = insert(UsageEvent).values(**event_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["event_id"],
            set_={
                "status": stmt.excluded.status,
                "billing_info": stmt.excluded.billing_info,
                "total_cost": stmt.excluded.total_cost,
                "error_message": stmt.excluded.error_message,
                "retry_count": stmt.excluded.retry_count,
                "updated_at": func.now(),
            }
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        
        # Fetch the upserted event
        event_id = event_data["event_id"]
        stmt = select(UsageEvent).where(UsageEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    async def get_event_by_id(self, event_id: uuid.UUID) -> Optional[UsageEvent]:
        """Get event by event_id"""
        stmt = select(UsageEvent).where(UsageEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_events_by_tenant(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        service_type: Optional[ServiceType] = None,
        user_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[UsageEvent], int]:
        """Get events by tenant with filters"""
        query = select(UsageEvent).where(UsageEvent.tenant_id == tenant_id)
        count_query = select(func.count()).select_from(UsageEvent).where(
            UsageEvent.tenant_id == tenant_id
        )
        
        # Apply filters
        conditions = []
        if start_date:
            conditions.append(UsageEvent.timestamp >= start_date)
        if end_date:
            conditions.append(UsageEvent.timestamp <= end_date)
        if service_type:
            conditions.append(UsageEvent.service_type == service_type)
        if user_id:
            conditions.append(UsageEvent.user_id == user_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar()
        
        # Get events with pagination
        query = query.order_by(desc(UsageEvent.timestamp)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        events = result.scalars().all()
        
        return list(events), total_count
    
    async def get_pending_events(self, limit: int = 100) -> List[UsageEvent]:
        """Get events that need processing"""
        stmt = (
            select(UsageEvent)
            .where(UsageEvent.status == EventStatus.PENDING)
            .order_by(UsageEvent.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_event_status(
        self,
        event_id: uuid.UUID,
        status: EventStatus,
        error_message: Optional[str] = None,
        billing_info: Optional[Dict[str, Any]] = None,
        total_cost: Optional[float] = None
    ) -> bool:
        """Update event processing status"""
        update_data = {"status": status, "updated_at": func.now()}
        
        if error_message is not None:
            update_data["error_message"] = error_message
        if billing_info is not None:
            update_data["billing_info"] = billing_info
        if total_cost is not None:
            update_data["total_cost"] = total_cost
        
        stmt = update(UsageEvent).where(UsageEvent.event_id == event_id).values(**update_data)
        result = await self.session.execute(stmt)
        return result.rowcount > 0


class UsageAggregateRepository(BaseRepository):
    """Repository for usage aggregates"""
    
    async def upsert_aggregate(self, aggregate_data: Dict[str, Any]) -> UsageAggregate:
        """Upsert usage aggregate"""
        stmt = insert(UsageAggregate).values(**aggregate_data)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_usage_aggregates_unique",
            set_={
                "event_count": stmt.excluded.event_count,
                "unique_users": stmt.excluded.unique_users,
                "total_cost": stmt.excluded.total_cost,
                "aggregated_metrics": stmt.excluded.aggregated_metrics,
                "avg_latency_ms": stmt.excluded.avg_latency_ms,
                "p95_latency_ms": stmt.excluded.p95_latency_ms,
                "error_count": stmt.excluded.error_count,
                "error_rate": stmt.excluded.error_rate,
                "updated_at": func.now(),
            }
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        
        # Fetch the upserted aggregate
        stmt = select(UsageAggregate).where(
            and_(
                UsageAggregate.tenant_id == aggregate_data["tenant_id"],
                UsageAggregate.period_start == aggregate_data["period_start"],
                UsageAggregate.period_type == aggregate_data["period_type"],
                UsageAggregate.service_type == aggregate_data.get("service_type"),
                UsageAggregate.service_provider == aggregate_data.get("service_provider"),
                UsageAggregate.user_id == aggregate_data.get("user_id"),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    async def get_aggregates(
        self,
        tenant_id: str,
        period_type: AggregationPeriod,
        start_date: datetime,
        end_date: datetime,
        service_type: Optional[ServiceType] = None,
        user_id: Optional[str] = None
    ) -> List[UsageAggregate]:
        """Get usage aggregates with filters"""
        query = select(UsageAggregate).where(
            and_(
                UsageAggregate.tenant_id == tenant_id,
                UsageAggregate.period_type == period_type,
                UsageAggregate.period_start >= start_date,
                UsageAggregate.period_end <= end_date,
            )
        )
        
        if service_type:
            query = query.where(UsageAggregate.service_type == service_type)
        if user_id:
            query = query.where(UsageAggregate.user_id == user_id)
        
        query = query.order_by(UsageAggregate.period_start)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ServiceRegistryRepository(BaseRepository):
    """Repository for service registry"""
    
    async def get_service_config(self, service_type: ServiceType) -> Optional[ServiceRegistry]:
        """Get service configuration"""
        stmt = select(ServiceRegistry).where(
            and_(
                ServiceRegistry.service_type == service_type,
                ServiceRegistry.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_active_services(self) -> List[ServiceRegistry]:
        """Get all active services"""
        stmt = select(ServiceRegistry).where(ServiceRegistry.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_or_update_service(self, service_data: Dict[str, Any]) -> ServiceRegistry:
        """Create or update service configuration"""
        service_type = service_data["service_type"]
        
        # Check if service exists
        existing = await self.get_service_config(service_type)
        if existing:
            # Update existing service
            for key, value in service_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = func.now()
            await self.session.flush()
            return existing
        else:
            # Create new service
            service = ServiceRegistry(**service_data)
            self.session.add(service)
            await self.session.flush()
            return service


class BillingRuleRepository(BaseRepository):
    """Repository for billing rules"""
    
    async def get_active_billing_rule(
        self,
        service_type: ServiceType,
        provider: str,
        model_or_tier: Optional[str] = None,
        effective_date: Optional[datetime] = None
    ) -> Optional[BillingRule]:
        """Get active billing rule for service/provider/model"""
        if effective_date is None:
            effective_date = datetime.utcnow()
        
        query = select(BillingRule).where(
            and_(
                BillingRule.service_type == service_type,
                BillingRule.provider == provider,
                BillingRule.is_active == True,
                BillingRule.effective_from <= effective_date,
                or_(
                    BillingRule.effective_until.is_(None),
                    BillingRule.effective_until > effective_date
                )
            )
        )
        
        if model_or_tier:
            query = query.where(BillingRule.model_or_tier == model_or_tier)
        
        # Order by specificity (model-specific rules first, then general)
        query = query.order_by(
            BillingRule.model_or_tier.desc().nullslast(),
            desc(BillingRule.effective_from)
        )
        
        result = await self.session.execute(query)
        return result.scalars().first()


class TenantRepository(BaseRepository):
    """Repository for tenant management"""
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        stmt = select(Tenant).where(Tenant.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants"""
        stmt = select(Tenant).where(Tenant.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        """Create new tenant"""
        tenant = Tenant(**tenant_data)
        self.session.add(tenant)
        await self.session.flush()
        return tenant


class AlertRepository(BaseRepository):
    """Repository for alert management"""
    
    async def get_active_alert_configs(self, tenant_id: str) -> List[AlertConfiguration]:
        """Get active alert configurations for tenant"""
        stmt = select(AlertConfiguration).where(
            and_(
                AlertConfiguration.tenant_id == tenant_id,
                AlertConfiguration.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_alert_instance(self, alert_data: Dict[str, Any]) -> AlertInstance:
        """Create new alert instance"""
        alert = AlertInstance(**alert_data)
        self.session.add(alert)
        await self.session.flush()
        return alert
    
    async def get_active_alerts(self, tenant_id: str) -> List[AlertInstance]:
        """Get active alert instances for tenant"""
        stmt = select(AlertInstance).where(
            and_(
                AlertInstance.tenant_id == tenant_id,
                AlertInstance.status.in_(["active", "acknowledged"])
            )
        ).order_by(desc(AlertInstance.triggered_at))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())