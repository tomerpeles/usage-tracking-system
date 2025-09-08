import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from shared.models.enums import ServiceType


class EventMetadata(BaseModel):
    """Base metadata for events"""
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    client_version: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class LLMEventData(BaseModel):
    """Validation model for LLM service events"""
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    service_type: ServiceType = ServiceType.LLM_SERVICE
    service_provider: str = Field(min_length=1, max_length=255)
    event_type: str = Field(default="completion")
    
    # LLM-specific metadata
    model: str = Field(min_length=1)
    model_version: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    
    # LLM metrics
    input_tokens: int = Field(gt=0)
    output_tokens: int = Field(ge=0)
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = Field(None, ge=0)
    
    # Common fields
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    @validator("total_tokens", always=True)
    def calculate_total_tokens(cls, v, values):
        if v is None and "input_tokens" in values and "output_tokens" in values:
            return values["input_tokens"] + values["output_tokens"]
        return v
    
    def to_event_dict(self) -> Dict[str, Any]:
        """Convert to usage event dict format"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "service_type": self.service_type,
            "service_provider": self.service_provider,
            "event_type": self.event_type,
            "metadata_": {
                "model": self.model,
                "model_version": self.model_version,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                **((self.metadata_ or {})),
            },
            "metrics": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "latency_ms": self.latency_ms,
            },
            "tags": self.tags or [],
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


class DocumentEventData(BaseModel):
    """Validation model for document processing events"""
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    service_type: ServiceType = ServiceType.DOCUMENT_PROCESSOR
    service_provider: str = Field(min_length=1, max_length=255)
    event_type: str = Field(default="processing")
    
    # Document-specific metadata
    document_type: str = Field(min_length=1)
    processing_type: str = Field(min_length=1)
    file_format: Optional[str] = None
    
    # Document metrics
    pages_processed: int = Field(gt=0)
    characters_extracted: Optional[int] = Field(None, ge=0)
    processing_time_ms: Optional[int] = Field(None, ge=0)
    file_size_bytes: Optional[int] = Field(None, gt=0)
    
    # Common fields
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_event_dict(self) -> Dict[str, Any]:
        """Convert to usage event dict format"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "service_type": self.service_type,
            "service_provider": self.service_provider,
            "event_type": self.event_type,
            "metadata_": {
                "document_type": self.document_type,
                "processing_type": self.processing_type,
                "file_format": self.file_format,
                **((self.metadata_ or {})),
            },
            "metrics": {
                "pages_processed": self.pages_processed,
                "characters_extracted": self.characters_extracted,
                "processing_time_ms": self.processing_time_ms,
                "file_size_bytes": self.file_size_bytes,
            },
            "tags": self.tags or [],
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


class APIEventData(BaseModel):
    """Validation model for API service events"""
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    service_type: ServiceType = ServiceType.API_SERVICE
    service_provider: str = Field(min_length=1, max_length=255)
    event_type: str = Field(default="request")
    
    # API-specific metadata
    endpoint: str = Field(min_length=1)
    method: str = Field(min_length=1)
    api_version: Optional[str] = None
    
    # API metrics
    request_count: int = Field(default=1, gt=0)
    response_time_ms: Optional[int] = Field(None, ge=0)
    payload_size_bytes: Optional[int] = Field(None, ge=0)
    response_size_bytes: Optional[int] = Field(None, ge=0)
    status_code: Optional[int] = Field(None, ge=100, le=599)
    
    # Common fields
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_event_dict(self) -> Dict[str, Any]:
        """Convert to usage event dict format"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "service_type": self.service_type,
            "service_provider": self.service_provider,
            "event_type": self.event_type,
            "metadata_": {
                "endpoint": self.endpoint,
                "method": self.method,
                "api_version": self.api_version,
                "status_code": self.status_code,
                **((self.metadata_ or {})),
            },
            "metrics": {
                "request_count": self.request_count,
                "response_time_ms": self.response_time_ms,
                "payload_size_bytes": self.payload_size_bytes,
                "response_size_bytes": self.response_size_bytes,
            },
            "tags": self.tags or [],
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


class BatchEventData(BaseModel):
    """Validation model for batch event submission"""
    events: List[Dict[str, Any]] = Field(min_items=1, max_items=1000)
    
    @validator("events")
    def validate_events(cls, v):
        validated_events = []
        for event_data in v:
            service_type = event_data.get("service_type")
            if service_type == ServiceType.LLM_SERVICE:
                validated_events.append(LLMEventData(**event_data))
            elif service_type == ServiceType.DOCUMENT_PROCESSOR:
                validated_events.append(DocumentEventData(**event_data))
            elif service_type == ServiceType.API_SERVICE:
                validated_events.append(APIEventData(**event_data))
            else:
                # Generic event validation for custom services
                validated_events.append(event_data)
        return validated_events


def validate_event_data(event_data: Dict[str, Any], service_type: Optional[ServiceType] = None) -> Dict[str, Any]:
    """Validate event data based on service type"""
    if service_type is None:
        service_type = event_data.get("service_type")
    
    if service_type == ServiceType.LLM_SERVICE:
        validated = LLMEventData(**event_data)
        return validated.to_event_dict()
    elif service_type == ServiceType.DOCUMENT_PROCESSOR:
        validated = DocumentEventData(**event_data)
        return validated.to_event_dict()
    elif service_type == ServiceType.API_SERVICE:
        validated = APIEventData(**event_data)
        return validated.to_event_dict()
    else:
        # For custom services, do basic validation
        required_fields = [
            "tenant_id", "user_id", "service_type", 
            "service_provider", "event_type"
        ]
        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults
        if "event_id" not in event_data:
            event_data["event_id"] = uuid.uuid4()
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.utcnow()
        if "metadata_" not in event_data:
            event_data["metadata_"] = {}
        if "metrics" not in event_data:
            event_data["metrics"] = {}
        if "tags" not in event_data:
            event_data["tags"] = []
        
        return event_data