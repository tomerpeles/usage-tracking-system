import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
import structlog

from config import settings
from shared.database import get_session, UsageEventRepository, health_check as db_health_check
from shared.utils import setup_logging, get_logger, validate_event_data
from shared.utils.metrics import metrics_endpoint, record_event_processing, record_batch_processing, api_requests_total, api_request_duration_seconds
from shared.models.enums import ServiceType
from .middleware import RateLimitMiddleware, AuthMiddleware, MetricsMiddleware
from .schemas import (
    EventResponse,
    BatchEventResponse, 
    UsageQueryParams,
    UsageResponse,
    HealthResponse
)

# Setup logging
setup_logging()
logger = get_logger("api_gateway")

# Create FastAPI app
app = FastAPI(
    title="Usage Tracking API Gateway",
    description="Multi-tenant SaaS usage tracking system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Redis connection for event queue
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global redis_client
    try:
        redis_client = redis.from_url(settings.redis.redis_url)
        await redis_client.ping()
        logger.info("Connected to Redis", redis_url=settings.redis.redis_url)
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        redis_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown"""
    if redis_client:
        await redis_client.close()


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()



@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    
    # Check Redis connection
    redis_healthy = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_healthy = True
        except Exception:
            pass
    
    # Check database connection
    db_healthy = await db_health_check()
    
    overall_healthy = redis_healthy and db_healthy
    
    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=datetime.utcnow(),
        services={
            "redis": "up" if redis_healthy else "down",
            "database": "up" if db_healthy else "down"
        }
    )


@app.post("/api/v1/events", response_model=EventResponse)
async def create_event(
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    request: Request
) -> EventResponse:
    """Create a single usage event"""
    
    try:
        # Validate event data
        validated_event = validate_event_data(event_data)
        
        # Add request metadata
        validated_event["request_id"] = str(uuid.uuid4())
        validated_event["metadata_"]["client_ip"] = request.client.host if request.client else None
        validated_event["metadata_"]["user_agent"] = request.headers.get("user-agent")
        
        # Queue event for processing
        if redis_client:
            event_json = _serialize_event(validated_event)
            await redis_client.lpush("usage_events", event_json)
            
            # Record metrics
            record_event_processing(
                tenant_id=validated_event["tenant_id"],
                service_type=validated_event["service_type"],
                event_type=validated_event["event_type"]
            )
            
            logger.info(
                "Event queued for processing",
                event_id=validated_event["event_id"],
                tenant_id=validated_event["tenant_id"],
                service_type=validated_event["service_type"]
            )
        else:
            # Fallback to direct database storage
            background_tasks.add_task(_store_event_directly, validated_event)
        
        return EventResponse(
            success=True,
            event_id=validated_event["event_id"],
            message="Event received and queued for processing"
        )
        
    except Exception as e:
        logger.error("Failed to create event", error=str(e), event_data=event_data)
        raise HTTPException(status_code=400, detail=f"Invalid event data: {str(e)}")


@app.post("/api/v1/events/batch", response_model=BatchEventResponse)
async def create_events_batch(
    batch_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    request: Request
) -> BatchEventResponse:
    """Create multiple usage events in a batch"""
    
    events = batch_data.get("events", [])
    if not events:
        raise HTTPException(status_code=400, detail="No events provided")
    
    if len(events) > settings.batch.max_batch_size:
        raise HTTPException(
            status_code=400, 
            detail=f"Batch size exceeds maximum of {settings.batch.max_batch_size}"
        )
    
    validated_events = []
    failed_events = []
    
    for i, event_data in enumerate(events):
        try:
            validated_event = validate_event_data(event_data)
            
            # Add request metadata
            validated_event["request_id"] = str(uuid.uuid4())
            validated_event["metadata_"]["client_ip"] = request.client.host if request.client else None
            validated_event["metadata_"]["user_agent"] = request.headers.get("user-agent")
            validated_event["metadata_"]["batch_index"] = i
            
            validated_events.append(validated_event)
            
        except Exception as e:
            failed_events.append({
                "index": i,
                "error": str(e),
                "event_data": event_data
            })
    
    # Queue validated events for processing
    if validated_events:
        if redis_client:
            pipe = redis_client.pipeline()
            tenant_id = validated_events[0]["tenant_id"] if validated_events else "unknown"
            
            for event in validated_events:
                event_json = _serialize_event(event)
                pipe.lpush("usage_events", event_json)
                
                # Record metrics for each event
                record_event_processing(
                    tenant_id=event["tenant_id"],
                    service_type=event["service_type"],
                    event_type=event["event_type"]
                )
            
            await pipe.execute()
            
            # Record batch processing metrics
            record_batch_processing(tenant_id, len(validated_events))
            
            logger.info(
                "Batch events queued for processing",
                batch_size=len(validated_events),
                failed_count=len(failed_events)
            )
        else:
            # Fallback to direct database storage
            background_tasks.add_task(_store_events_directly, validated_events)
    
    return BatchEventResponse(
        success=True,
        processed_count=len(validated_events),
        failed_count=len(failed_events),
        failed_events=failed_events,
        message=f"Processed {len(validated_events)} events, {len(failed_events)} failed"
    )


@app.get("/api/v1/usage", response_model=UsageResponse)
async def get_usage(
    tenant_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service_type: Optional[ServiceType] = None,
    user_id: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> UsageResponse:
    """Query usage data with filters"""
    
    # Validate query parameters
    if limit <= 0 or limit > 10000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 10000")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be >= 0")
    
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
            
            # Convert events to response format
            event_data = []
            for event in events:
                event_dict = {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "user_id": event.user_id,
                    "service_type": event.service_type,
                    "service_provider": event.service_provider,
                    "event_type": event.event_type,
                    "metrics": event.metrics,
                    "billing_info": event.billing_info,
                    "total_cost": float(event.total_cost) if event.total_cost else None,
                    "tags": event.tags,
                }
                event_data.append(event_dict)
            
            return UsageResponse(
                events=event_data,
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_more=offset + len(events) < total_count
            )
            
    except Exception as e:
        logger.error("Failed to query usage", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to query usage data")


# Background task functions
async def _store_event_directly(event_data: Dict[str, Any]):
    """Store event directly in database (fallback)"""
    try:
        async with get_session() as session:
            repo = UsageEventRepository(session)
            await repo.create_event(event_data)
            logger.info("Event stored directly", event_id=event_data["event_id"])
    except Exception as e:
        logger.error("Failed to store event directly", error=str(e), event_id=event_data.get("event_id"))


async def _store_events_directly(events_data: List[Dict[str, Any]]):
    """Store events directly in database (fallback)"""
    try:
        async with get_session() as session:
            repo = UsageEventRepository(session)
            await repo.create_events_batch(events_data)
            logger.info("Batch events stored directly", count=len(events_data))
    except Exception as e:
        logger.error("Failed to store batch events directly", error=str(e), count=len(events_data))


def _serialize_event(event_data: Dict[str, Any]) -> str:
    """Serialize event data for Redis queue"""
    import json
    from datetime import datetime
    import uuid
    
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(event_data, default=default_serializer)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.api_gateway_port,
        reload=True,
        log_level=settings.logging.level.lower()
    )