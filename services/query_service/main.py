import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import settings
from shared.database import get_session, UsageEventRepository, UsageAggregateRepository
from shared.models.enums import ServiceType, AggregationPeriod
from shared.utils import setup_logging, get_logger
from .schemas import (
    UsageQueryResponse,
    AggregateQueryResponse,
    ServiceBreakdownResponse,
    CostAnalysisResponse,
    TrendAnalysisResponse
)

# Setup logging
setup_logging()
logger = get_logger("query_service")

# Create FastAPI app
app = FastAPI(
    title="Usage Query Service",
    description="Query and analytics service for usage data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection for caching
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global redis_client
    try:
        redis_client = redis.from_url(settings.redis.redis_url)
        await redis_client.ping()
        logger.info("Connected to Redis for caching")
    except Exception as e:
        logger.warning("Failed to connect to Redis for caching", error=str(e))
        redis_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown"""
    if redis_client:
        await redis_client.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "query_service", "timestamp": datetime.utcnow()}


@app.get("/api/v1/usage", response_model=UsageQueryResponse)
async def query_usage(
    tenant_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service_type: Optional[ServiceType] = None,
    service_provider: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(default=1000, le=10000),
    offset: int = Query(default=0, ge=0),
    include_billing: bool = Query(default=False)
) -> UsageQueryResponse:
    """Query usage events with filters"""
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        async with get_session() as session:
            repo = UsageEventRepository(session)
            
            events, total_count = await repo.get_events_by_tenant(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                service_type=service_type,
                user_id=user_id,
                limit=limit,
                offset=offset
            )
            
            # Filter by service provider if specified
            if service_provider:
                events = [e for e in events if e.service_provider == service_provider]
                total_count = len(events)
            
            # Convert events to response format
            event_data = []
            for event in events:
                event_dict = {
                    "event_id": str(event.event_id),
                    "timestamp": event.timestamp,
                    "user_id": event.user_id,
                    "service_type": event.service_type,
                    "service_provider": event.service_provider,
                    "event_type": event.event_type,
                    "metrics": event.metrics or {},
                    "tags": event.tags or [],
                }
                
                if include_billing:
                    event_dict["billing_info"] = event.billing_info or {}
                    event_dict["total_cost"] = float(event.total_cost) if event.total_cost else None
                
                event_data.append(event_dict)
            
            return UsageQueryResponse(
                events=event_data,
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_more=offset + len(events) < total_count,
                query_params={
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "service_type": service_type,
                    "service_provider": service_provider,
                    "user_id": user_id
                }
            )
            
    except Exception as e:
        logger.error("Failed to query usage", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query usage data")


@app.get("/api/v1/usage/aggregate", response_model=AggregateQueryResponse)
async def query_aggregates(
    tenant_id: str,
    period: AggregationPeriod,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service_type: Optional[ServiceType] = None,
    service_provider: Optional[str] = None,
    user_id: Optional[str] = None
) -> AggregateQueryResponse:
    """Query pre-aggregated usage data"""
    
    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        if period == AggregationPeriod.HOUR:
            start_date = end_date - timedelta(hours=24)
        elif period == AggregationPeriod.DAY:
            start_date = end_date - timedelta(days=30)
        elif period == AggregationPeriod.WEEK:
            start_date = end_date - timedelta(weeks=12)
        else:  # MONTH
            start_date = end_date - timedelta(days=365)
    
    try:
        # Check cache first
        cache_key = _build_cache_key("aggregates", {
            "tenant_id": tenant_id,
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "service_type": service_type,
            "service_provider": service_provider,
            "user_id": user_id
        })
        
        cached_result = await _get_cached_result(cache_key)
        if cached_result:
            return AggregateQueryResponse(**cached_result)
        
        async with get_session() as session:
            repo = UsageAggregateRepository(session)
            
            aggregates = await repo.get_aggregates(
                tenant_id=tenant_id,
                period_type=period,
                start_date=start_date,
                end_date=end_date,
                service_type=service_type,
                user_id=user_id
            )
            
            # Filter by service provider if specified
            if service_provider:
                aggregates = [a for a in aggregates if a.service_provider == service_provider]
            
            # Convert to response format
            aggregate_data = []
            for agg in aggregates:
                aggregate_data.append({
                    "period_start": agg.period_start,
                    "period_end": agg.period_end,
                    "service_type": agg.service_type,
                    "service_provider": agg.service_provider,
                    "user_id": agg.user_id,
                    "event_count": agg.event_count,
                    "unique_users": agg.unique_users,
                    "total_cost": float(agg.total_cost) if agg.total_cost else None,
                    "aggregated_metrics": agg.aggregated_metrics or {},
                    "error_rate": float(agg.error_rate) if agg.error_rate else None,
                })
            
            response = AggregateQueryResponse(
                aggregates=aggregate_data,
                period=period,
                start_date=start_date,
                end_date=end_date,
                total_aggregates=len(aggregate_data)
            )
            
            # Cache the result
            await _cache_result(cache_key, response.dict(), ttl=300)  # 5 minutes
            
            return response
            
    except Exception as e:
        logger.error("Failed to query aggregates", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to query aggregate data")


@app.get("/api/v1/usage/by-service", response_model=ServiceBreakdownResponse)
async def get_service_breakdown(
    tenant_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=10, le=50)
) -> ServiceBreakdownResponse:
    """Get usage breakdown by service"""
    
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        cache_key = _build_cache_key("service_breakdown", {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": limit
        })
        
        cached_result = await _get_cached_result(cache_key)
        if cached_result:
            return ServiceBreakdownResponse(**cached_result)
        
        async with get_session() as session:
            repo = UsageEventRepository(session)
            
            # Get service breakdown using raw SQL for better performance
            query = """
                SELECT 
                    service_type,
                    service_provider,
                    COUNT(*) as event_count,
                    SUM(total_cost) as total_cost,
                    COUNT(DISTINCT user_id) as unique_users,
                    ARRAY_AGG(DISTINCT user_id ORDER BY user_id LIMIT 5) as top_users
                FROM usage_events 
                WHERE tenant_id = :tenant_id 
                    AND timestamp >= :start_date 
                    AND timestamp <= :end_date
                GROUP BY service_type, service_provider
                ORDER BY event_count DESC
                LIMIT :limit
            """
            
            result = await session.execute(query, {
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            })
            
            services = []
            total_events = 0
            total_cost = 0.0
            
            for row in result:
                event_count = row.event_count
                cost = float(row.total_cost) if row.total_cost else 0.0
                
                services.append({
                    "service_type": row.service_type,
                    "service_provider": row.service_provider,
                    "event_count": event_count,
                    "total_cost": cost,
                    "unique_users": row.unique_users,
                    "top_users": row.top_users[:5] if row.top_users else [],
                    "percentage_of_total": 0.0  # Will calculate after getting totals
                })
                
                total_events += event_count
                total_cost += cost
            
            # Calculate percentages
            for service in services:
                if total_events > 0:
                    service["percentage_of_total"] = (service["event_count"] / total_events) * 100
            
            response = ServiceBreakdownResponse(
                services=services,
                total_services=len(services),
                total_events=total_events,
                total_cost=total_cost,
                period_start=start_date,
                period_end=end_date
            )
            
            await _cache_result(cache_key, response.dict(), ttl=600)  # 10 minutes
            
            return response
            
    except Exception as e:
        logger.error("Failed to get service breakdown", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get service breakdown")


@app.get("/api/v1/usage/costs", response_model=CostAnalysisResponse)
async def get_cost_analysis(
    tenant_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = Query(default="day", regex="^(hour|day|week|month)$")
) -> CostAnalysisResponse:
    """Get cost analysis and breakdown"""
    
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        cache_key = _build_cache_key("cost_analysis", {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by
        })
        
        cached_result = await _get_cached_result(cache_key)
        if cached_result:
            return CostAnalysisResponse(**cached_result)
        
        async with get_session() as session:
            # Get total cost
            total_query = """
                SELECT SUM(total_cost) as total_cost
                FROM usage_events 
                WHERE tenant_id = :tenant_id 
                    AND timestamp >= :start_date 
                    AND timestamp <= :end_date
                    AND total_cost IS NOT NULL
            """
            
            total_result = await session.execute(total_query, {
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            total_cost = 0.0
            for row in total_result:
                total_cost = float(row.total_cost) if row.total_cost else 0.0
            
            # Get cost by service
            service_query = """
                SELECT 
                    service_type,
                    service_provider,
                    SUM(total_cost) as cost
                FROM usage_events 
                WHERE tenant_id = :tenant_id 
                    AND timestamp >= :start_date 
                    AND timestamp <= :end_date
                    AND total_cost IS NOT NULL
                GROUP BY service_type, service_provider
                ORDER BY cost DESC
            """
            
            service_result = await session.execute(service_query, {
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            cost_by_service = {}
            for row in service_result:
                key = f"{row.service_type}:{row.service_provider}"
                cost_by_service[key] = float(row.cost) if row.cost else 0.0
            
            # Get cost by time period
            time_format = {
                "hour": "date_trunc('hour', timestamp)",
                "day": "date_trunc('day', timestamp)",
                "week": "date_trunc('week', timestamp)",
                "month": "date_trunc('month', timestamp)"
            }[group_by]
            
            time_query = f"""
                SELECT 
                    {time_format} as period,
                    SUM(total_cost) as cost
                FROM usage_events 
                WHERE tenant_id = :tenant_id 
                    AND timestamp >= :start_date 
                    AND timestamp <= :end_date
                    AND total_cost IS NOT NULL
                GROUP BY {time_format}
                ORDER BY period
            """
            
            time_result = await session.execute(time_query, {
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            cost_by_period = {}
            for row in time_result:
                period_str = row.period.isoformat() if row.period else "unknown"
                cost_by_period[period_str] = float(row.cost) if row.cost else 0.0
            
            response = CostAnalysisResponse(
                total_cost=total_cost,
                currency="USD",
                period_start=start_date,
                period_end=end_date,
                cost_by_service=cost_by_service,
                cost_by_period=cost_by_period,
                group_by=group_by
            )
            
            await _cache_result(cache_key, response.dict(), ttl=600)  # 10 minutes
            
            return response
            
    except Exception as e:
        logger.error("Failed to get cost analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get cost analysis")


@app.get("/api/v1/analytics/trends", response_model=TrendAnalysisResponse)
async def get_trend_analysis(
    tenant_id: str,
    metric: str = Query(default="event_count", regex="^(event_count|total_cost|unique_users)$"),
    period: AggregationPeriod = AggregationPeriod.DAY,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service_type: Optional[ServiceType] = None
) -> TrendAnalysisResponse:
    """Get trend analysis for specified metric"""
    
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        days_back = {"hour": 7, "day": 30, "week": 12*7, "month": 365}[period]
        start_date = end_date - timedelta(days=days_back)
    
    try:
        async with get_session() as session:
            repo = UsageAggregateRepository(session)
            
            aggregates = await repo.get_aggregates(
                tenant_id=tenant_id,
                period_type=period,
                start_date=start_date,
                end_date=end_date,
                service_type=service_type
            )
            
            # Extract metric values and calculate trend
            data_points = []
            metric_values = []
            
            for agg in aggregates:
                value = 0.0
                if metric == "event_count":
                    value = agg.event_count
                elif metric == "total_cost":
                    value = float(agg.total_cost) if agg.total_cost else 0.0
                elif metric == "unique_users":
                    value = agg.unique_users
                
                data_points.append({
                    "period": agg.period_start.isoformat(),
                    "value": value
                })
                metric_values.append(value)
            
            # Calculate trend direction and percentage change
            trend_direction = "stable"
            percentage_change = 0.0
            
            if len(metric_values) >= 2:
                first_half = metric_values[:len(metric_values)//2]
                second_half = metric_values[len(metric_values)//2:]
                
                first_avg = sum(first_half) / len(first_half) if first_half else 0
                second_avg = sum(second_half) / len(second_half) if second_half else 0
                
                if second_avg > first_avg * 1.05:  # 5% threshold
                    trend_direction = "up"
                elif second_avg < first_avg * 0.95:
                    trend_direction = "down"
                
                if first_avg > 0:
                    percentage_change = ((second_avg - first_avg) / first_avg) * 100
            
            return TrendAnalysisResponse(
                metric=metric,
                period_type=period,
                start_date=start_date,
                end_date=end_date,
                data_points=data_points,
                trend_direction=trend_direction,
                percentage_change=percentage_change,
                service_type=service_type
            )
            
    except Exception as e:
        logger.error("Failed to get trend analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get trend analysis")


# Helper functions for caching
def _build_cache_key(prefix: str, params: Dict[str, Any]) -> str:
    """Build cache key from parameters"""
    param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    return f"query_cache:{prefix}:{param_str}"


async def _get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached result from Redis"""
    if not redis_client:
        return None
    
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            import json
            return json.loads(cached_data)
    except Exception:
        pass
    
    return None


async def _cache_result(cache_key: str, data: Dict[str, Any], ttl: int = 300):
    """Cache result in Redis"""
    if not redis_client:
        return
    
    try:
        import json
        cached_data = json.dumps(data, default=str)  # Handle datetime serialization
        await redis_client.setex(cache_key, ttl, cached_data)
    except Exception as e:
        logger.warning("Failed to cache result", error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.query_service_port,
        reload=True,
        log_level=settings.logging.level.lower()
    )