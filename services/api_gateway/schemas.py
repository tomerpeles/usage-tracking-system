import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    """Response model for single event creation"""
    success: bool
    event_id: uuid.UUID
    message: str
    

class BatchEventResponse(BaseModel):
    """Response model for batch event creation"""
    success: bool
    processed_count: int
    failed_count: int
    failed_events: List[Dict[str, Any]] = []
    message: str


class UsageEvent(BaseModel):
    """Usage event data model for responses"""
    event_id: uuid.UUID
    timestamp: datetime
    user_id: str
    service_type: str
    service_provider: str
    event_type: str
    metrics: Dict[str, Any]
    billing_info: Optional[Dict[str, Any]] = None
    total_cost: Optional[float] = None
    tags: List[str] = []


class UsageResponse(BaseModel):
    """Response model for usage queries"""
    events: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int
    has_more: bool


class UsageQueryParams(BaseModel):
    """Query parameters for usage endpoints"""
    tenant_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    service_type: Optional[str] = None
    user_id: Optional[str] = None
    limit: int = Field(default=1000, le=10000, ge=1)
    offset: int = Field(default=0, ge=0)


class AggregateUsageResponse(BaseModel):
    """Response model for aggregated usage data"""
    period: str
    period_start: datetime
    period_end: datetime
    service_type: Optional[str] = None
    service_provider: Optional[str] = None
    user_id: Optional[str] = None
    event_count: int
    unique_users: int
    total_cost: Optional[float] = None
    aggregated_metrics: Dict[str, Any] = {}
    error_rate: Optional[float] = None


class ServiceBreakdownResponse(BaseModel):
    """Response model for usage breakdown by service"""
    service_type: str
    service_provider: str
    event_count: int
    total_cost: Optional[float] = None
    percentage_of_total: Optional[float] = None
    top_users: List[Dict[str, Any]] = []


class CostBreakdownResponse(BaseModel):
    """Response model for cost breakdown"""
    total_cost: float
    currency: str = "USD"
    period_start: datetime
    period_end: datetime
    cost_by_service: Dict[str, float] = {}
    cost_by_user: Dict[str, float] = {}
    cost_by_day: Dict[str, float] = {}


class AnalyticsTrendsResponse(BaseModel):
    """Response model for analytics trends"""
    metric: str
    period_type: str
    data_points: List[Dict[str, Any]]
    trend_direction: Optional[str] = None  # "up", "down", "stable"
    percentage_change: Optional[float] = None


class AnalyticsComparisonResponse(BaseModel):
    """Response model for service comparison analytics"""
    comparison_type: str
    period_start: datetime
    period_end: datetime
    services: List[Dict[str, Any]]
    

class TopUsersResponse(BaseModel):
    """Response model for top users analytics"""
    period_start: datetime
    period_end: datetime
    metric: str  # "events", "cost", "tokens", etc.
    users: List[Dict[str, Any]]


class ServiceConfigResponse(BaseModel):
    """Response model for service configurations"""
    service_type: str
    service_name: str
    description: Optional[str] = None
    providers: List[str] = []
    required_fields: List[str] = []
    optional_fields: List[str] = []
    is_active: bool
    version: str


class CreateServiceRequest(BaseModel):
    """Request model for creating service configuration"""
    service_type: str = Field(min_length=1, max_length=50)
    service_name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    providers: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    billing_config: Dict[str, Any] = Field(default_factory=dict)
    aggregation_rules: Dict[str, Any] = Field(default_factory=dict)
    validation_schema: Optional[Dict[str, Any]] = None


class UpdateServiceRequest(BaseModel):
    """Request model for updating service configuration"""
    service_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    providers: Optional[List[str]] = None
    required_fields: Optional[List[str]] = None
    optional_fields: Optional[List[str]] = None
    billing_config: Optional[Dict[str, Any]] = None
    aggregation_rules: Optional[Dict[str, Any]] = None
    validation_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str  # "healthy" or "unhealthy"
    timestamp: datetime
    services: Dict[str, str] = {}  # service -> status
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: str = "validation_error"
    message: str
    field_errors: List[Dict[str, Any]] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimitResponse(BaseModel):
    """Rate limit error response model"""
    error: str = "rate_limit_exceeded"
    message: str
    retry_after: int  # seconds
    limit: int
    reset_time: datetime