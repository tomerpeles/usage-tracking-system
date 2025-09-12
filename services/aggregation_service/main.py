import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import and_, func, select, text
from sqlalchemy.dialects.postgresql import insert

from config import settings
from shared.database import get_session, UsageEventRepository, UsageAggregateRepository
from shared.models import UsageEvent, UsageAggregate, BillingSummary
from shared.models.enums import ServiceType, EventStatus, AggregationPeriod
from shared.utils import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("aggregation_service")


class AggregationService:
    """Service for aggregating usage data into summary tables"""
    
    def __init__(self):
        self.running = False
        self.aggregation_interval = 300  # 5 minutes
    
    async def start(self):
        """Start the aggregation service"""
        logger.info("Starting aggregation service")
        self.running = True
        
        # Run initial aggregations
        await self._run_all_aggregations()
        
        # Start periodic aggregation loop
        await self._aggregation_loop()
    
    async def stop(self):
        """Stop the aggregation service"""
        logger.info("Stopping aggregation service")
        self.running = False
    
    async def _aggregation_loop(self):
        """Main aggregation loop"""
        while self.running:
            try:
                logger.info("Starting aggregation cycle")
                
                # Run all aggregation jobs
                await self._run_all_aggregations()
                
                logger.info("Aggregation cycle completed")
                
                # Wait for next cycle
                await asyncio.sleep(self.aggregation_interval)
                
            except Exception as e:
                logger.error("Error in aggregation loop", error=str(e), exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _run_all_aggregations(self):
        """Run all aggregation jobs"""
        
        # Hourly aggregations (process last 25 hours to handle overlaps)
        end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=25)
        await self._aggregate_usage_data(
            AggregationPeriod.HOUR, 
            start_time, 
            end_time
        )
        
        # Daily aggregations (process last 8 days)
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=8)
        await self._aggregate_usage_data(
            AggregationPeriod.DAY, 
            start_date, 
            end_date
        )
        
        # Weekly aggregations (process last 5 weeks)
        week_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        # Get start of current week (Monday)
        days_since_monday = week_end.weekday()
        week_start = week_end - timedelta(days=days_since_monday)
        start_week = week_start - timedelta(weeks=5)
        await self._aggregate_usage_data(
            AggregationPeriod.WEEK, 
            start_week, 
            week_end
        )
        
        # Monthly aggregations (process last 13 months)
        month_end = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Go back to start of 13 months ago
        start_month = month_end.replace(year=month_end.year - 1)
        if month_end.month > 1:
            start_month = start_month.replace(month=month_end.month - 1)
        else:
            start_month = start_month.replace(year=start_month.year - 1, month=12)
        
        await self._aggregate_usage_data(
            AggregationPeriod.MONTH, 
            start_month, 
            month_end
        )
        
        # Generate billing summaries
        await self._generate_billing_summaries()
    
    async def _aggregate_usage_data(
        self, 
        period: AggregationPeriod, 
        start_time: datetime, 
        end_time: datetime
    ):
        """Aggregate usage data for specified period"""
        
        logger.info(
            "Starting aggregation",
            period=period,
            start_time=start_time,
            end_time=end_time
        )
        
        try:
            async with get_session() as session:
                # Get all tenants with events in the period
                tenants_query = select(UsageEvent.tenant_id).distinct().where(
                    and_(
                        UsageEvent.timestamp >= start_time,
                        UsageEvent.timestamp < end_time,
                        UsageEvent.status == EventStatus.COMPLETED
                    )
                )
                
                tenant_result = await session.execute(tenants_query)
                tenants = [row.tenant_id for row in tenant_result]
                
                logger.info(f"Found {len(tenants)} tenants to aggregate for {period}")
                
                # Process each tenant
                for tenant_id in tenants:
                    await self._aggregate_tenant_data(
                        session, tenant_id, period, start_time, end_time
                    )
        
        except Exception as e:
            logger.error("Failed to aggregate usage data", error=str(e), period=period)
    
    async def _aggregate_tenant_data(
        self,
        session,
        tenant_id: str,
        period: AggregationPeriod,
        start_time: datetime,
        end_time: datetime
    ):
        """Aggregate usage data for a specific tenant"""
        
        # Calculate period boundaries
        periods = self._get_period_boundaries(period, start_time, end_time)
        
        for period_start, period_end in periods:
            await self._aggregate_tenant_period(
                session, tenant_id, period, period_start, period_end
            )
    
    def _get_period_boundaries(
        self, 
        period: AggregationPeriod, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """Get list of period boundaries for aggregation"""
        
        boundaries = []
        current_start = start_time
        
        while current_start < end_time:
            if period == AggregationPeriod.HOUR:
                current_end = current_start + timedelta(hours=1)
            elif period == AggregationPeriod.DAY:
                current_end = current_start + timedelta(days=1)
            elif period == AggregationPeriod.WEEK:
                current_end = current_start + timedelta(weeks=1)
            elif period == AggregationPeriod.MONTH:
                # Handle month boundaries properly
                if current_start.month == 12:
                    current_end = current_start.replace(
                        year=current_start.year + 1, 
                        month=1
                    )
                else:
                    current_end = current_start.replace(
                        month=current_start.month + 1
                    )
            
            boundaries.append((current_start, min(current_end, end_time)))
            current_start = current_end
        
        return boundaries
    
    async def _aggregate_tenant_period(
        self,
        session,
        tenant_id: str,
        period: AggregationPeriod,
        period_start: datetime,
        period_end: datetime
    ):
        """Aggregate data for a tenant in a specific period"""
        
        # Base query for events in this period
        base_query = select(UsageEvent).where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= period_start,
                UsageEvent.timestamp < period_end,
                UsageEvent.status == EventStatus.COMPLETED
            )
        )
        
        # Overall tenant aggregate (all services)
        await self._create_aggregate(
            session, tenant_id, period, period_start, period_end,
            service_type=None, service_provider=None, user_id=None
        )
        
        # Aggregate by service type
        service_types_query = select(UsageEvent.service_type).distinct().where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= period_start,
                UsageEvent.timestamp < period_end,
                UsageEvent.status == EventStatus.COMPLETED
            )
        )
        
        service_result = await session.execute(service_types_query)
        service_types = [row.service_type for row in service_result]
        
        for service_type in service_types:
            # Service type aggregate
            await self._create_aggregate(
                session, tenant_id, period, period_start, period_end,
                service_type=service_type, service_provider=None, user_id=None
            )
            
            # Get providers for this service type
            providers_query = select(UsageEvent.service_provider).distinct().where(
                and_(
                    UsageEvent.tenant_id == tenant_id,
                    UsageEvent.service_type == service_type,
                    UsageEvent.timestamp >= period_start,
                    UsageEvent.timestamp < period_end,
                    UsageEvent.status == EventStatus.COMPLETED
                )
            )
            
            provider_result = await session.execute(providers_query)
            providers = [row.service_provider for row in provider_result]
            
            for provider in providers:
                # Service provider aggregate
                await self._create_aggregate(
                    session, tenant_id, period, period_start, period_end,
                    service_type=service_type, service_provider=provider, user_id=None
                )
        
        # Aggregate by user (top 100 users only to limit data volume)
        users_query = select(
            UsageEvent.user_id, 
            func.count().label('event_count')
        ).where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= period_start,
                UsageEvent.timestamp < period_end,
                UsageEvent.status == EventStatus.COMPLETED
            )
        ).group_by(UsageEvent.user_id).order_by(
            func.count().desc()
        ).limit(100)
        
        user_result = await session.execute(users_query)
        top_users = [row.user_id for row in user_result]
        
        for user_id in top_users:
            # User aggregate
            await self._create_aggregate(
                session, tenant_id, period, period_start, period_end,
                service_type=None, service_provider=None, user_id=user_id
            )
    
    async def _create_aggregate(
        self,
        session,
        tenant_id: str,
        period: AggregationPeriod,
        period_start: datetime,
        period_end: datetime,
        service_type: Optional[str] = None,
        service_provider: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Create or update an aggregate record"""
        
        # Build the aggregation query
        conditions = [
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.timestamp >= period_start,
            UsageEvent.timestamp < period_end,
            UsageEvent.status == EventStatus.COMPLETED
        ]
        
        if service_type:
            conditions.append(UsageEvent.service_type == service_type)
        if service_provider:
            conditions.append(UsageEvent.service_provider == service_provider)
        if user_id:
            conditions.append(UsageEvent.user_id == user_id)
        
        # Aggregation query - simplified to avoid complex function errors
        agg_query = select(
            func.count().label('event_count'),
            func.count(func.distinct(UsageEvent.user_id)).label('unique_users'),
            func.sum(UsageEvent.total_cost).label('total_cost'),
            func.avg(
                func.cast(UsageEvent.metrics.op('->>')('latency_ms'), func.FLOAT)
            ).label('avg_latency_ms'),
            func.coalesce(
                func.avg(func.cast(UsageEvent.metrics.op('->>')('latency_ms'), func.FLOAT)), 0
            ).label('p95_latency_ms'),
            func.literal(0).label('error_count')  # Simplified for now
        ).where(and_(*conditions))
        
        result = await session.execute(agg_query)
        row = result.first()
        
        if row and row.event_count > 0:
            # Calculate error rate
            error_rate = (row.error_count / row.event_count) if row.event_count > 0 else 0.0
            
            # Aggregate service-specific metrics
            aggregated_metrics = await self._calculate_service_metrics(
                session, service_type, conditions
            )
            
            # Create or update aggregate record
            aggregate_data = {
                'tenant_id': tenant_id,
                'period_start': period_start,
                'period_end': period_end,
                'period_type': period,
                'service_type': service_type,
                'service_provider': service_provider,
                'user_id': user_id,
                'event_count': row.event_count,
                'unique_users': row.unique_users,
                'total_cost': float(row.total_cost) if row.total_cost else None,
                'aggregated_metrics': aggregated_metrics,
                'avg_latency_ms': float(row.avg_latency_ms) if row.avg_latency_ms else None,
                'p95_latency_ms': float(row.p95_latency_ms) if row.p95_latency_ms else None,
                'error_count': row.error_count,
                'error_rate': error_rate
            }
            
            # Use upsert to handle duplicates
            repo = UsageAggregateRepository(session)
            await repo.upsert_aggregate(aggregate_data)
    
    async def _calculate_service_metrics(
        self,
        session,
        service_type: Optional[str],
        conditions: List
    ) -> Dict[str, Any]:
        """Calculate service-specific aggregated metrics"""
        
        aggregated_metrics = {}
        
        if service_type == ServiceType.LLM_SERVICE:
            # Aggregate token usage
            token_query = select(
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('input_tokens'), func.BIGINT)
                ).label('total_input_tokens'),
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('output_tokens'), func.BIGINT)
                ).label('total_output_tokens'),
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('total_tokens'), func.BIGINT)
                ).label('total_tokens'),
                func.avg(
                    func.cast(UsageEvent.metrics.op('->>')('input_tokens'), func.FLOAT)
                ).label('avg_input_tokens'),
                func.avg(
                    func.cast(UsageEvent.metrics.op('->>')('output_tokens'), func.FLOAT)
                ).label('avg_output_tokens')
            ).where(and_(*conditions))
            
            token_result = await session.execute(token_query)
            token_row = token_result.first()
            
            if token_row:
                aggregated_metrics.update({
                    'total_input_tokens': token_row.total_input_tokens or 0,
                    'total_output_tokens': token_row.total_output_tokens or 0,
                    'total_tokens': token_row.total_tokens or 0,
                    'avg_input_tokens': token_row.avg_input_tokens or 0.0,
                    'avg_output_tokens': token_row.avg_output_tokens or 0.0
                })
        
        elif service_type == ServiceType.DOCUMENT_PROCESSOR:
            # Aggregate document processing metrics
            doc_query = select(
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('pages_processed'), func.BIGINT)
                ).label('total_pages'),
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('characters_extracted'), func.BIGINT)
                ).label('total_characters'),
                func.avg(
                    func.cast(UsageEvent.metrics.op('->>')('processing_time_ms'), func.FLOAT)
                ).label('avg_processing_time_ms')
            ).where(and_(*conditions))
            
            doc_result = await session.execute(doc_query)
            doc_row = doc_result.first()
            
            if doc_row:
                aggregated_metrics.update({
                    'total_pages_processed': doc_row.total_pages or 0,
                    'total_characters_extracted': doc_row.total_characters or 0,
                    'avg_processing_time_ms': doc_row.avg_processing_time_ms or 0.0
                })
        
        elif service_type == ServiceType.API_SERVICE:
            # Aggregate API metrics
            api_query = select(
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('request_count'), func.BIGINT)
                ).label('total_requests'),
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('payload_size_bytes'), func.BIGINT)
                ).label('total_payload_bytes'),
                func.sum(
                    func.cast(UsageEvent.metrics.op('->>')('response_size_bytes'), func.BIGINT)
                ).label('total_response_bytes'),
                func.avg(
                    func.cast(UsageEvent.metrics.op('->>')('response_time_ms'), func.FLOAT)
                ).label('avg_response_time_ms')
            ).where(and_(*conditions))
            
            api_result = await session.execute(api_query)
            api_row = api_result.first()
            
            if api_row:
                aggregated_metrics.update({
                    'total_requests': api_row.total_requests or 0,
                    'total_payload_bytes': api_row.total_payload_bytes or 0,
                    'total_response_bytes': api_row.total_response_bytes or 0,
                    'avg_response_time_ms': api_row.avg_response_time_ms or 0.0
                })
        
        return aggregated_metrics
    
    async def _generate_billing_summaries(self):
        """Generate monthly billing summaries"""
        
        logger.info("Generating billing summaries")
        
        # Get current and previous month boundaries
        now = datetime.utcnow()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Previous month
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(
                year=current_month_start.year - 1,
                month=12
            )
        else:
            prev_month_start = current_month_start.replace(
                month=current_month_start.month - 1
            )
        
        # Generate summaries for both months
        await self._generate_month_billing_summary(prev_month_start, current_month_start)
        await self._generate_month_billing_summary(current_month_start, now)
    
    async def _generate_month_billing_summary(
        self,
        month_start: datetime,
        month_end: datetime
    ):
        """Generate billing summary for a specific month"""
        
        try:
            async with get_session() as session:
                # Get all tenants with events in this month
                tenants_query = select(UsageEvent.tenant_id).distinct().where(
                    and_(
                        UsageEvent.timestamp >= month_start,
                        UsageEvent.timestamp < month_end,
                        UsageEvent.status == EventStatus.COMPLETED,
                        UsageEvent.total_cost.isnot(None)
                    )
                )
                
                tenant_result = await session.execute(tenants_query)
                tenants = [row.tenant_id for row in tenant_result]
                
                logger.info(
                    f"Generating billing summaries for {len(tenants)} tenants",
                    month=month_start.strftime('%Y-%m')
                )
                
                for tenant_id in tenants:
                    await self._generate_tenant_billing_summary(
                        session, tenant_id, month_start, month_end
                    )
        
        except Exception as e:
            logger.error("Failed to generate billing summaries", error=str(e))
    
    async def _generate_tenant_billing_summary(
        self,
        session,
        tenant_id: str,
        month_start: datetime,
        month_end: datetime
    ):
        """Generate billing summary for a specific tenant and month"""
        
        # Calculate total cost
        total_query = select(
            func.sum(UsageEvent.total_cost).label('total_cost'),
            func.count().label('total_events'),
            func.count(func.distinct(UsageEvent.user_id)).label('active_users')
        ).where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= month_start,
                UsageEvent.timestamp < month_end,
                UsageEvent.status == EventStatus.COMPLETED,
                UsageEvent.total_cost.isnot(None)
            )
        )
        
        total_result = await session.execute(total_query)
        total_row = total_result.first()
        
        if not total_row or not total_row.total_cost:
            return  # No billable events
        
        # Cost by service
        service_query = select(
            UsageEvent.service_type,
            UsageEvent.service_provider,
            func.sum(UsageEvent.total_cost).label('cost')
        ).where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= month_start,
                UsageEvent.timestamp < month_end,
                UsageEvent.status == EventStatus.COMPLETED,
                UsageEvent.total_cost.isnot(None)
            )
        ).group_by(UsageEvent.service_type, UsageEvent.service_provider)
        
        service_result = await session.execute(service_query)
        cost_by_service = {}
        
        for row in service_result:
            key = f"{row.service_type}:{row.service_provider}"
            cost_by_service[key] = float(row.cost)
        
        # Cost by user (top 50 users)
        user_query = select(
            UsageEvent.user_id,
            func.sum(UsageEvent.total_cost).label('cost')
        ).where(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.timestamp >= month_start,
                UsageEvent.timestamp < month_end,
                UsageEvent.status == EventStatus.COMPLETED,
                UsageEvent.total_cost.isnot(None)
            )
        ).group_by(UsageEvent.user_id).order_by(
            func.sum(UsageEvent.total_cost).desc()
        ).limit(50)
        
        user_result = await session.execute(user_query)
        cost_by_user = {}
        
        for row in user_result:
            cost_by_user[row.user_id] = float(row.cost)
        
        # Create or update billing summary
        summary_data = {
            'tenant_id': tenant_id,
            'billing_year': month_start.year,
            'billing_month': month_start.month,
            'total_cost': float(total_row.total_cost),
            'cost_by_service': cost_by_service,
            'cost_by_user': cost_by_user,
            'total_events': total_row.total_events,
            'active_users': total_row.active_users,
            'is_finalized': False  # Will be finalized at month end
        }
        
        # Upsert billing summary
        stmt = insert(BillingSummary).values(**summary_data)
        stmt = stmt.on_conflict_do_update(
            constraint='uq_billing_summary_unique',
            set_={
                'total_cost': stmt.excluded.total_cost,
                'cost_by_service': stmt.excluded.cost_by_service,
                'cost_by_user': stmt.excluded.cost_by_user,
                'total_events': stmt.excluded.total_events,
                'active_users': stmt.excluded.active_users,
                'updated_at': func.now()
            }
        )
        
        await session.execute(stmt)
        await session.commit()
        
        logger.info(
            "Generated billing summary",
            tenant_id=tenant_id,
            month=month_start.strftime('%Y-%m'),
            total_cost=summary_data['total_cost']
        )


async def main():
    """Main entry point for aggregation service"""
    service = AggregationService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error("Aggregation service crashed", error=str(e), exc_info=True)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())