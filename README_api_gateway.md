# API Gateway Service

The API Gateway is the main entry point for the Usage Tracking System, providing RESTful API endpoints for event ingestion, usage querying, and system management.

## Overview

The API Gateway service acts as the front-facing interface for clients to interact with the usage tracking system. It handles authentication, rate limiting, request validation, and routes requests to appropriate backend services.

## Key Features

### Core Functionality
- **Event Ingestion**: Single event and batch event processing
- **Usage Querying**: Retrieve usage data with filtering and pagination
- **Health Monitoring**: System health checks and status reporting
- **Metrics Collection**: Prometheus metrics for monitoring and observability

### Middleware Stack
- **Authentication**: API key-based authentication with tenant isolation
- **Rate Limiting**: Redis-based rate limiting per client/tenant
- **CORS**: Cross-origin resource sharing with tenant-specific rules
- **Request Logging**: Comprehensive request/response logging
- **Error Handling**: Global error handling with structured responses
- **Metrics**: Automatic API metrics collection

## API Endpoints

### Event Management

#### POST /api/v1/events
Create a single usage event.

**Request Body:**
```json
{
  "tenant_id": "string",
  "user_id": "string",
  "service_type": "string",
  "service_provider": "string",
  "event_type": "string",
  "metrics": {},
  "billing_info": {},
  "tags": []
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "uuid",
  "message": "Event received and queued for processing"
}
```

#### POST /api/v1/events/batch
Create multiple usage events in a single request.

**Request Body:**
```json
{
  "events": [
    {
      "tenant_id": "string",
      "user_id": "string",
      "service_type": "string",
      // ... other event fields
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "processed_count": 10,
  "failed_count": 0,
  "failed_events": [],
  "message": "Processed 10 events, 0 failed"
}
```

### Usage Querying

#### GET /api/v1/usage
Query usage data with filters and pagination.

**Query Parameters:**
- `tenant_id` (required): Tenant identifier
- `start_date` (optional): Start date for filtering
- `end_date` (optional): End date for filtering
- `service_type` (optional): Filter by service type
- `user_id` (optional): Filter by user
- `limit` (optional, default=1000): Number of records to return
- `offset` (optional, default=0): Pagination offset

**Response:**
```json
{
  "events": [...],
  "total_count": 1000,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

### System Management

#### GET /health
System health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "services": {
    "redis": "up",
    "database": "up"
  },
  "version": "1.0.0"
}
```

#### GET /metrics
Prometheus metrics endpoint for monitoring.

## Architecture

### Request Flow
1. **Authentication**: Validate API key and extract tenant information
2. **Rate Limiting**: Check and enforce rate limits per client/tenant
3. **Validation**: Validate request data against schemas
4. **Processing**:
   - For events: Queue in Redis or fallback to direct database storage
   - For queries: Fetch from database with applied filters
5. **Response**: Return structured JSON response

### Event Processing
- **Primary Path**: Events are queued in Redis for asynchronous processing
- **Fallback Path**: Direct database storage if Redis is unavailable
- **Batch Processing**: Optimized batch operations with pipeline processing

### Data Flow
```
Client Request → Auth Middleware → Rate Limit → Validation → Redis Queue → Response
                                                         ↓
                                                   Event Processor Service
                                                         ↓
                                                     Database
```

## Configuration

The service uses configuration from the main `config.py`:

- **API Settings**: Host, port, and CORS configuration
- **Redis**: Connection settings for event queuing and rate limiting
- **Database**: Connection settings for usage queries
- **Rate Limiting**: Requests per minute limits
- **Batch Processing**: Maximum batch sizes
- **Logging**: Log levels and structured logging

## Middleware Components

### Authentication Middleware (`AuthMiddleware`)
- API key validation (X-API-Key or Authorization header)
- Tenant extraction and request state management
- Public endpoint exemptions (/health, /metrics, /docs)

### Rate Limiting Middleware (`RateLimitMiddleware`)
- Redis-based sliding window rate limiting
- Per-client and per-tenant limits
- Rate limit headers in responses

### Metrics Middleware (`MetricsMiddleware`)
- Automatic request/response metrics collection
- Prometheus counter and histogram metrics
- Endpoint and tenant-based labeling

### Error Handling Middleware (`ErrorHandlingMiddleware`)
- Global exception catching and logging
- Structured error responses
- HTTP exception pass-through

## Data Models

### Request/Response Schemas
- `EventResponse`: Single event creation response
- `BatchEventResponse`: Batch event creation response
- `UsageResponse`: Usage query response with pagination
- `HealthResponse`: System health status
- `ErrorResponse`: Standardized error responses

### Validation
- Pydantic models for request/response validation
- Field validation and constraints
- Type safety and serialization

## Dependencies

### Core Dependencies
- **FastAPI**: Web framework for API endpoints
- **Redis**: Event queuing and rate limiting
- **PostgreSQL**: Usage data storage (via shared database layer)
- **Pydantic**: Data validation and serialization

### Monitoring & Logging
- **Prometheus**: Metrics collection
- **Structlog**: Structured logging
- **Uvicorn**: ASGI server

## Usage Examples

### Single Event
```bash
curl -X POST "http://localhost:8000/api/v1/events" \
  -H "X-API-Key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "user-123",
    "service_type": "COMPUTE",
    "service_provider": "aws",
    "event_type": "vm_usage",
    "metrics": {
      "instance_type": "t3.micro",
      "duration_hours": 1.5
    }
  }'
```

### Query Usage
```bash
curl -X GET "http://localhost:8000/api/v1/usage?tenant_id=test-tenant&limit=10" \
  -H "X-API-Key: test-api-key"
```

### Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

## Error Handling

The API Gateway provides structured error responses:

### Authentication Error (401)
```json
{
  "error": "authentication_required",
  "message": "API key is required. Provide it in X-API-Key or Authorization header."
}
```

### Rate Limit Error (429)
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 100 requests per minute exceeded",
  "retry_after": 45,
  "limit": 100,
  "reset_time": 1642248000
}
```

### Validation Error (400)
```json
{
  "error": "validation_error",
  "message": "Invalid event data: missing required field 'tenant_id'"
}
```

## Running the Service

### Development
```bash
cd services/api_gateway
python main.py
```

### Production
```bash
uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables
Ensure the following environment variables are configured:
- Database connection settings
- Redis connection settings
- API configuration (host, port)
- Rate limiting settings

## Monitoring

The service exposes metrics at `/metrics` endpoint for Prometheus scraping:

- `api_requests_total`: Total API requests counter
- `api_request_duration_seconds`: Request duration histogram
- Custom business metrics from the metrics middleware

## Security Features

- **API Key Authentication**: Secure tenant-based access control
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Input Validation**: Comprehensive request validation
- **Error Sanitization**: Secure error responses without sensitive data exposure
- **CORS Configuration**: Controlled cross-origin access

## File Structure

```
services/api_gateway/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application and endpoints
├── middleware.py        # Custom middleware implementations
└── schemas.py           # Pydantic models for validation
```

## Integration Points

### Upstream Services
- Client applications (web apps, mobile apps, IoT devices)
- SDK integrations
- Third-party service integrations

### Downstream Services
- Event Processing Service (via Redis queue)
- Aggregation Service (via database queries)
- Database (direct queries for usage data)

### External Dependencies
- Redis (event queuing, rate limiting)
- PostgreSQL (usage data storage)
- Prometheus (metrics collection)