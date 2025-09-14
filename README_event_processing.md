# Event Processing System

The Event Processing System is a core component of the Usage System that handles the asynchronous processing of usage events from various services. It transforms raw usage data into enriched, billable records.

## Overview

The event processor consumes events from a Redis queue, enriches them with metadata and billing information, and stores them in the database for aggregation and billing purposes.

## Architecture

```
Redis Queue → Event Processor → Database
     ↓              ↓              ↓
usage_events → Processing → usage_events table
                   ↓
            dead_letter_events
```

## Core Components

### EventProcessor Class
Main processing engine located in `services/event_processor/main.py`

**Key Features:**
- Asynchronous event processing
- Batch processing for efficiency
- Automatic retry mechanism
- Dead letter queue for failed events
- Redis connection management

### Event Flow

1. **Event Retrieval**
   - Uses Redis BRPOP to retrieve events from `usage_events` queue
   - Processes in batches (default: 10 events)
   - Deserializes JSON data back to Python objects

2. **Event Validation**
   - Validates required fields:
     - `tenant_id`
     - `user_id`
     - `service_type`
     - `service_provider`
     - `event_type`

3. **Event Enrichment**
   - Updates processing timestamps
   - Calculates derived metrics
   - Adds service-specific metadata
   - Computes session durations

4. **Billing Calculation**
   - Retrieves billing rules from database
   - Supports model-specific and provider-level rules
   - Calculates costs using configurable billing methods
   - Handles tiered rates and minimum charges

5. **Database Storage**
   - Uses upsert operations to handle duplicates
   - Stores enriched events in `usage_events` table

## Configuration

Event processor configuration is managed through environment variables:

```python
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Processing Configuration
BATCH_SIZE=10              # Events per batch
PROCESSING_TIMEOUT=30      # Seconds to wait for events
MAX_RETRIES=3             # Maximum retry attempts
```

## Event Enrichment

### Service-Specific Enrichment

**LLM Services:**
- Calculates `total_tokens` from `input_tokens` + `output_tokens`
- Adds cost-per-token metrics
- Processes model-specific billing rules

**Session-Based Services:**
- Calculates `session_duration_ms` from start/end timestamps
- Adds session metadata

### Metadata Enhancement

The processor enriches events with:
- Processing timestamps
- Calculated metrics
- Service configuration data
- Billing information

## Error Handling

### Retry Mechanism
- Failed events are automatically retried up to 3 times
- Retry count is tracked in event metadata
- Exponential backoff between retries

### Dead Letter Queue
Events that exceed max retries are sent to `dead_letter_events` queue for:
- Manual review and processing
- Debugging and troubleshooting
- Data recovery operations

### Error Categories
1. **Validation Errors:** Missing required fields
2. **Processing Errors:** Enrichment or billing calculation failures
3. **Database Errors:** Storage or connection issues
4. **System Errors:** Redis connectivity problems

## Monitoring and Logging

### Structured Logging
The processor uses structured logging with:
- Event IDs for traceability
- Processing metrics
- Error context and stack traces
- Performance timing data

### Key Metrics Logged
- Batch processing times
- Success/failure rates
- Queue depths
- Database operation timing
- Error frequencies

## Running the Event Processor

### Development
```bash
cd services/event_processor
python main.py
```

### Production (Docker)
```bash
docker-compose up event-processor
```

### Environment Variables
Ensure these are set:
- `REDIS_URL`
- `DATABASE_URL`
- `LOG_LEVEL`

## Event Schema

### Input Event Structure
```json
{
  "event_id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "service_type": "LLM_SERVICE|STORAGE_SERVICE|COMPUTE_SERVICE",
  "service_provider": "openai|anthropic|aws",
  "event_type": "api_call|file_upload|compute_job",
  "timestamp": "2024-01-01T12:00:00Z",
  "metrics": {
    "input_tokens": 100,
    "output_tokens": 50,
    "model": "gpt-4"
  },
  "metadata_": {}
}
```

### Output Event Structure
```json
{
  "event_id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "service_type": "LLM_SERVICE",
  "service_provider": "openai",
  "event_type": "api_call",
  "timestamp": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:05Z",
  "metrics": {
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "model": "gpt-4"
  },
  "billing_info": {
    "total_cost": 0.003,
    "billing_unit": "tokens",
    "rate_per_unit": 0.00002,
    "calculation_method": "linear"
  },
  "total_cost": 0.003,
  "status": "COMPLETED",
  "error_message": null,
  "metadata_": {}
}
```

## Billing Integration

### Billing Rules
The processor integrates with the billing system to:
- Retrieve active billing rules by service and provider
- Support model-specific pricing
- Handle complex pricing structures (tiered, minimum charges)
- Calculate accurate costs for aggregation

### Supported Billing Methods
- **Linear:** cost = rate × quantity
- **Tiered:** Different rates for usage tiers
- **Flat:** Fixed cost per event
- **Minimum:** Ensures minimum charge is applied

## Troubleshooting

### Common Issues

**Events not processing:**
- Check Redis connectivity
- Verify queue names match
- Check event format validity

**Billing calculation errors:**
- Ensure billing rules exist
- Verify service type mappings
- Check metric field names

**Database storage failures:**
- Verify database connectivity
- Check for schema mismatches
- Review unique constraint violations

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python main.py
```

## Performance Considerations

### Batch Processing
- Default batch size: 10 events
- Adjust based on event complexity and database performance
- Monitor processing latency

### Connection Pooling
- Redis connections are managed per processor instance
- Database connections use async session pooling
- Consider connection limits under high load

### Scaling
- Run multiple processor instances for horizontal scaling
- Use Redis Sentinel for high availability
- Consider partitioned queues for very high throughput

## Related Components

- **Event Ingestion Service:** Publishes events to Redis queue
- **Aggregation Service:** Consumes processed events for billing
- **Billing Rules Management:** Configures pricing and calculation methods
- **Service Registry:** Defines service configurations and enrichment rules