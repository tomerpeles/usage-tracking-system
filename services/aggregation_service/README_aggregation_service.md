# Aggregation Service

The Aggregation Service is a critical component of the Usage System responsible for processing raw usage events and creating pre-calculated aggregations for fast querying and billing purposes.

## Overview

This service continuously processes usage events stored in the database and generates aggregated statistics at multiple time granularities (hourly, daily, weekly, monthly). It also creates billing summaries for invoicing and cost tracking.

## Architecture

### Core Components

- **AggregationService**: Main service class that orchestrates the aggregation process
- **UsageAggregate Model**: Database model for storing aggregated usage statistics
- **BillingSummary Model**: Database model for monthly billing summaries
- **UsageAggregateRepository**: Database access layer for aggregate operations

### File Structure

```
services/aggregation_service/
├── __init__.py          # Module initialization and exports
├── main.py             # Main aggregation service implementation
└── README_aggregation_service.md  # This documentation
```

## Functionality

### 1. Data Aggregation

The service processes usage events and creates aggregations at multiple levels:

#### Time Granularities
- **Hourly**: Aggregates events by hour (last 25 hours processed)
- **Daily**: Aggregates events by day (last 8 days processed)
- **Weekly**: Aggregates events by week (last 5 weeks processed)
- **Monthly**: Aggregates events by month (last 13 months processed)

#### Aggregation Dimensions
- **Tenant Level**: Overall usage across all services for a tenant
- **Service Type**: Usage broken down by service type (LLM_SERVICE, DOCUMENT_PROCESSOR, API_SERVICE)
- **Service Provider**: Usage broken down by specific service providers
- **User Level**: Usage statistics for top 100 users (by event count)

### 2. Metrics Collected

#### Standard Metrics (All Services)
- `event_count`: Total number of completed events
- `unique_users`: Number of distinct users
- `total_cost`: Sum of all event costs
- `avg_latency_ms`: Average latency (planned feature)
- `p95_latency_ms`: 95th percentile latency (planned feature)
- `error_count`: Number of failed events (planned feature)
- `error_rate`: Error rate percentage (planned feature)

#### Service-Specific Metrics
Stored in `aggregated_metrics` JSONB field:

**LLM Service**:
- `total_input_tokens`: Sum of input tokens
- `total_output_tokens`: Sum of output tokens
- `total_tokens`: Total tokens processed
- `avg_input_tokens`: Average input tokens per request
- `avg_output_tokens`: Average output tokens per request

**Document Processor**:
- `total_pages_processed`: Total pages processed
- `total_characters_extracted`: Total characters extracted
- `avg_processing_time_ms`: Average processing time

**API Service**:
- `total_requests`: Total API requests
- `total_payload_bytes`: Total request payload size
- `total_response_bytes`: Total response size
- `avg_response_time_ms`: Average response time

### 3. Billing Summary Generation

The service generates monthly billing summaries containing:

- **Total Cost**: Monthly cost for the tenant
- **Cost by Service**: Breakdown by service type and provider
- **Cost by User**: Top 50 users by cost
- **Usage Statistics**: Total events and active user counts
- **Finalization Status**: Whether the billing period is closed

## Database Schema

### UsageAggregate Table (`services/aggregation_service/main.py:13-136`)

```sql
CREATE TABLE usage_aggregates (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- HOUR, DAY, WEEK, MONTH
    service_type VARCHAR(50), -- NULL for all services
    service_provider VARCHAR(255), -- NULL for all providers
    user_id VARCHAR(255), -- NULL for all users
    event_count INTEGER NOT NULL DEFAULT 0,
    unique_users INTEGER NOT NULL DEFAULT 0,
    total_cost DECIMAL(12,6),
    aggregated_metrics JSONB,
    avg_latency_ms DECIMAL(10,2),
    p95_latency_ms DECIMAL(10,2),
    error_count INTEGER NOT NULL DEFAULT 0,
    error_rate DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### BillingSummary Table (`services/aggregation_service/main.py:139-214`)

```sql
CREATE TABLE billing_summaries (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    billing_month INTEGER NOT NULL,
    billing_year INTEGER NOT NULL,
    total_cost DECIMAL(12,2) NOT NULL,
    cost_by_service JSONB NOT NULL,
    cost_by_user JSONB NOT NULL,
    total_events INTEGER NOT NULL,
    active_users INTEGER NOT NULL,
    is_finalized BOOLEAN NOT NULL DEFAULT FALSE,
    finalized_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Configuration

### Environment Variables

The service uses configuration from the main application settings:

- **Database Connection**: Configured via `shared.database.get_session()`
- **Logging**: Uses structured logging via `structlog`
- **Aggregation Interval**: 300 seconds (5 minutes) by default

### Timing Configuration

- **Aggregation Cycle**: Runs every 5 minutes
- **Overlap Handling**: Processes overlapping periods to ensure data consistency
- **Retry Logic**: 1-minute delay on errors before retrying

## Key Methods

### AggregationService Class (`services/aggregation_service/main.py:20-573`)

#### Core Methods

- `start()`: Initialize and start the aggregation service
- `stop()`: Gracefully stop the service
- `_aggregation_loop()`: Main processing loop that runs every 5 minutes
- `_run_all_aggregations()`: Execute all aggregation types (hourly, daily, weekly, monthly)

#### Aggregation Methods

- `_aggregate_usage_data()`: Process events for a specific time period
- `_aggregate_tenant_data()`: Aggregate data for a specific tenant
- `_aggregate_tenant_period()`: Create aggregates for a tenant in a specific period
- `_create_aggregate()`: Generate individual aggregate records

#### Utility Methods

- `_get_period_boundaries()`: Calculate time period boundaries
- `_calculate_service_metrics()`: Compute service-specific metrics
- `_generate_billing_summaries()`: Create monthly billing summaries

## Error Handling

The service implements comprehensive error handling:

- **Database Errors**: Logged and retried with exponential backoff
- **Processing Errors**: Individual aggregation failures don't stop the entire cycle
- **Memory Management**: Processes data in batches to handle large datasets
- **Graceful Shutdown**: Handles interrupt signals properly

## Performance Considerations

### Optimizations

1. **Batch Processing**: Processes multiple tenants and periods in batches
2. **Upsert Operations**: Uses PostgreSQL UPSERT to handle duplicate aggregations
3. **Index Usage**: Leverages database indexes for efficient queries
4. **Limited User Aggregation**: Only processes top 100 users to limit data volume

### Resource Usage

- **Memory**: Moderate memory usage due to batch processing
- **CPU**: CPU-intensive during aggregation cycles
- **Database**: Heavy read/write operations on usage_events and aggregate tables
- **Network**: Database connection pool usage

## Monitoring and Logging

The service provides comprehensive logging using structured logging:

```python
# Key log events
logger.info("Starting aggregation service")
logger.info("Starting aggregation cycle")
logger.info("Found X tenants to aggregate for PERIOD")
logger.info("Generated billing summary", tenant_id=..., total_cost=...)
logger.error("Error in aggregation loop", error=..., exc_info=True)
```

## Usage Examples

### Running the Service

```bash
# Run as standalone service
python -m services.aggregation_service.main

# Or import and use programmatically
from services.aggregation_service import AggregationService

service = AggregationService()
await service.start()
```

### Querying Aggregated Data

```python
# Get hourly aggregates for a tenant
from shared.database import UsageAggregateRepository

async with get_session() as session:
    repo = UsageAggregateRepository(session)
    aggregates = await repo.get_aggregates(
        tenant_id="tenant-123",
        period_type=AggregationPeriod.HOUR,
        start_time=datetime.utcnow() - timedelta(hours=24),
        end_time=datetime.utcnow()
    )
```

## Dependencies

- **SQLAlchemy**: Database ORM and query building
- **structlog**: Structured logging
- **asyncio**: Asynchronous execution
- **PostgreSQL**: Database with JSONB support for metrics storage

## Future Enhancements

1. **Real-time Metrics**: Add support for real-time latency and error rate calculations
2. **Custom Aggregation Rules**: Allow tenants to define custom aggregation logic
3. **Data Retention**: Implement automatic cleanup of old aggregations
4. **Performance Monitoring**: Add detailed performance metrics for the aggregation process
5. **Horizontal Scaling**: Support for distributed aggregation across multiple instances

## Related Components

- **Usage Event Collection**: Processes events from `shared.models.UsageEvent`
- **API Service**: Exposes aggregated data via REST endpoints
- **Dashboard**: Visualizes aggregated usage statistics
- **Billing System**: Uses billing summaries for invoice generation