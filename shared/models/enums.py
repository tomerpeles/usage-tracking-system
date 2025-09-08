import enum


class ServiceType(str, enum.Enum):
    """Service types for usage tracking"""
    LLM_SERVICE = "llm_service"
    DOCUMENT_PROCESSOR = "document_processor"
    API_SERVICE = "api_service"
    CUSTOM = "custom"


class EventStatus(str, enum.Enum):
    """Event processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AggregationPeriod(str, enum.Enum):
    """Aggregation time periods"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AlertType(str, enum.Enum):
    """Alert types"""
    USAGE_THRESHOLD = "usage_threshold"
    ERROR_RATE = "error_rate"
    COST_THRESHOLD = "cost_threshold"
    LATENCY_THRESHOLD = "latency_threshold"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class BillingUnit(str, enum.Enum):
    """Billing units"""
    TOKENS = "tokens"
    REQUESTS = "requests"
    PAGES = "pages"
    BYTES = "bytes"
    MINUTES = "minutes"
    CUSTOM = "custom"


class ProcessingStatus(str, enum.Enum):
    """Processing status for events"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"