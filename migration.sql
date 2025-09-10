BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;;

CREATE TABLE tenants (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    contact_email VARCHAR(255), 
    settings JSONB NOT NULL, 
    rate_limits JSONB, 
    usage_quotas JSONB, 
    billing_email VARCHAR(255), 
    billing_settings JSONB, 
    is_active BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (tenant_id)
);

CREATE INDEX ix_tenants_created_at ON tenants (created_at);

CREATE INDEX ix_tenants_id ON tenants (id);

CREATE INDEX ix_tenants_is_active ON tenants (is_active);

CREATE INDEX ix_tenants_tenant_id ON tenants (tenant_id);

CREATE TABLE service_registry (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    service_type VARCHAR(50) NOT NULL, 
    service_name VARCHAR(255) NOT NULL, 
    description TEXT, 
    providers JSONB NOT NULL, 
    required_fields JSONB NOT NULL, 
    optional_fields JSONB NOT NULL, 
    billing_config JSONB NOT NULL, 
    aggregation_rules JSONB NOT NULL, 
    validation_schema JSONB, 
    is_active BOOLEAN NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_service_registry_type UNIQUE (service_type)
);

CREATE INDEX ix_service_registry_created_at ON service_registry (created_at);

CREATE INDEX ix_service_registry_id ON service_registry (id);

CREATE INDEX ix_service_registry_is_active ON service_registry (is_active);

CREATE INDEX ix_service_registry_service_type ON service_registry (service_type);

CREATE TABLE billing_rules (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    service_type VARCHAR(50) NOT NULL, 
    provider VARCHAR(255) NOT NULL, 
    model_or_tier VARCHAR(255), 
    billing_unit VARCHAR(50) NOT NULL, 
    rate_per_unit FLOAT NOT NULL, 
    tiered_rates JSONB, 
    minimum_charge FLOAT, 
    calculation_method VARCHAR(50) NOT NULL, 
    calculation_expression TEXT, 
    effective_from TIMESTAMP WITH TIME ZONE NOT NULL, 
    effective_until TIMESTAMP WITH TIME ZONE, 
    is_active BOOLEAN NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_billing_rules_created_at ON billing_rules (created_at);

CREATE INDEX ix_billing_rules_id ON billing_rules (id);

CREATE INDEX ix_billing_rules_active ON billing_rules (is_active);

CREATE INDEX ix_billing_rules_effective ON billing_rules (effective_from, effective_until);

CREATE INDEX ix_billing_rules_service_provider ON billing_rules (service_type, provider);

CREATE TABLE usage_events (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    metadata JSONB, 
    tags JSONB, 
    event_id UUID NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    user_id VARCHAR(255) NOT NULL, 
    service_type VARCHAR(50) NOT NULL, 
    service_provider VARCHAR(255) NOT NULL, 
    event_type VARCHAR(255) NOT NULL, 
    metrics JSONB, 
    billing_info JSONB, 
    status VARCHAR(50) NOT NULL, 
    error_message VARCHAR(1000), 
    retry_count INTEGER NOT NULL, 
    total_cost DECIMAL(10, 6), 
    session_id VARCHAR(255), 
    request_id VARCHAR(255), 
    PRIMARY KEY (id), 
    UNIQUE (event_id)
);

CREATE INDEX ix_usage_events_created_at ON usage_events (created_at);

CREATE INDEX ix_usage_events_event_id ON usage_events (event_id);

CREATE INDEX ix_usage_events_id ON usage_events (id);

CREATE INDEX ix_usage_events_service_provider ON usage_events (service_provider);

CREATE INDEX ix_usage_events_service_type ON usage_events (service_type);

CREATE INDEX ix_usage_events_session_id ON usage_events (session_id);

CREATE INDEX ix_usage_events_status ON usage_events (status);

CREATE INDEX ix_usage_events_tenant_id ON usage_events (tenant_id);

CREATE INDEX ix_usage_events_timestamp ON usage_events (timestamp);

CREATE INDEX ix_usage_events_user_id ON usage_events (user_id);

CREATE INDEX ix_usage_events_request_id ON usage_events (request_id);

CREATE INDEX ix_usage_events_tenant_timestamp ON usage_events (tenant_id, timestamp);

CREATE INDEX ix_usage_events_user_timestamp ON usage_events (user_id, timestamp);

CREATE INDEX ix_usage_events_service_timestamp ON usage_events (service_type, timestamp);

CREATE INDEX ix_usage_events_provider_timestamp ON usage_events (service_provider, timestamp);

CREATE INDEX ix_usage_events_tenant_service ON usage_events (tenant_id, service_type);

CREATE INDEX ix_usage_events_tenant_user ON usage_events (tenant_id, user_id);

CREATE INDEX ix_usage_events_metadata_gin ON usage_events USING gin (metadata);

CREATE INDEX ix_usage_events_metrics_gin ON usage_events USING gin (metrics);

CREATE INDEX ix_usage_events_billing_gin ON usage_events USING gin (billing_info);

CREATE INDEX ix_usage_events_tags_gin ON usage_events USING gin (tags);

CREATE INDEX ix_usage_events_pending ON usage_events (status) WHERE status = 'pending';

CREATE INDEX ix_usage_events_failed ON usage_events (status) WHERE status = 'failed';

CREATE TABLE usage_aggregates (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    period_start TIMESTAMP WITH TIME ZONE NOT NULL, 
    period_end TIMESTAMP WITH TIME ZONE NOT NULL, 
    period_type VARCHAR(20) NOT NULL, 
    service_type VARCHAR(50), 
    service_provider VARCHAR(255), 
    user_id VARCHAR(255), 
    event_count INTEGER NOT NULL, 
    unique_users INTEGER NOT NULL, 
    total_cost DECIMAL(12, 6), 
    aggregated_metrics JSONB, 
    avg_latency_ms DECIMAL(10, 2), 
    p95_latency_ms DECIMAL(10, 2), 
    error_count INTEGER NOT NULL, 
    error_rate DECIMAL(5, 4), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_usage_aggregates_unique UNIQUE (tenant_id, period_start, period_type, service_type, service_provider, user_id)
);

CREATE INDEX ix_usage_aggregates_created_at ON usage_aggregates (created_at);

CREATE INDEX ix_usage_aggregates_id ON usage_aggregates (id);

CREATE INDEX ix_usage_aggregates_period_end ON usage_aggregates (period_end);

CREATE INDEX ix_usage_aggregates_period_start ON usage_aggregates (period_start);

CREATE INDEX ix_usage_aggregates_period_type ON usage_aggregates (period_type);

CREATE INDEX ix_usage_aggregates_service_provider ON usage_aggregates (service_provider);

CREATE INDEX ix_usage_aggregates_service_type ON usage_aggregates (service_type);

CREATE INDEX ix_usage_aggregates_tenant_id ON usage_aggregates (tenant_id);

CREATE INDEX ix_usage_aggregates_user_id ON usage_aggregates (user_id);

CREATE INDEX ix_usage_agg_tenant_period ON usage_aggregates (tenant_id, period_start, period_type);

CREATE INDEX ix_usage_agg_service_period ON usage_aggregates (service_type, period_start, period_type);

CREATE INDEX ix_usage_agg_user_period ON usage_aggregates (user_id, period_start, period_type);

CREATE INDEX ix_usage_agg_metrics_gin ON usage_aggregates USING gin (aggregated_metrics);

CREATE TABLE billing_summaries (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    billing_month INTEGER NOT NULL, 
    billing_year INTEGER NOT NULL, 
    total_cost DECIMAL(12, 2) NOT NULL, 
    cost_by_service JSONB NOT NULL, 
    cost_by_user JSONB NOT NULL, 
    total_events INTEGER NOT NULL, 
    active_users INTEGER NOT NULL, 
    is_finalized BOOLEAN NOT NULL, 
    finalized_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_billing_summary_unique UNIQUE (tenant_id, billing_year, billing_month)
);

CREATE INDEX ix_billing_summaries_billing_month ON billing_summaries (billing_month);

CREATE INDEX ix_billing_summaries_billing_year ON billing_summaries (billing_year);

CREATE INDEX ix_billing_summaries_created_at ON billing_summaries (created_at);

CREATE INDEX ix_billing_summaries_id ON billing_summaries (id);

CREATE INDEX ix_billing_summaries_tenant_id ON billing_summaries (tenant_id);

CREATE INDEX ix_billing_summary_period ON billing_summaries (billing_year, billing_month);

CREATE TABLE alert_configurations (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    alert_type VARCHAR(50) NOT NULL, 
    description TEXT, 
    service_type VARCHAR(50), 
    service_provider VARCHAR(255), 
    user_id VARCHAR(255), 
    threshold_value DECIMAL(12, 6) NOT NULL, 
    threshold_operator VARCHAR(10) NOT NULL, 
    time_window_minutes INTEGER NOT NULL, 
    evaluation_frequency_minutes INTEGER NOT NULL, 
    minimum_data_points INTEGER NOT NULL, 
    notification_channels JSONB NOT NULL, 
    notification_settings JSONB NOT NULL, 
    cooldown_minutes INTEGER NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    metadata JSONB, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_alert_configurations_alert_type ON alert_configurations (alert_type);

CREATE INDEX ix_alert_configurations_created_at ON alert_configurations (created_at);

CREATE INDEX ix_alert_configurations_id ON alert_configurations (id);

CREATE INDEX ix_alert_configurations_tenant_id ON alert_configurations (tenant_id);

CREATE INDEX ix_alert_configurations_user_id ON alert_configurations (user_id);

CREATE INDEX ix_alert_config_active ON alert_configurations (is_active);

CREATE INDEX ix_alert_config_service ON alert_configurations (service_type, service_provider);

CREATE INDEX ix_alert_config_tenant_type ON alert_configurations (tenant_id, alert_type);

CREATE TABLE alert_instances (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    alert_config_id VARCHAR(36) NOT NULL, 
    alert_type VARCHAR(50) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    acknowledged_at TIMESTAMP WITH TIME ZONE, 
    acknowledged_by VARCHAR(255), 
    current_value DECIMAL(12, 6) NOT NULL, 
    threshold_value DECIMAL(12, 6) NOT NULL, 
    service_type VARCHAR(50), 
    service_provider VARCHAR(255), 
    user_id VARCHAR(255), 
    context_data JSONB, 
    notifications_sent JSONB NOT NULL, 
    last_notification_at TIMESTAMP WITH TIME ZONE, 
    notification_count INTEGER NOT NULL, 
    resolution_notes TEXT, 
    auto_resolved BOOLEAN NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_alert_instances_alert_type ON alert_instances (alert_type);

CREATE INDEX ix_alert_instances_created_at ON alert_instances (created_at);

CREATE INDEX ix_alert_instances_id ON alert_instances (id);

CREATE INDEX ix_alert_instances_status ON alert_instances (status);

CREATE INDEX ix_alert_instances_tenant_id ON alert_instances (tenant_id);

CREATE INDEX ix_alert_instances_triggered_at ON alert_instances (triggered_at);

CREATE INDEX ix_alert_instances_user_id ON alert_instances (user_id);

CREATE INDEX ix_alert_instance_config ON alert_instances (alert_config_id);

CREATE INDEX ix_alert_instance_service ON alert_instances (service_type, service_provider);

CREATE INDEX ix_alert_instance_tenant_status ON alert_instances (tenant_id, status);

SELECT create_hypertable(
                'usage_events',
                'timestamp',
                chunk_time_interval => INTERVAL '1 month',
                if_not_exists => TRUE
            );;

SELECT add_retention_policy(
                'usage_events',
                INTERVAL '365 days',
                if_not_exists => TRUE
            );;

INSERT INTO alembic_version (version_num) VALUES ('001_initial') RETURNING alembic_version.version_num;

COMMIT;

