# Docker Compose Configuration Documentation

## Overview

This Docker Compose configuration orchestrates a comprehensive usage tracking system with microservices architecture, monitoring, and logging capabilities. The system includes core services, databases, load balancing, and optional monitoring stack.

## Key Functionality

### Microservices Architecture
- **API Gateway (Port 8000)**: Main HTTP entry point for client requests
- **Event Processor**: Asynchronous background processing of usage events
- **Query Service (Port 8002)**: Dedicated read operations and data retrieval
- **Aggregation Service**: Real-time data aggregation and analytics processing
- **Database Migration Service**: Automated schema management with Alembic

### Data Storage & Caching
- **TimescaleDB Integration**: PostgreSQL with time-series extensions for efficient usage data storage
- **Redis Caching**: High-performance caching layer with LRU eviction policy
- **Persistent Volumes**: Data persistence across container restarts

### Load Balancing & High Availability
- **Nginx Load Balancer**: Production-grade reverse proxy and load distribution
- **Health Checks**: Comprehensive service monitoring and automatic failure detection
- **Service Dependencies**: Orchestrated startup sequence ensuring system stability

### Monitoring & Observability
- **Prometheus Metrics**: System and application metrics collection
- **Grafana Dashboards**: Real-time visualization and alerting
- **Loki Log Aggregation**: Centralized logging with structured log storage
- **Promtail Collection**: Automatic log collection from all Docker containers

## Notable Features

### Deployment Flexibility
- **Profile-Based Deployment**: Separate profiles for development, production, and monitoring
- **Resource Management**: CPU and memory limits (512MB RAM, 0.5 CPU per service)
- **Horizontal Scaling**: Support for scaling individual services (e.g., multiple API gateways)

### Security & Network Isolation
- **Custom Bridge Network**: Isolated network (172.20.0.0/16) for inter-service communication
- **Internal Services**: Event processor and aggregation service not exposed to external network
- **Health Check Integration**: Proactive service monitoring and automatic restart capabilities

### Configuration Management
- **Environment Variable Configuration**: Centralized configuration via environment variables
- **External Configuration Files**: Support for custom configurations (nginx.conf, prometheus.yml, etc.)
- **Database Initialization**: Automated TimescaleDB setup with custom SQL scripts

### Development & Operations Support
- **Hot Reloading**: Development-friendly container configuration
- **Log Management**: Structured logging with configurable log levels
- **Backup & Recovery**: Volume-based data persistence and backup strategies
- **Rolling Updates**: Support for zero-downtime deployments

## Architecture

The system follows a microservices pattern with the following components:

### Core Services
- **API Gateway**: Main entry point handling HTTP requests
- **Event Processor**: Processes usage events asynchronously
- **Query Service**: Dedicated service for data queries
- **Aggregation Service**: Handles data aggregation tasks
- **Database Migration**: Manages schema migrations

### Infrastructure Services
- **PostgreSQL with TimescaleDB**: Time-series database for usage data
- **Redis**: Caching and message queue
- **Nginx**: Load balancer (production profile)

### Monitoring Stack (Optional)
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboard
- **Loki**: Log aggregation
- **Promtail**: Log collection agent

## Service Details

### Database Layer

#### PostgreSQL with TimescaleDB
```yaml
postgres:
  image: timescale/timescaledb:latest-pg14
  container_name: usage_postgres
  ports: ["5432:5432"]
```
- **Purpose**: Primary database with time-series extensions
- **Database**: `usage_tracking`
- **User**: `usage_user`
- **Features**: TimescaleDB for efficient time-series data handling
- **Health Check**: PostgreSQL readiness check
- **Volume**: Persistent data storage

#### Redis
```yaml
redis:
  image: redis:7-alpine
  container_name: usage_redis
  ports: ["6379:6379"]
```
- **Purpose**: Caching and message queue
- **Configuration**: 512MB max memory with LRU eviction
- **Features**: Append-only file persistence
- **Health Check**: Redis ping command

### Application Services

#### API Gateway
```yaml
api_gateway:
  ports: ["8000:8000"]
  dockerfile: Dockerfile.api_gateway
```
- **Purpose**: Main HTTP API endpoint
- **Port**: 8000
- **Health Check**: HTTP health endpoint
- **Resources**: 512MB RAM, 0.5 CPU cores
- **Dependencies**: PostgreSQL and Redis

#### Event Processor
```yaml
event_processor:
  dockerfile: Dockerfile.event_processor
```
- **Purpose**: Asynchronous event processing
- **No exposed ports**: Internal service
- **Health Check**: Process existence check
- **Resources**: 512MB RAM, 0.5 CPU cores
- **Dependencies**: PostgreSQL and Redis

#### Query Service
```yaml
query_service:
  ports: ["8002:8002"]
  dockerfile: Dockerfile.query_service
```
- **Purpose**: Dedicated query handling service
- **Port**: 8002
- **Health Check**: HTTP health endpoint
- **Resources**: 512MB RAM, 0.5 CPU cores
- **Dependencies**: PostgreSQL and Redis

#### Aggregation Service
```yaml
aggregation_service:
  dockerfile: Dockerfile.aggregation_service
```
- **Purpose**: Data aggregation and analytics
- **No exposed ports**: Internal service
- **Health Check**: Process existence check
- **Resources**: 512MB RAM, 0.5 CPU cores
- **Dependencies**: PostgreSQL

#### Database Migration
```yaml
migrate:
  command: ["python", "-m", "alembic", "upgrade", "head"]
  restart: "no"
```
- **Purpose**: Database schema migrations
- **Execution**: Run once and exit
- **Dependencies**: PostgreSQL
- **Uses**: Alembic for migrations

### Load Balancer (Production Profile)

#### Nginx
```yaml
nginx:
  image: nginx:alpine
  ports: ["80:80"]
  profiles: ["production"]
```
- **Purpose**: Load balancing and reverse proxy
- **Configuration**: Custom nginx.conf
- **Profile**: Only runs in production mode
- **Health Check**: HTTP health endpoint

### Monitoring Stack (Monitoring Profile)

#### Prometheus
```yaml
prometheus:
  image: prom/prometheus:latest
  ports: ["9090:9090"]
  profiles: ["monitoring"]
```
- **Purpose**: Metrics collection and storage
- **Configuration**: Custom prometheus.yml
- **Retention**: 200 hours
- **Web Interface**: Port 9090

#### Grafana
```yaml
grafana:
  image: grafana/grafana:latest
  ports: ["3000:3000"]
  profiles: ["monitoring"]
```
- **Purpose**: Visualization and dashboards
- **Default Credentials**: admin/admin
- **Dashboards**: Pre-configured via provisioning
- **Dependencies**: Prometheus and Loki

#### Loki
```yaml
loki:
  image: grafana/loki:2.9.0
  ports: ["3100:3100"]
  profiles: ["monitoring"]
```
- **Purpose**: Log aggregation
- **Configuration**: Custom loki.yml
- **Storage**: Persistent volume

#### Promtail
```yaml
promtail:
  image: grafana/promtail:2.9.0
  profiles: ["monitoring"]
```
- **Purpose**: Log collection from Docker containers
- **Configuration**: Custom promtail.yml
- **Access**: Docker socket and container logs

## Network Configuration

### Custom Network
```yaml
networks:
  usage_network:
    driver: bridge
    subnet: 172.20.0.0/16
```
- **Type**: Bridge network
- **Subnet**: 172.20.0.0/16
- **Purpose**: Isolated communication between services

## Volume Management

### Persistent Volumes
- **postgres_data**: Database files
- **redis_data**: Redis persistence
- **prometheus_data**: Metrics storage
- **grafana_data**: Dashboard configurations
- **loki_data**: Log storage

## Deployment Profiles

### Default Profile
- Core application services
- Database and cache
- Basic functionality

### Production Profile
```bash
docker-compose --profile production up
```
- Includes Nginx load balancer
- Production-ready configuration

### Monitoring Profile
```bash
docker-compose --profile monitoring up
```
- Includes full monitoring stack
- Prometheus, Grafana, Loki, Promtail

### Combined Profiles
```bash
docker-compose --profile production --profile monitoring up
```

## Environment Variables

### Common Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `LOG_LEVEL`: Logging verbosity (INFO)

### Service-Specific Variables
- `API_HOST`: API binding address (0.0.0.0)
- `API_PORT`: Service port numbers
- `GF_SECURITY_ADMIN_PASSWORD`: Grafana admin password

## Health Checks

All services include comprehensive health checks:
- **Database**: PostgreSQL readiness
- **Cache**: Redis ping
- **HTTP Services**: Health endpoints
- **Background Services**: Process checks

## Resource Limits

Application services are limited to:
- **Memory**: 512MB per service
- **CPU**: 0.5 cores per service

## Usage Commands

### Start Core Services
```bash
docker-compose up -d
```

### Start with Load Balancer
```bash
docker-compose --profile production up -d
```

### Start with Monitoring
```bash
docker-compose --profile monitoring up -d
```

### Start Everything
```bash
docker-compose --profile production --profile monitoring up -d
```

### View Logs
```bash
docker-compose logs -f [service_name]
```

### Scale Services
```bash
docker-compose up -d --scale api_gateway=3
```

## Service Dependencies

The dependency chain ensures proper startup order:
1. PostgreSQL and Redis (infrastructure)
2. Database migration
3. Application services (API Gateway, Event Processor, etc.)
4. Load balancer and monitoring (if enabled)

## Configuration Files

External configuration files required:
- `./docker/init-timescale.sql`: Database initialization
- `./docker/nginx.conf`: Nginx configuration
- `./docker/prometheus.yml`: Prometheus configuration
- `./docker/grafana/`: Grafana provisioning
- `./docker/loki/loki.yml`: Loki configuration
- `./docker/promtail/promtail.yml`: Promtail configuration

## Maintenance

### Backup
- Database: PostgreSQL dumps via pg_dump
- Configurations: Volume backups
- Metrics: Prometheus data export

### Updates
- Pull latest images: `docker-compose pull`
- Restart services: `docker-compose restart`
- View status: `docker-compose ps`

This configuration provides a production-ready, scalable usage tracking system with comprehensive monitoring and logging capabilities.