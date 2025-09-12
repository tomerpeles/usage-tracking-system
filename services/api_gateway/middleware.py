import time
from typing import Callable, Dict, Optional
import redis.asyncio as redis
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from config import settings
from shared.utils.metrics import api_requests_total, api_request_duration_seconds
from .schemas import RateLimitResponse, ErrorResponse

logger = structlog.get_logger("middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.rate_limit = settings.rate_limit.per_minute
        self.window_size = 60  # 1 minute window
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
            
        # Skip if Redis is not available
        if not self.redis_client:
            return await call_next(request)
            
        # Get client identifier (IP + tenant_id if available)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        current_requests = await self._get_request_count(client_id)
        
        if current_requests >= self.rate_limit:
            reset_time = await self._get_reset_time(client_id)
            response_data = RateLimitResponse(
                message=f"Rate limit of {self.rate_limit} requests per minute exceeded",
                retry_after=reset_time,
                limit=self.rate_limit,
                reset_time=time.time() + reset_time
            )
            
            return JSONResponse(
                status_code=429,
                content=response_data.model_dump(),
                headers={
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + reset_time)),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Increment request count
        await self._increment_request_count(client_id)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.rate_limit - current_requests - 1)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window_size))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier for rate limiting"""
        client_ip = request.client.host
        
        # Try to get tenant_id from headers or query params
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            tenant_id = request.query_params.get("tenant_id")
        
        if tenant_id:
            return f"rate_limit:{tenant_id}:{client_ip}"
        return f"rate_limit:anonymous:{client_ip}"
    
    async def _get_request_count(self, client_id: str) -> int:
        """Get current request count for client"""
        try:
            count = await self.redis_client.get(client_id)
            return int(count) if count else 0
        except Exception:
            return 0
    
    async def _increment_request_count(self, client_id: str):
        """Increment request count for client"""
        try:
            await self.redis_client.incr(client_id)
            await self.redis_client.expire(client_id, self.window_size)
        except Exception:
            pass
    
    async def _get_reset_time(self, client_id: str) -> int:
        """Get time until rate limit resets"""
        try:
            ttl = await self.redis_client.ttl(client_id)
            return max(1, ttl)  # At least 1 second
        except Exception:
            return self.window_size


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication and authorization middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.public_paths = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_required",
                    "message": "API key is required. Provide it in X-API-Key or Authorization header."
                }
            )
        
        # Remove "Bearer " prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        # Validate API key (this would typically check against a database)
        if not await self._validate_api_key(api_key, request):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_api_key",
                    "message": "Invalid API key provided"
                }
            )
        
        return await call_next(request)
    
    async def _validate_api_key(self, api_key: str, request: Request) -> bool:
        """Validate API key and extract tenant information"""
        
        # For development, accept test keys
        test_keys = {
            "test-api-key": "test-tenant",
            "demo-key": "demo-tenant",
            "admin-key": "admin-tenant"
        }
        
        if api_key in test_keys:
            tenant_id = test_keys[api_key]
            # Add tenant info to request state for downstream use
            request.state.tenant_id = tenant_id
            request.state.api_key_info = {
                "tenant_id": tenant_id,
                "permissions": ["read", "write"],
                "rate_limit": settings.rate_limit.per_minute
            }
            return True
        
        # In production, this would:
        # 1. Query database for API key
        # 2. Check if key is active and not expired
        # 3. Extract tenant_id and permissions
        # 4. Set request.state with tenant info
        
        # For now, reject all other keys
        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=round(process_time * 1000, 2),  # milliseconds
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            # Re-raise HTTP exceptions (they'll be handled by FastAPI)
            raise
        except Exception as e:
            logger.error(
                "Unhandled exception",
                error=str(e),
                path=request.url.path,
                method=request.method,
                exc_info=True
            )
            
            # Return generic error response
            error_response = ErrorResponse(
                error="internal_server_error",
                message="An internal server error occurred"
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump()
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with tenant-specific rules"""
    
    def __init__(self, app, allowed_origins: Optional[Dict[str, list]] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or {}
        self.default_origins = ["*"]  # Configure for production
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Get tenant-specific CORS settings
        tenant_id = getattr(request.state, "tenant_id", None)
        allowed_origins = self.allowed_origins.get(tenant_id, self.default_origins)
        
        origin = request.headers.get("origin")
        if origin and (allowed_origins == ["*"] or origin in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key, X-Tenant-ID"
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track API request metrics"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record start time
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract tenant ID from request if available
        tenant_id = getattr(request.state, "tenant_id", "unknown")
        
        # Get endpoint path (remove query parameters for grouping)
        endpoint = request.url.path
        method = request.method
        status_code = str(response.status_code)
        
        # Record metrics
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            tenant_id=tenant_id
        ).inc()
        
        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
            tenant_id=tenant_id
        ).observe(duration)
        
        return response