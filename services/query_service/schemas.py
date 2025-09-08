from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.models.enums import ServiceType, AggregationPeriod


class UsageQueryResponse(BaseModel):
    """Response model for usage queries"""
    events: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int
    has_more: bool
    query_params: Dict[str, Any]


class AggregateData(BaseModel):
    """Individual aggregate data point"""
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


class AggregateQueryResponse(BaseModel):
    """Response model for aggregate queries"""
    aggregates: List[Dict[str, Any]]
    period: AggregationPeriod
    start_date: datetime
    end_date: datetime
    total_aggregates: int


class ServiceData(BaseModel):
    """Service usage data"""
    service_type: str
    service_provider: str
    event_count: int
    total_cost: Optional[float] = None
    unique_users: int
    top_users: List[str] = []
    percentage_of_total: float = 0.0


class ServiceBreakdownResponse(BaseModel):
    """Response model for service breakdown"""
    services: List[Dict[str, Any]]
    total_services: int
    total_events: int
    total_cost: float
    period_start: datetime
    period_end: datetime


class CostAnalysisResponse(BaseModel):
    """Response model for cost analysis"""
    total_cost: float
    currency: str = "USD"
    period_start: datetime
    period_end: datetime
    cost_by_service: Dict[str, float] = {}
    cost_by_period: Dict[str, float] = {}
    group_by: str


class TrendDataPoint(BaseModel):
    """Trend analysis data point"""
    period: str
    value: float


class TrendAnalysisResponse(BaseModel):
    """Response model for trend analysis"""
    metric: str
    period_type: AggregationPeriod
    start_date: datetime
    end_date: datetime
    data_points: List[Dict[str, Any]]
    trend_direction: str  # "up", "down", "stable"
    percentage_change: float
    service_type: Optional[ServiceType] = None


class UserAnalyticsResponse(BaseModel):
    """Response model for user analytics"""
    user_id: str
    total_events: int
    total_cost: Optional[float] = None
    services_used: List[str] = []
    most_used_service: Optional[str] = None
    avg_events_per_day: float = 0.0
    first_event: Optional[datetime] = None
    last_event: Optional[datetime] = None


class TopUsersResponse(BaseModel):
    """Response model for top users analysis"""
    period_start: datetime
    period_end: datetime
    metric: str  # "events", "cost", "tokens", etc.
    users: List[UserAnalyticsResponse]
    total_users: int


class ComparisonData(BaseModel):
    """Service comparison data"""
    service_type: str
    service_provider: str
    current_period: Dict[str, Any] = {}
    previous_period: Dict[str, Any] = {}
    change_percentage: Dict[str, float] = {}


class ServiceComparisonResponse(BaseModel):
    """Response model for service comparison"""
    comparison_type: str
    current_period_start: datetime
    current_period_end: datetime
    previous_period_start: datetime
    previous_period_end: datetime
    services: List[ComparisonData]


class AlertMetric(BaseModel):
    """Alert-worthy metric"""
    metric_name: str
    current_value: float
    threshold_value: float
    threshold_type: str  # "above", "below"
    severity: str  # "low", "medium", "high"
    message: str


class HealthMetricsResponse(BaseModel):
    """Response model for health metrics"""
    tenant_id: str
    overall_health: str  # "healthy", "warning", "critical"
    timestamp: datetime
    metrics: List[AlertMetric] = []
    error_rate: float = 0.0
    avg_latency_ms: Optional[float] = None
    total_events_last_hour: int = 0
    total_cost_last_hour: float = 0.0


class ExportRequest(BaseModel):
    """Request model for data export"""
    tenant_id: str
    format: str = Field(default="csv", regex="^(csv|json|parquet)$")
    start_date: datetime
    end_date: datetime
    service_type: Optional[ServiceType] = None
    service_provider: Optional[str] = None
    user_id: Optional[str] = None
    include_billing: bool = False
    compress: bool = True


class ExportResponse(BaseModel):
    """Response model for data export"""
    export_id: str
    status: str  # "queued", "processing", "completed", "failed"
    format: str
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None