# Query Service

The Query Service is a high-performance FastAPI-based REST API that provides comprehensive querying, analytics, and reporting capabilities for usage data in the Usage System.

## Overview

This service exposes HTTP endpoints for querying raw usage events, pre-aggregated statistics, cost analysis, trend analysis, and service breakdowns. It includes Redis-based caching for optimal performance and supports various filtering and aggregation options.

## Architecture

### Core Components

- **FastAPI Application**: Modern, high-performance web framework with automatic API documentation
- **Redis Caching Layer**: In-memory caching for frequently requested data
- **Database Repositories**: Abstracted data access layer for usage events and aggregates
- **Pydantic Schemas**: Type-safe request/response models with validation
- **Structured Logging**: Comprehensive logging for monitoring and debugging

### File Structure

```
services/query_service/
├── __init__.py          # Module initialization and exports
├── main.py             # FastAPI application and endpoint implementations
├── schemas.py          # Pydantic models for request/response schemas
└── README_query_service.md  # This documentation
```

## API Endpoints

### Core Query Endpoints

#### 1. Usage Events Query (`/api/v1/usage`)
**GET** - Query raw usage events with comprehensive filtering

**Parameters:**
- `tenant_id` (required): Tenant identifier
- `start_date` (optional): Start date for query range
- `end_date` (optional): End date for query range
- `service_type` (optional): Filter by service type
- `service_provider` (optional): Filter by service provider
- `user_id` (optional): Filter by specific user
- `limit` (optional, max 10,000): Number of events to return
- `offset` (optional): Pagination offset
- `include_billing` (optional): Include billing information

**Response:** `UsageQueryResponse` with events array, pagination info, and query metadata

#### 2. Aggregated Data Query (`/api/v1/usage/aggregate`)
**GET** - Query pre-calculated aggregated usage statistics

**Parameters:**
- `tenant_id` (required): Tenant identifier
- `period` (required): Aggregation period (HOUR, DAY, WEEK, MONTH)
- `start_date` (optional): Start date for query range
- `end_date` (optional): End date for query range
- `service_type` (optional): Filter by service type
- `service_provider` (optional): Filter by service provider
- `user_id` (optional): Filter by specific user

**Response:** `AggregateQueryResponse` with aggregated metrics and time series data

**Default Date Ranges by Period:**
- HOUR: Last 24 hours
- DAY: Last 30 days
- WEEK: Last 12 weeks
- MONTH: Last 365 days

#### 3. Service Breakdown (`/api/v1/usage/by-service`)
**GET** - Get usage breakdown by service type and provider

**Parameters:**
- `tenant_id` (required): Tenant identifier
- `start_date` (optional): Start date (default: 30 days ago)
- `end_date` (optional): End date (default: now)
- `limit` (optional, max 50): Number of services to return

**Response:** `ServiceBreakdownResponse` with service statistics and percentage breakdowns

#### 4. Cost Analysis (`/api/v1/usage/costs`)
**GET** - Get detailed cost analysis and breakdown

**Parameters:**
- `tenant_id` (required): Tenant identifier
- `start_date` (optional): Start date (default: 30 days ago)
- `end_date` (optional): End date (default: now)
- `group_by` (optional): Time grouping (hour, day, week, month)

**Response:** `CostAnalysisResponse` with total costs, cost by service, and time-based cost trends

#### 5. Trend Analysis (`/api/v1/analytics/trends`)
**GET** - Get trend analysis for specified metrics

**Parameters:**
- `tenant_id` (required): Tenant identifier
- `metric` (required): Metric to analyze (event_count, total_cost, unique_users)
- `period` (optional): Aggregation period (default: DAY)
- `start_date` (optional): Start date
- `end_date` (optional): End date
- `service_type` (optional): Filter by service type

**Response:** `TrendAnalysisResponse` with trend direction, percentage change, and data points

### Utility Endpoints

#### Health Check (`/health`)
**GET** - Service health status

**Response:** Service health status and timestamp

#### Metrics (`/metrics`)
**GET** - Prometheus metrics endpoint

**Response:** Prometheus-formatted metrics

## Response Models

### Core Response Schemas (`services/query_service/schemas.py:9-177`)

#### UsageQueryResponse
```python
{
  "events": [
    {
      "event_id": "uuid",
      "timestamp": "datetime",
      "user_id": "string",
      "service_type": "string",
      "service_provider": "string",
      "event_type": "string",
      "metrics": {},
      "tags": [],
      "billing_info": {},  # if include_billing=true
      "total_cost": float  # if include_billing=true
    }
  ],
  "total_count": int,
  "limit": int,
  "offset": int,
  "has_more": bool,
  "query_params": {}
}
```

#### AggregateQueryResponse
```python
{
  "aggregates": [
    {
      "period_start": "datetime",
      "period_end": "datetime",
      "service_type": "string",
      "service_provider": "string",
      "user_id": "string",
      "event_count": int,
      "unique_users": int,
      "total_cost": float,
      "aggregated_metrics": {},
      "error_rate": float
    }
  ],
  "period": "HOUR|DAY|WEEK|MONTH",
  "start_date": "datetime",
  "end_date": "datetime",
  "total_aggregates": int
}
```

#### ServiceBreakdownResponse
```python
{
  "services": [
    {
      "service_type": "string",
      "service_provider": "string",
      "event_count": int,
      "total_cost": float,
      "unique_users": int,
      "top_users": ["user1", "user2"],
      "percentage_of_total": float
    }
  ],
  "total_services": int,
  "total_events": int,
  "total_cost": float,
  "period_start": "datetime",
  "period_end": "datetime"
}
```

## Caching Strategy

### Redis Integration (`services/query_service/main.py:43-589`)

The service implements intelligent caching using Redis:

**Cache Keys Format:**
```
query_cache:{endpoint_name}:{param1=value1:param2=value2}
```

**TTL (Time To Live) Settings:**
- Aggregates: 5 minutes (300 seconds)
- Service breakdown: 10 minutes (600 seconds)
- Cost analysis: 10 minutes (600 seconds)

**Cache Functions:**
- `_build_cache_key()`: Generate consistent cache keys
- `_get_cached_result()`: Retrieve cached data
- `_cache_result()`: Store data with TTL

**Fallback Behavior:**
- If Redis is unavailable, queries fall back to direct database access
- Cache failures are logged but don't interrupt service operation

## Performance Optimizations

### Database Query Optimization

1. **Raw SQL for Complex Aggregations**: Uses optimized SQL queries for service breakdowns and cost analysis
2. **Repository Pattern**: Leverages existing database repositories for consistent data access
3. **Batch Processing**: Efficiently handles large result sets with pagination
4. **Index Utilization**: Queries are designed to use existing database indexes

### Example Optimized Query (`services/query_service/main.py:280-295`)
```sql
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
```

### Memory Management

- **Streaming Responses**: Large datasets are processed in batches
- **Connection Pooling**: Efficient database connection management
- **Lazy Loading**: Data is loaded only when requested

## Configuration

### Environment Variables

The service is configured through the main application settings:

```python
# Database Configuration
database.host
database.port
database.name
database.user
database.password

# Redis Configuration
redis.redis_url

# API Configuration
api.host
api.query_service_port

# Logging Configuration
logging.level
```

### CORS Configuration (`services/query_service/main.py:34-41`)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Error Handling

### Exception Management

The service implements comprehensive error handling:

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found
- `500`: Internal Server Error

**Error Response Format:**
```python
{
  "detail": "Error message description"
}
```

**Error Scenarios:**
- Database connection failures
- Invalid query parameters
- Redis connection issues (graceful fallback)
- Data processing errors

### Logging Strategy (`services/query_service/main.py:23-25`)

Uses structured logging with contextual information:

```python
logger.error("Failed to query usage", error=str(e), tenant_id=tenant_id)
logger.warning("Failed to connect to Redis for caching", error=str(e))
```

## Usage Examples

### Basic Usage Query

```bash
curl -X GET "http://localhost:8002/api/v1/usage?tenant_id=tenant-123&limit=100&include_billing=true"
```

### Aggregated Data Query

```bash
curl -X GET "http://localhost:8002/api/v1/usage/aggregate?tenant_id=tenant-123&period=DAY&service_type=LLM_SERVICE"
```

### Service Breakdown

```bash
curl -X GET "http://localhost:8002/api/v1/usage/by-service?tenant_id=tenant-123&limit=10"
```

### Cost Analysis

```bash
curl -X GET "http://localhost:8002/api/v1/usage/costs?tenant_id=tenant-123&group_by=day"
```

### Trend Analysis

```bash
curl -X GET "http://localhost:8002/api/v1/analytics/trends?tenant_id=tenant-123&metric=total_cost&period=WEEK"
```

## API Documentation

### Interactive Documentation

The service provides automatic API documentation:

- **Swagger UI**: Available at `http://localhost:8002/docs`
- **ReDoc**: Available at `http://localhost:8002/redoc`
- **OpenAPI Schema**: Available at `http://localhost:8002/openapi.json`

### Schema Validation

All endpoints use Pydantic models for:
- **Request Validation**: Automatic parameter validation and type conversion
- **Response Serialization**: Type-safe response formatting
- **API Documentation**: Automatic schema generation

## Monitoring and Observability

### Metrics Collection

- **Prometheus Metrics**: Available at `/metrics` endpoint
- **Request Timing**: Automatic timing of database queries
- **Cache Hit Rates**: Redis cache performance metrics
- **Error Rates**: HTTP error tracking

### Health Checks

```python
{
  "status": "healthy",
  "service": "query_service",
  "timestamp": "2023-12-14T10:30:00Z"
}
```

## Dependencies

### Core Dependencies

- **FastAPI**: Modern web framework with automatic documentation
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: Database ORM and query builder
- **Redis**: In-memory caching layer
- **Uvicorn**: ASGI server for production deployment
- **Structlog**: Structured logging

### Integration Dependencies

- **Shared Database**: Uses `shared.database` for consistent data access
- **Shared Models**: Leverages common data models and enums
- **Shared Utils**: Uses common logging and metrics utilities

## Deployment

### Running the Service

```bash
# Development mode
python -m services.query_service.main

# Production mode with Uvicorn
uvicorn services.query_service.main:app --host 0.0.0.0 --port 8002
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["uvicorn", "services.query_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# API
QUERY_SERVICE_PORT=8002
LOG_LEVEL=info
```

## Security Considerations

### Input Validation

- **Pydantic Validation**: All inputs are validated against strict schemas
- **SQL Injection Protection**: Uses parameterized queries exclusively
- **Rate Limiting**: Can be integrated with API gateways for rate limiting

### Data Access

- **Tenant Isolation**: All queries require tenant_id parameter
- **Parameter Sanitization**: Input parameters are validated and sanitized
- **Error Information**: Error messages don't expose sensitive data

## Future Enhancements

### Planned Features

1. **Real-time Queries**: WebSocket support for live data streaming
2. **Advanced Analytics**: Machine learning-based trend prediction
3. **Data Export**: Export functionality for large datasets (CSV, JSON, Parquet)
4. **Custom Dashboards**: Template-based dashboard generation
5. **Alert Integration**: Threshold-based alerting system

### Performance Improvements

1. **Query Optimization**: Advanced database indexing strategies
2. **Distributed Caching**: Multi-level caching with Redis Cluster
3. **Response Compression**: GZIP compression for large responses
4. **Connection Pooling**: Advanced connection pool management

## Related Components

- **Aggregation Service**: Provides pre-calculated data that this service queries
- **Usage Collection**: Generates the raw events that this service exposes
- **Dashboard UI**: Consumes this API for data visualization
- **Billing System**: Uses cost analysis endpoints for billing calculations