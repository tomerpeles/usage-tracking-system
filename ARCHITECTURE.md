# Usage Tracking System - Architecture Documentation

## System Overview

The Usage Tracking System is a production-ready, multi-tenant SaaS platform designed to track, process, and analyze usage events from various service types including LLMs, document processors, and APIs. The system follows a microservices architecture with event-driven processing and real-time analytics capabilities.

## 1. High-Level System Architecture

### Purpose
Shows the overall system context, external actors, and major system boundaries.

### Diagram
```mermaid
graph TB
    subgraph "External Actors"
        U[Users/Applications]
        A[Admins/Operators]
        M[Monitoring Systems]
    end
    
    subgraph "Client Layer"
        SDK[Python Client SDK]
        API_DIRECT[Direct API Calls]
    end
    
    subgraph "Load Balancer"
        LB[Nginx Load Balancer]
    end
    
    subgraph "API Layer"
        AG[API Gateway :8000]
        QS[Query Service :8002]
    end
    
    subgraph "Processing Layer"
        EP[Event Processor]
        AS[Aggregation Service]
    end
    
    subgraph "Data Layer"
        PG[(TimescaleDB/PostgreSQL)]
        RD[(Redis Queue/Cache)]
    end
    
    subgraph "Monitoring Layer"
        PROM[Prometheus]
        GRAF[Grafana Dashboard]
    end
    
    %% Client connections
    U --> SDK
    U --> API_DIRECT
    SDK --> LB
    API_DIRECT --> LB
    
    %% Load balancer routing
    LB --> AG
    LB --> QS
    
    %% API Layer connections
    AG --> RD
    AG --> PG
    QS --> PG
    QS --> RD
    
    %% Processing Layer
    EP --> RD
    EP --> PG
    AS --> PG
    
    %% Monitoring
    AG --> PROM
    QS --> PROM
    EP --> PROM
    AS --> PROM
    PROM --> GRAF
    A --> GRAF
    M --> PROM
    
    %% Styling
    classDef service fill:#e1f5fe
    classDef database fill:#f3e5f5
    classDef queue fill:#fff3e0
    classDef monitoring fill:#e8f5e8
    
    class AG,QS,EP,AS service
    class PG database
    class RD queue
    class PROM,GRAF monitoring
```

### Components
- **Python Client SDK**: Easy-to-use SDK for applications to track usage events
- **API Gateway**: Main entry point for event ingestion and basic queries  
- **Query Service**: Dedicated service for complex analytics and data retrieval
- **Event Processor**: Async service processing events from Redis queue
- **Aggregation Service**: Background service generating pre-computed summaries
- **TimescaleDB**: Time-series optimized PostgreSQL for efficient data storage
- **Redis**: Message queue for event processing and result caching
- **Nginx**: Load balancer for production deployments

### Key Data Flows
- **Event Ingestion**: SDK/API → API Gateway → Redis Queue → Event Processor → Database
- **Query Flow**: Client → Query Service → Database/Cache → Response
- **Aggregation Flow**: Aggregation Service → Database (reads/writes summaries)
- **Monitoring**: All services → Prometheus → Grafana

## 2. Service/Component Architecture

### Purpose
Detailed view of all services, their interactions, and internal APIs.

### Diagram
```mermaid
graph TB
    subgraph "Client SDK Layer"
        SDK[UsageTracker SDK]
        SDK_METHODS[track_llm()<br/>track_document()<br/>track_api()<br/>track_custom()<br/>get_usage()]
        SDK --> SDK_METHODS
    end
    
    subgraph "API Gateway Service"
        AG_MAIN[API Gateway Main]
        AG_AUTH[Auth Middleware]
        AG_RATE[Rate Limit Middleware] 
        AG_ENDPOINTS["/api/v1/events"<br/>"/api/v1/events/batch"<br/>"/api/v1/usage"<br/>"/health"]
        
        AG_MAIN --> AG_AUTH
        AG_AUTH --> AG_RATE
        AG_RATE --> AG_ENDPOINTS
    end
    
    subgraph "Event Processor Service"
        EP_MAIN[Event Processor]
        EP_QUEUE[Queue Consumer]
        EP_ENRICHER[Event Enricher]
        EP_BILLING[Billing Calculator]
        EP_VALIDATOR[Data Validator]
        
        EP_MAIN --> EP_QUEUE
        EP_QUEUE --> EP_VALIDATOR
        EP_VALIDATOR --> EP_ENRICHER
        EP_ENRICHER --> EP_BILLING
    end
    
    subgraph "Query Service"
        QS_MAIN[Query Service Main]
        QS_ENDPOINTS["/api/v1/usage"<br/>"/api/v1/usage/aggregate"<br/>"/api/v1/usage/by-service"<br/>"/api/v1/usage/costs"<br/>"/api/v1/analytics/trends"]
        QS_CACHE[Result Caching]
        
        QS_MAIN --> QS_ENDPOINTS
        QS_MAIN --> QS_CACHE
    end
    
    subgraph "Aggregation Service"
        AS_MAIN[Aggregation Service]
        AS_SCHEDULER[Aggregation Scheduler]
        AS_HOURLY[Hourly Aggregator]
        AS_DAILY[Daily Aggregator] 
        AS_MONTHLY[Monthly Aggregator]
        AS_BILLING[Billing Summarizer]
        
        AS_MAIN --> AS_SCHEDULER
        AS_SCHEDULER --> AS_HOURLY
        AS_SCHEDULER --> AS_DAILY
        AS_SCHEDULER --> AS_MONTHLY
        AS_SCHEDULER --> AS_BILLING
    end
    
    subgraph "Shared Components"
        MODELS[Data Models<br/>UsageEvent<br/>ServiceRegistry<br/>BillingRule<br/>UsageAggregate]
        REPOS[Repository Layer<br/>UsageEventRepository<br/>ServiceRegistryRepository<br/>BillingRuleRepository]
        UTILS[Shared Utilities<br/>Logging<br/>Validation<br/>Billing Calculation]
        
        MODELS --> REPOS
        REPOS --> UTILS
    end
    
    subgraph "External Dependencies"
        PG[(TimescaleDB)]
        REDIS[(Redis)]
        PROM[Prometheus Metrics]
    end
    
    %% Client to API Gateway
    SDK_METHODS --> AG_ENDPOINTS
    
    %% API Gateway to Redis
    AG_ENDPOINTS --> REDIS
    AG_ENDPOINTS --> PG
    
    %% Event Processing Flow
    REDIS --> EP_QUEUE
    EP_BILLING --> PG
    
    %% Query Service connections
    QS_ENDPOINTS --> PG
    QS_CACHE --> REDIS
    
    %% Aggregation Service
    AS_BILLING --> PG
    
    %% Shared components usage
    EP_MAIN --> REPOS
    QS_MAIN --> REPOS
    AS_MAIN --> REPOS
    AG_MAIN --> REPOS
    
    %% Monitoring
    AG_MAIN --> PROM
    EP_MAIN --> PROM
    QS_MAIN --> PROM
    AS_MAIN --> PROM
    
    %% Styling
    classDef service fill:#e1f5fe
    classDef middleware fill:#fff9c4
    classDef database fill:#f3e5f5
    classDef shared fill:#f0f4ff
    
    class AG_MAIN,EP_MAIN,QS_MAIN,AS_MAIN service
    class AG_AUTH,AG_RATE middleware  
    class PG,REDIS database
    class MODELS,REPOS,UTILS shared
```

### Key Service Responsibilities

**API Gateway Service:**
- Event ingestion (single and batch)
- Request authentication and authorization
- Rate limiting and quota enforcement
- Basic usage queries
- Health monitoring

**Event Processor Service:**
- Asynchronous event processing from Redis queue
- Event validation and enrichment
- Billing cost calculation
- Service registry lookups
- Dead letter queue handling for failed events

**Query Service:**
- Complex analytics queries
- Pre-aggregated data retrieval
- Cost analysis and breakdowns
- Trend analysis and forecasting
- Result caching for performance

**Aggregation Service:**
- Scheduled data aggregation (hourly/daily/monthly)
- Billing summary generation
- Performance metric calculations
- Multi-dimensional rollups (tenant, service, user)

## 3. Data Architecture

### Purpose
Shows database schemas, data flow, and relationships between data stores.

### Diagram
```mermaid
erDiagram
    USAGE_EVENTS ||--o{ BILLING_RULES : "calculates_cost"
    USAGE_EVENTS }|--|| TENANTS : "belongs_to"
    USAGE_EVENTS }|--|| SERVICE_REGISTRY : "references"
    USAGE_EVENTS ||--o{ USAGE_AGGREGATES : "summarized_in"
    USAGE_AGGREGATES }|--|| TENANTS : "belongs_to"
    BILLING_SUMMARIES }|--|| TENANTS : "belongs_to"
    USAGE_EVENTS ||--o{ BILLING_SUMMARIES : "contributes_to"
    
    USAGE_EVENTS {
        uuid id PK
        uuid event_id UK "Deduplication key"
        timestamp timestamp "TimescaleDB partition key"
        string tenant_id FK "Multi-tenancy"
        string user_id "Event actor"
        enum service_type "llm_service, document_processor, api_service"
        string service_provider "openai, anthropic, etc"
        string event_type "completion, processing, request"
        jsonb metrics "Quantifiable measurements"
        jsonb billing_info "Cost calculations"
        jsonb metadata "Additional context"
        string[] tags "Categorization"
        enum status "pending, completed, failed"
        decimal total_cost "Calculated cost"
        string session_id "Grouping identifier"
        string request_id "Tracing identifier"
        int retry_count "Error handling"
        string error_message "Failure details"
        timestamp created_at
        timestamp updated_at
    }
    
    SERVICE_REGISTRY {
        uuid id PK
        enum service_type UK
        string service_name
        text description
        jsonb providers "Supported providers"
        jsonb required_fields "Validation schema"
        jsonb billing_config "Default billing rules"
        jsonb aggregation_rules "Summarization logic"
        jsonb validation_schema "Input validation"
        bool is_active
        string version
        timestamp created_at
        timestamp updated_at
    }
    
    BILLING_RULES {
        uuid id PK
        enum service_type
        string provider
        string model_or_tier "Specific pricing tier"
        enum billing_unit "tokens, requests, pages"
        decimal rate_per_unit
        jsonb tiered_rates "Volume discounts"
        decimal minimum_charge
        string calculation_method "multiply, sum, custom"
        text calculation_expression "Custom formula"
        timestamp effective_from
        timestamp effective_until
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
    
    USAGE_AGGREGATES {
        uuid id PK
        string tenant_id FK
        timestamp period_start "Aggregation window"
        timestamp period_end
        enum period_type "hour, day, week, month"
        enum service_type "Nullable - all services"
        string service_provider "Nullable - all providers"  
        string user_id "Nullable - all users"
        int event_count "Total events"
        int unique_users "Distinct users"
        decimal total_cost "Sum of costs"
        jsonb aggregated_metrics "Service-specific totals"
        decimal avg_latency_ms "Performance metrics"
        decimal p95_latency_ms
        int error_count "Reliability metrics"
        decimal error_rate "0.0 to 1.0"
        timestamp created_at
        timestamp updated_at
    }
    
    BILLING_SUMMARIES {
        uuid id PK
        string tenant_id FK
        int billing_year
        int billing_month
        decimal total_cost "Monthly total"
        jsonb cost_by_service "Service breakdown"
        jsonb cost_by_user "User breakdown"
        int total_events "Event count"
        int active_users "Unique users"
        bool is_finalized "Billing locked"
        timestamp finalized_at
        timestamp created_at
        timestamp updated_at
    }
    
    TENANTS {
        uuid id PK
        string tenant_id UK "Business identifier"
        string name
        string contact_email
        jsonb settings "Tenant configuration"
        jsonb rate_limits "API quotas"
        jsonb usage_quotas "Resource limits"
        string billing_email
        jsonb billing_settings "Payment config"
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
```

### Data Stores and Their Purposes

**TimescaleDB/PostgreSQL (Primary Database):**
- **usage_events**: Main event storage with time-based partitioning
- **usage_aggregates**: Pre-computed summaries for fast querying
- **billing_summaries**: Monthly billing rollups for invoicing
- **service_registry**: Service definitions and configurations
- **billing_rules**: Pricing rules and cost calculation logic
- **tenants**: Multi-tenant configuration and settings

**Redis (Cache and Queue):**
- **Event Queue**: `usage_events` list for async processing
- **Dead Letter Queue**: `dead_letter_events` for failed events  
- **Query Cache**: `query_cache:*` keys for API response caching
- **Rate Limiting**: Token bucket counters per tenant
- **Session Storage**: Temporary state for batch processing

### Key Indexes and Performance Optimizations

**Primary Indexes:**
- TimescaleDB automatic time-based partitioning on `timestamp`
- Composite indexes on `(tenant_id, timestamp)` for tenant queries
- Service-based indexes on `(service_type, timestamp)`
- User-based indexes on `(user_id, timestamp)`

**JSON Indexes:**
- GIN indexes on JSONB columns (`metadata`, `metrics`, `billing_info`)
- Partial indexes on status for efficient error handling

**Aggregation Optimizations:**
- Unique constraints preventing duplicate aggregations
- Multi-dimensional rollup strategies (tenant → service → user)

## 4. Deployment Architecture

### Purpose
Shows infrastructure components, containerization, and production deployment.

### Diagram
```mermaid
graph TB
    subgraph "Load Balancer Tier"
        LB[Nginx Load Balancer<br/>:80]
        SSL[SSL Termination]
        LB --> SSL
    end
    
    subgraph "Application Tier"
        subgraph "API Gateway Containers"
            AG1[API Gateway<br/>Container 1<br/>:8000]
            AG2[API Gateway<br/>Container 2<br/>:8000]
            AG3[API Gateway<br/>Container 3<br/>:8000]
        end
        
        subgraph "Query Service Containers"
            QS1[Query Service<br/>Container 1<br/>:8002]
            QS2[Query Service<br/>Container 2<br/>:8002]
        end
        
        subgraph "Background Services"
            EP1[Event Processor<br/>Container 1]
            EP2[Event Processor<br/>Container 2]
            EP3[Event Processor<br/>Container 3]
            AS[Aggregation Service<br/>Container]
        end
    end
    
    subgraph "Data Tier"
        subgraph "Database Cluster"
            PG_PRIMARY[(TimescaleDB Primary<br/>:5432)]
            PG_REPLICA1[(TimescaleDB Replica 1<br/>:5432)]
            PG_REPLICA2[(TimescaleDB Replica 2<br/>:5432)]
        end
        
        subgraph "Cache Cluster"
            REDIS_MASTER[(Redis Master<br/>:6379)]
            REDIS_REPLICA[(Redis Replica<br/>:6379)]
        end
    end
    
    subgraph "Monitoring & Ops Tier"
        PROM[Prometheus<br/>:9090]
        GRAF[Grafana<br/>:3000]
        LOGS[Log Aggregation]
        ALERTS[Alert Manager]
    end
    
    subgraph "Infrastructure"
        DOCKER[Docker Engine]
        K8S[Kubernetes Orchestration]
        STORAGE[Persistent Storage]
    end
    
    %% Load balancer routing
    SSL --> AG1
    SSL --> AG2  
    SSL --> AG3
    SSL --> QS1
    SSL --> QS2
    
    %% Application to data connections
    AG1 --> PG_PRIMARY
    AG2 --> PG_PRIMARY
    AG3 --> PG_PRIMARY
    
    QS1 --> PG_REPLICA1
    QS2 --> PG_REPLICA2
    
    AG1 --> REDIS_MASTER
    AG2 --> REDIS_MASTER
    AG3 --> REDIS_MASTER
    QS1 --> REDIS_REPLICA
    QS2 --> REDIS_REPLICA
    
    EP1 --> REDIS_MASTER
    EP2 --> REDIS_MASTER
    EP3 --> REDIS_MASTER
    EP1 --> PG_PRIMARY
    EP2 --> PG_PRIMARY
    EP3 --> PG_PRIMARY
    
    AS --> PG_PRIMARY
    
    %% Database replication
    PG_PRIMARY --> PG_REPLICA1
    PG_PRIMARY --> PG_REPLICA2
    REDIS_MASTER --> REDIS_REPLICA
    
    %% Monitoring connections
    AG1 --> PROM
    AG2 --> PROM
    AG3 --> PROM
    QS1 --> PROM
    QS2 --> PROM
    EP1 --> PROM
    EP2 --> PROM
    EP3 --> PROM
    AS --> PROM
    
    PROM --> GRAF
    PROM --> ALERTS
    
    %% Infrastructure
    DOCKER --> K8S
    K8S --> STORAGE
    
    %% Styling
    classDef app fill:#e1f5fe
    classDef db fill:#f3e5f5
    classDef monitoring fill:#e8f5e8
    classDef infra fill:#fff3e0
    
    class AG1,AG2,AG3,QS1,QS2,EP1,EP2,EP3,AS app
    class PG_PRIMARY,PG_REPLICA1,PG_REPLICA2,REDIS_MASTER,REDIS_REPLICA db
    class PROM,GRAF,LOGS,ALERTS monitoring
    class DOCKER,K8S,STORAGE infra
```

### Deployment Configuration

**Container Orchestration:**
- Docker containers with multi-stage builds
- Kubernetes for production orchestration
- Horizontal Pod Autoscaling based on CPU/memory
- Service mesh for inter-service communication

**Resource Allocation:**
- API Gateway: 512MB RAM, 0.5 CPU per container
- Query Service: 512MB RAM, 0.5 CPU per container  
- Event Processor: 512MB RAM, 0.5 CPU per container
- Aggregation Service: 512MB RAM, 0.5 CPU (single instance)

**High Availability:**
- Multiple replicas for stateless services
- Database clustering with read replicas
- Redis replication for cache reliability
- Health checks and automatic failover

**Networking:**
- Private network (172.20.0.0/16) for service communication
- Load balancer with SSL termination
- Service discovery via Kubernetes DNS
- Network policies for security isolation

## 5. Event Processing Flow Sequence

### Purpose
Detailed sequence diagram showing how events flow through the system from ingestion to storage.

### Diagram
```mermaid
sequenceDiagram
    participant C as Client/SDK
    participant AG as API Gateway
    participant R as Redis Queue
    participant EP as Event Processor
    participant SR as Service Registry
    participant BR as Billing Rules
    participant DB as TimescaleDB
    
    %% Event ingestion
    Note over C,DB: Event Ingestion Flow
    C->>+AG: POST /api/v1/events
    AG->>AG: Validate API key & rate limits
    AG->>AG: Validate event structure
    AG->>AG: Generate event_id & request_id
    AG->>+R: lpush('usage_events', event_json)
    R-->>-AG: OK
    AG-->>-C: 200 {event_id, success}
    
    %% Async processing
    Note over R,DB: Asynchronous Processing
    EP->>+R: brpop('usage_events', timeout=30)
    R-->>-EP: event_data
    
    %% Event enrichment
    EP->>EP: Deserialize event
    EP->>EP: Validate required fields
    EP->>+SR: Get service configuration
    SR-->>-EP: Service config & enrichment rules
    EP->>EP: Apply enrichment rules
    EP->>EP: Calculate derived metrics
    
    %% Billing calculation  
    EP->>+BR: Get billing rules for service/provider
    BR-->>-EP: Billing rule configuration
    EP->>EP: Calculate event cost
    EP->>EP: Set status = 'completed'
    
    %% Storage
    EP->>+DB: INSERT/UPSERT usage_event
    DB-->>-EP: Success
    
    %% Error handling path
    Note over EP,R: Error Handling (if processing fails)
    EP->>EP: Set status = 'failed', increment retry_count
    alt retry_count < 3
        EP->>+R: lpush('usage_events', failed_event)
        R-->>-EP: Queued for retry
    else retry_count >= 3
        EP->>+R: lpush('dead_letter_events', failed_event)
        R-->>-EP: Moved to dead letter queue
    end
```

## 6. Query and Analytics Flow

### Purpose
Shows how analytical queries are processed and cached.

### Diagram
```mermaid
sequenceDiagram
    participant C as Client
    participant QS as Query Service
    participant RC as Redis Cache
    participant UA as Usage Aggregates
    participant UE as Usage Events
    
    %% Cache check
    Note over C,UE: Analytics Query Flow
    C->>+QS: GET /api/v1/usage/aggregate?period=day
    QS->>QS: Build cache key from parameters
    QS->>+RC: GET cache_key
    RC-->>-QS: cached_result OR null
    
    alt Cache Hit
        QS-->>C: 200 cached_data
    else Cache Miss
        %% Database query
        QS->>+UA: SELECT aggregated data
        UA-->>-QS: Aggregation records
        
        alt Aggregates Available
            QS->>QS: Format response data
        else No Aggregates (Real-time query needed)
            QS->>+UE: SELECT usage_events with GROUP BY
            UE-->>-QS: Raw aggregated results
            QS->>QS: Calculate metrics on-demand
        end
        
        %% Cache result
        QS->>+RC: SETEX cache_key, ttl=300, result
        RC-->>-QS: OK
        QS-->>-C: 200 analytics_data
    end
    
    %% Background aggregation
    Note over UA,UE: Background Aggregation Process
    participant AS as Aggregation Service
    
    loop Every 5 minutes
        AS->>AS: Identify time periods to aggregate
        AS->>+UE: SELECT events for aggregation window
        UE-->>-AS: Event data
        AS->>AS: Calculate aggregated metrics
        AS->>+UA: UPSERT aggregation records
        UA-->>-AS: Success
    end
```

## 7. Technology Stack Summary

### Core Technologies
- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async/await support)
- **Database**: PostgreSQL 14 with TimescaleDB extension
- **Cache/Queue**: Redis 7
- **HTTP Client**: httpx (async)
- **ORM**: SQLAlchemy 2.0 with async support

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose (dev) / Kubernetes (prod)
- **Load Balancer**: Nginx
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured logging with structlog

### Development & Testing
- **Testing**: pytest with async support
- **Code Quality**: Black, isort, mypy
- **Database Migrations**: Alembic
- **Environment**: python-dotenv for configuration

## 8. Key Architectural Decisions

### Event-Driven Architecture
- **Decision**: Use Redis queue for async event processing
- **Rationale**: Decouples ingestion from processing, enables horizontal scaling
- **Trade-offs**: Eventual consistency, requires reliable queue management

### Time-Series Database
- **Decision**: PostgreSQL with TimescaleDB for time-series data
- **Rationale**: Optimized for time-based queries, familiar SQL interface
- **Trade-offs**: Single database type vs. polyglot persistence

### Pre-Aggregation Strategy
- **Decision**: Background service for pre-computed summaries
- **Rationale**: Fast query response times for analytical queries
- **Trade-offs**: Storage overhead vs. query performance

### Multi-Tenant Design
- **Decision**: Shared database with tenant isolation
- **Rationale**: Cost efficiency, easier operations
- **Trade-offs**: Shared infrastructure vs. complete isolation

### SDK-First Approach
- **Decision**: Comprehensive client SDK with batching
- **Rationale**: Developer experience, reduced API calls
- **Trade-offs**: SDK complexity vs. direct API usage

## 9. Future Architecture Considerations

### Scalability Improvements
- **Horizontal Partitioning**: Shard by tenant_id for very large scales
- **Read Replicas**: Geographic distribution for global deployments
- **Event Streaming**: Kafka for higher throughput scenarios

### Advanced Analytics
- **Real-time Stream Processing**: Apache Flink for instant aggregations
- **Machine Learning**: Usage prediction and anomaly detection
- **Data Warehouse**: Export to analytical databases for complex BI

### Operational Excellence  
- **Circuit Breakers**: Resilience patterns for service interactions
- **Distributed Tracing**: OpenTelemetry for request tracing
- **Chaos Engineering**: Proactive reliability testing

## 10. Maintenance and Operational Guidelines

### Database Maintenance
- **Partitioning**: Automatic time-based partitioning in TimescaleDB
- **Data Retention**: Configurable event retention policies
- **Index Management**: Regular VACUUM and ANALYZE operations

### Monitoring Alerts
- **SLI/SLO Definition**: 99.9% availability, <100ms p95 latency
- **Key Metrics**: Queue depth, processing lag, error rates
- **Business Metrics**: Event ingestion rate, tenant usage patterns

### Backup and Recovery
- **Database Backups**: Automated daily backups with point-in-time recovery
- **Configuration Backup**: Infrastructure as code approach
- **Disaster Recovery**: Multi-region deployment capabilities

---

*This architecture documentation is living document that should be updated as the system evolves. Last updated: 2025-09-11*