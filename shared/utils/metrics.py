"""Prometheus metrics utilities for Usage Tracking System"""

import time
from typing import Optional
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from fastapi.responses import Response as FastAPIResponse


# API Gateway Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code', 'tenant_id']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint', 'tenant_id']
)

events_processed_total = Counter(
    'events_processed_total', 
    'Total number of events processed',
    ['tenant_id', 'service_type', 'event_type']
)

batch_events_processed_total = Counter(
    'batch_events_processed_total',
    'Total number of batch events processed',
    ['tenant_id']
)

# Event Processor Metrics
event_processing_duration_seconds = Histogram(
    'event_processing_duration_seconds',
    'Event processing duration in seconds',
    ['event_type', 'service_type']
)

redis_queue_size = Gauge(
    'redis_queue_size',
    'Current size of Redis event queue'
)

# Query Service Metrics
query_requests_total = Counter(
    'query_requests_total',
    'Total number of query requests',
    ['tenant_id', 'query_type']
)

query_duration_seconds = Histogram(
    'query_duration_seconds',
    'Query duration in seconds',
    ['tenant_id', 'query_type']
)

# Database Metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# Business Metrics
total_tokens_processed = Counter(
    'total_tokens_processed',
    'Total tokens processed',
    ['tenant_id', 'service_provider', 'model']
)

total_cost_usd = Counter(
    'total_cost_usd',
    'Total cost in USD',
    ['tenant_id', 'service_provider']
)


def track_api_request(method: str, endpoint: str, tenant_id: Optional[str] = None):
    """Decorator to track API request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = "200"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = "500"
                raise
            finally:
                duration = time.time() - start_time
                tenant = tenant_id or "unknown"
                
                api_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    tenant_id=tenant
                ).inc()
                
                api_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint,
                    tenant_id=tenant
                ).observe(duration)
        
        return wrapper
    return decorator


def metrics_endpoint() -> FastAPIResponse:
    """FastAPI endpoint to expose Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def record_event_processing(tenant_id: str, service_type: str, event_type: str):
    """Record event processing metrics"""
    events_processed_total.labels(
        tenant_id=tenant_id,
        service_type=service_type,
        event_type=event_type
    ).inc()


def record_batch_processing(tenant_id: str, count: int):
    """Record batch event processing metrics"""
    batch_events_processed_total.labels(tenant_id=tenant_id).inc(count)


def record_token_usage(tenant_id: str, service_provider: str, model: str, tokens: int):
    """Record token usage metrics"""
    total_tokens_processed.labels(
        tenant_id=tenant_id,
        service_provider=service_provider,
        model=model
    ).inc(tokens)


def record_cost(tenant_id: str, service_provider: str, cost: float):
    """Record cost metrics"""
    total_cost_usd.labels(
        tenant_id=tenant_id,
        service_provider=service_provider
    ).inc(cost)


def update_redis_queue_size(size: int):
    """Update Redis queue size metric"""
    redis_queue_size.set(size)