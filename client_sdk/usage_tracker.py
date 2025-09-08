import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from .exceptions import (
    UsageTrackingError,
    RateLimitError,
    ValidationError,
    AuthenticationError,
    ServiceUnavailableError,
    ConfigurationError,
    RetryableError,
)


class UsageTracker:
    """Client SDK for tracking usage events"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        tenant_id: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        enable_batching: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ):
        """Initialize Usage Tracker client
        
        Args:
            api_key: API key for authentication
            base_url: Base URL of the usage tracking API
            tenant_id: Default tenant ID for events
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff multiplier for retries
            enable_batching: Whether to enable event batching
            batch_size: Maximum number of events in a batch
            flush_interval: How often to flush batched events (seconds)
        """
        
        if not api_key:
            raise ConfigurationError("API key is required")
        
        if not base_url:
            raise ConfigurationError("Base URL is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.tenant_id = tenant_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Batching configuration
        self.enable_batching = enable_batching
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._event_batch: List[Dict[str, Any]] = []
        self._last_flush = datetime.utcnow()
        self._flush_lock = asyncio.Lock()
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self._client is None:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": f"usage-tracker-sdk/1.0.0",
            }
            
            if self.tenant_id:
                headers["X-Tenant-ID"] = self.tenant_id
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
    
    async def close(self):
        """Close the client and flush any remaining events"""
        if self.enable_batching and self._event_batch:
            await self.flush_events()
        
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def track_llm(
        self,
        tenant_id: Optional[str] = None,
        user_id: str = None,
        model: str = None,
        input_tokens: int = None,
        output_tokens: int = None,
        latency_ms: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_version: Optional[str] = None,
        service_provider: str = "openai",
        event_type: str = "completion",
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Track LLM usage event
        
        Args:
            tenant_id: Tenant identifier (uses default if not provided)
            user_id: User identifier
            model: Model name (e.g., "gpt-4", "claude-3")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens  
            latency_ms: Response latency in milliseconds
            temperature: Model temperature setting
            max_tokens: Maximum tokens setting
            model_version: Version of the model
            service_provider: Service provider (e.g., "openai", "anthropic")
            event_type: Type of event (default: "completion")
            session_id: Session identifier for grouping events
            request_id: Request identifier for tracing
            metadata: Additional metadata
            tags: List of tags for categorization
            
        Returns:
            Event ID
            
        Raises:
            ValidationError: If required fields are missing or invalid
            UsageTrackingError: If tracking fails
        """
        
        # Validate required fields
        if not user_id:
            raise ValidationError("user_id is required for LLM tracking")
        if not model:
            raise ValidationError("model is required for LLM tracking")
        if input_tokens is None or input_tokens < 0:
            raise ValidationError("input_tokens must be >= 0")
        if output_tokens is None or output_tokens < 0:
            raise ValidationError("output_tokens must be >= 0")
        
        event_data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id or self.tenant_id,
            "user_id": user_id,
            "service_type": "llm_service",
            "service_provider": service_provider,
            "event_type": event_type,
            "metadata": {
                "model": model,
                "model_version": model_version,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **(metadata or {}),
            },
            "metrics": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "latency_ms": latency_ms,
            },
            "tags": tags or [],
            "session_id": session_id,
            "request_id": request_id,
        }
        
        return await self._track_event(event_data)
    
    async def track_document(
        self,
        tenant_id: Optional[str] = None,
        user_id: str = None,
        service_provider: str = None,
        document_type: str = None,
        processing_type: str = None,
        pages_processed: int = None,
        characters_extracted: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        file_format: Optional[str] = None,
        event_type: str = "processing",
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Track document processing event
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            service_provider: Service provider name
            document_type: Type of document (e.g., "invoice", "contract")
            processing_type: Type of processing (e.g., "ocr", "extraction")
            pages_processed: Number of pages processed
            characters_extracted: Number of characters extracted
            processing_time_ms: Processing time in milliseconds
            file_size_bytes: Size of processed file in bytes
            file_format: File format (e.g., "pdf", "docx")
            event_type: Type of event (default: "processing")
            session_id: Session identifier
            request_id: Request identifier
            metadata: Additional metadata
            tags: List of tags
            
        Returns:
            Event ID
        """
        
        # Validate required fields
        if not user_id:
            raise ValidationError("user_id is required for document tracking")
        if not service_provider:
            raise ValidationError("service_provider is required for document tracking")
        if not document_type:
            raise ValidationError("document_type is required for document tracking")
        if not processing_type:
            raise ValidationError("processing_type is required for document tracking")
        if pages_processed is None or pages_processed <= 0:
            raise ValidationError("pages_processed must be > 0")
        
        event_data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id or self.tenant_id,
            "user_id": user_id,
            "service_type": "document_processor",
            "service_provider": service_provider,
            "event_type": event_type,
            "metadata": {
                "document_type": document_type,
                "processing_type": processing_type,
                "file_format": file_format,
                **(metadata or {}),
            },
            "metrics": {
                "pages_processed": pages_processed,
                "characters_extracted": characters_extracted,
                "processing_time_ms": processing_time_ms,
                "file_size_bytes": file_size_bytes,
            },
            "tags": tags or [],
            "session_id": session_id,
            "request_id": request_id,
        }
        
        return await self._track_event(event_data)
    
    async def track_api(
        self,
        tenant_id: Optional[str] = None,
        user_id: str = None,
        service_provider: str = None,
        endpoint: str = None,
        method: str = "GET",
        request_count: int = 1,
        response_time_ms: Optional[int] = None,
        payload_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        status_code: Optional[int] = None,
        api_version: Optional[str] = None,
        event_type: str = "request",
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Track API usage event
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            service_provider: Service provider name
            endpoint: API endpoint path
            method: HTTP method
            request_count: Number of requests
            response_time_ms: Response time in milliseconds
            payload_size_bytes: Request payload size
            response_size_bytes: Response payload size
            status_code: HTTP status code
            api_version: API version
            event_type: Type of event (default: "request")
            session_id: Session identifier
            request_id: Request identifier
            metadata: Additional metadata
            tags: List of tags
            
        Returns:
            Event ID
        """
        
        # Validate required fields
        if not user_id:
            raise ValidationError("user_id is required for API tracking")
        if not service_provider:
            raise ValidationError("service_provider is required for API tracking")
        if not endpoint:
            raise ValidationError("endpoint is required for API tracking")
        
        event_data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id or self.tenant_id,
            "user_id": user_id,
            "service_type": "api_service",
            "service_provider": service_provider,
            "event_type": event_type,
            "metadata": {
                "endpoint": endpoint,
                "method": method.upper(),
                "api_version": api_version,
                "status_code": status_code,
                **(metadata or {}),
            },
            "metrics": {
                "request_count": request_count,
                "response_time_ms": response_time_ms,
                "payload_size_bytes": payload_size_bytes,
                "response_size_bytes": response_size_bytes,
            },
            "tags": tags or [],
            "session_id": session_id,
            "request_id": request_id,
        }
        
        return await self._track_event(event_data)
    
    async def track_custom(
        self,
        tenant_id: Optional[str] = None,
        user_id: str = None,
        service_type: str = None,
        service_provider: str = None,
        event_type: str = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Track custom usage event
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            service_type: Type of service
            service_provider: Service provider name
            event_type: Type of event
            metrics: Custom metrics dict
            metadata: Additional metadata
            tags: List of tags
            session_id: Session identifier
            request_id: Request identifier
            
        Returns:
            Event ID
        """
        
        # Validate required fields
        if not user_id:
            raise ValidationError("user_id is required for custom tracking")
        if not service_type:
            raise ValidationError("service_type is required for custom tracking")
        if not service_provider:
            raise ValidationError("service_provider is required for custom tracking")
        if not event_type:
            raise ValidationError("event_type is required for custom tracking")
        
        event_data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id or self.tenant_id,
            "user_id": user_id,
            "service_type": service_type,
            "service_provider": service_provider,
            "event_type": event_type,
            "metadata": metadata or {},
            "metrics": metrics or {},
            "tags": tags or [],
            "session_id": session_id,
            "request_id": request_id,
        }
        
        return await self._track_event(event_data)
    
    async def _track_event(self, event_data: Dict[str, Any]) -> str:
        """Track a single event (internal method)"""
        
        if not event_data.get("tenant_id"):
            if not self.tenant_id:
                raise ValidationError("tenant_id is required (set default or provide per event)")
            event_data["tenant_id"] = self.tenant_id
        
        event_id = event_data["event_id"]
        
        if self.enable_batching:
            await self._add_to_batch(event_data)
        else:
            await self._send_single_event(event_data)
        
        return event_id
    
    async def _add_to_batch(self, event_data: Dict[str, Any]):
        """Add event to batch for later sending"""
        async with self._flush_lock:
            self._event_batch.append(event_data)
            
            # Check if we should flush
            should_flush = (
                len(self._event_batch) >= self.batch_size or
                (datetime.utcnow() - self._last_flush).total_seconds() >= self.flush_interval
            )
            
            if should_flush:
                await self._flush_batch()
    
    async def flush_events(self) -> int:
        """Flush all batched events immediately
        
        Returns:
            Number of events flushed
        """
        async with self._flush_lock:
            return await self._flush_batch()
    
    async def _flush_batch(self) -> int:
        """Flush current batch (internal method)"""
        if not self._event_batch:
            return 0
        
        events_to_send = self._event_batch.copy()
        self._event_batch.clear()
        self._last_flush = datetime.utcnow()
        
        try:
            await self._send_batch_events(events_to_send)
            return len(events_to_send)
        except Exception as e:
            # Re-add failed events to batch for retry
            self._event_batch.extend(events_to_send)
            raise e
    
    async def _send_single_event(self, event_data: Dict[str, Any]):
        """Send a single event to the API"""
        await self._ensure_client()
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    "/api/v1/events",
                    json=event_data
                )
                
                if response.status_code == 200:
                    return response.json()
                
                await self._handle_error_response(response)
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                raise ServiceUnavailableError(f"Service unavailable: {str(e)}")
    
    async def _send_batch_events(self, events: List[Dict[str, Any]]):
        """Send a batch of events to the API"""
        await self._ensure_client()
        
        batch_data = {"events": events}
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    "/api/v1/events/batch",
                    json=batch_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("failed_count", 0) > 0:
                        self.logger.warning(
                            f"Batch had {result['failed_count']} failed events",
                            extra={"failed_events": result.get("failed_events", [])}
                        )
                    return result
                
                await self._handle_error_response(response)
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                raise ServiceUnavailableError(f"Service unavailable: {str(e)}")
    
    async def _handle_error_response(self, response: httpx.Response):
        """Handle error responses from the API"""
        try:
            error_data = response.json()
        except:
            error_data = {"error": "unknown", "message": response.text}
        
        if response.status_code == 400:
            raise ValidationError(
                error_data.get("message", "Validation failed"),
                field_errors=error_data.get("field_errors", []),
                response=error_data
            )
        elif response.status_code == 401:
            raise AuthenticationError(
                error_data.get("message", "Authentication failed"),
                response=error_data
            )
        elif response.status_code == 429:
            raise RateLimitError(
                error_data.get("message", "Rate limit exceeded"),
                retry_after=response.headers.get("Retry-After"),
                response=error_data
            )
        elif response.status_code >= 500:
            raise ServiceUnavailableError(
                error_data.get("message", "Service unavailable"),
                response=error_data
            )
        else:
            raise UsageTrackingError(
                error_data.get("message", f"Request failed with status {response.status_code}"),
                status_code=response.status_code,
                response=error_data
            )
    
    async def get_usage(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        service_type: Optional[str] = None,
        service_provider: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        include_billing: bool = False,
    ) -> Dict[str, Any]:
        """Query usage data
        
        Args:
            tenant_id: Tenant to query (uses default if not provided)
            start_date: Start date for query
            end_date: End date for query
            service_type: Filter by service type
            service_provider: Filter by service provider
            user_id: Filter by user ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            include_billing: Whether to include billing information
            
        Returns:
            Usage query results
        """
        await self._ensure_client()
        
        params = {
            "tenant_id": tenant_id or self.tenant_id,
            "limit": limit,
            "offset": offset,
            "include_billing": include_billing,
        }
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if service_type:
            params["service_type"] = service_type
        if service_provider:
            params["service_provider"] = service_provider
        if user_id:
            params["user_id"] = user_id
        
        response = await self._client.get("/api/v1/usage", params=params)
        
        if response.status_code == 200:
            return response.json()
        
        await self._handle_error_response(response)