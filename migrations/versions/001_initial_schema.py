"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    
    # Create tenants table
    op.create_table('tenants',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('rate_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('usage_quotas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('billing_email', sa.String(length=255), nullable=True),
    sa.Column('billing_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id')
    )
    op.create_index(op.f('ix_tenants_created_at'), 'tenants', ['created_at'], unique=False)
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_is_active'), 'tenants', ['is_active'], unique=False)
    op.create_index(op.f('ix_tenants_tenant_id'), 'tenants', ['tenant_id'], unique=False)

    # Create service_registry table
    op.create_table('service_registry',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('service_type', sa.String(length=50), nullable=False),
    sa.Column('service_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('providers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('required_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('optional_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('billing_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('aggregation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('validation_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service_type', name='uq_service_registry_type')
    )
    op.create_index(op.f('ix_service_registry_created_at'), 'service_registry', ['created_at'], unique=False)
    op.create_index(op.f('ix_service_registry_id'), 'service_registry', ['id'], unique=False)
    op.create_index(op.f('ix_service_registry_is_active'), 'service_registry', ['is_active'], unique=False)
    op.create_index(op.f('ix_service_registry_service_type'), 'service_registry', ['service_type'], unique=False)

    # Create billing_rules table
    op.create_table('billing_rules',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('service_type', sa.String(length=50), nullable=False),
    sa.Column('provider', sa.String(length=255), nullable=False),
    sa.Column('model_or_tier', sa.String(length=255), nullable=True),
    sa.Column('billing_unit', sa.String(length=50), nullable=False),
    sa.Column('rate_per_unit', sa.Float(), nullable=False),
    sa.Column('tiered_rates', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('minimum_charge', sa.Float(), nullable=True),
    sa.Column('calculation_method', sa.String(length=50), nullable=False),
    sa.Column('calculation_expression', sa.Text(), nullable=True),
    sa.Column('effective_from', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('effective_until', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_rules_created_at'), 'billing_rules', ['created_at'], unique=False)
    op.create_index(op.f('ix_billing_rules_id'), 'billing_rules', ['id'], unique=False)
    op.create_index('ix_billing_rules_active', 'billing_rules', ['is_active'], unique=False)
    op.create_index('ix_billing_rules_effective', 'billing_rules', ['effective_from', 'effective_until'], unique=False)
    op.create_index('ix_billing_rules_service_provider', 'billing_rules', ['service_type', 'provider'], unique=False)

    # Create usage_events table
    op.create_table('usage_events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('user_id', sa.String(length=255), nullable=False),
    sa.Column('service_type', sa.String(length=50), nullable=False),
    sa.Column('service_provider', sa.String(length=255), nullable=False),
    sa.Column('event_type', sa.String(length=255), nullable=False),
    sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('billing_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('error_message', sa.String(length=1000), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('total_cost', sa.DECIMAL(precision=10, scale=6), nullable=True),
    sa.Column('session_id', sa.String(length=255), nullable=True),
    sa.Column('request_id', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id')
    )
    
    # Create indexes for usage_events
    op.create_index(op.f('ix_usage_events_created_at'), 'usage_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_usage_events_event_id'), 'usage_events', ['event_id'], unique=False)
    op.create_index(op.f('ix_usage_events_id'), 'usage_events', ['id'], unique=False)
    op.create_index(op.f('ix_usage_events_service_provider'), 'usage_events', ['service_provider'], unique=False)
    op.create_index(op.f('ix_usage_events_service_type'), 'usage_events', ['service_type'], unique=False)
    op.create_index(op.f('ix_usage_events_session_id'), 'usage_events', ['session_id'], unique=False)
    op.create_index(op.f('ix_usage_events_status'), 'usage_events', ['status'], unique=False)
    op.create_index(op.f('ix_usage_events_tenant_id'), 'usage_events', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_usage_events_timestamp'), 'usage_events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_usage_events_user_id'), 'usage_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_usage_events_request_id'), 'usage_events', ['request_id'], unique=False)
    
    # Composite indexes
    op.create_index('ix_usage_events_tenant_timestamp', 'usage_events', ['tenant_id', 'timestamp'], unique=False)
    op.create_index('ix_usage_events_user_timestamp', 'usage_events', ['user_id', 'timestamp'], unique=False)
    op.create_index('ix_usage_events_service_timestamp', 'usage_events', ['service_type', 'timestamp'], unique=False)
    op.create_index('ix_usage_events_provider_timestamp', 'usage_events', ['service_provider', 'timestamp'], unique=False)
    op.create_index('ix_usage_events_tenant_service', 'usage_events', ['tenant_id', 'service_type'], unique=False)
    op.create_index('ix_usage_events_tenant_user', 'usage_events', ['tenant_id', 'user_id'], unique=False)
    
    # GIN indexes for JSONB columns
    op.create_index('ix_usage_events_metadata_gin', 'usage_events', ['metadata'], unique=False, postgresql_using='gin')
    op.create_index('ix_usage_events_metrics_gin', 'usage_events', ['metrics'], unique=False, postgresql_using='gin')
    op.create_index('ix_usage_events_billing_gin', 'usage_events', ['billing_info'], unique=False, postgresql_using='gin')
    op.create_index('ix_usage_events_tags_gin', 'usage_events', ['tags'], unique=False, postgresql_using='gin')
    
    # Partial indexes
    op.create_index('ix_usage_events_pending', 'usage_events', ['status'], unique=False, postgresql_where="status = 'pending'")
    op.create_index('ix_usage_events_failed', 'usage_events', ['status'], unique=False, postgresql_where="status = 'failed'")

    # Create usage_aggregates table
    op.create_table('usage_aggregates',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('period_type', sa.String(length=20), nullable=False),
    sa.Column('service_type', sa.String(length=50), nullable=True),
    sa.Column('service_provider', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('event_count', sa.Integer(), nullable=False),
    sa.Column('unique_users', sa.Integer(), nullable=False),
    sa.Column('total_cost', sa.DECIMAL(precision=12, scale=6), nullable=True),
    sa.Column('aggregated_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('avg_latency_ms', sa.DECIMAL(precision=10, scale=2), nullable=True),
    sa.Column('p95_latency_ms', sa.DECIMAL(precision=10, scale=2), nullable=True),
    sa.Column('error_count', sa.Integer(), nullable=False),
    sa.Column('error_rate', sa.DECIMAL(precision=5, scale=4), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'period_start', 'period_type', 'service_type', 'service_provider', 'user_id', name='uq_usage_aggregates_unique')
    )
    op.create_index(op.f('ix_usage_aggregates_created_at'), 'usage_aggregates', ['created_at'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_id'), 'usage_aggregates', ['id'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_period_end'), 'usage_aggregates', ['period_end'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_period_start'), 'usage_aggregates', ['period_start'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_period_type'), 'usage_aggregates', ['period_type'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_service_provider'), 'usage_aggregates', ['service_provider'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_service_type'), 'usage_aggregates', ['service_type'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_tenant_id'), 'usage_aggregates', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_usage_aggregates_user_id'), 'usage_aggregates', ['user_id'], unique=False)
    
    # Composite indexes for aggregates
    op.create_index('ix_usage_agg_tenant_period', 'usage_aggregates', ['tenant_id', 'period_start', 'period_type'], unique=False)
    op.create_index('ix_usage_agg_service_period', 'usage_aggregates', ['service_type', 'period_start', 'period_type'], unique=False)
    op.create_index('ix_usage_agg_user_period', 'usage_aggregates', ['user_id', 'period_start', 'period_type'], unique=False)
    op.create_index('ix_usage_agg_metrics_gin', 'usage_aggregates', ['aggregated_metrics'], unique=False, postgresql_using='gin')

    # Create billing_summaries table
    op.create_table('billing_summaries',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('billing_month', sa.Integer(), nullable=False),
    sa.Column('billing_year', sa.Integer(), nullable=False),
    sa.Column('total_cost', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('cost_by_service', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cost_by_user', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('total_events', sa.Integer(), nullable=False),
    sa.Column('active_users', sa.Integer(), nullable=False),
    sa.Column('is_finalized', sa.Boolean(), nullable=False),
    sa.Column('finalized_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'billing_year', 'billing_month', name='uq_billing_summary_unique')
    )
    op.create_index(op.f('ix_billing_summaries_billing_month'), 'billing_summaries', ['billing_month'], unique=False)
    op.create_index(op.f('ix_billing_summaries_billing_year'), 'billing_summaries', ['billing_year'], unique=False)
    op.create_index(op.f('ix_billing_summaries_created_at'), 'billing_summaries', ['created_at'], unique=False)
    op.create_index(op.f('ix_billing_summaries_id'), 'billing_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_billing_summaries_tenant_id'), 'billing_summaries', ['tenant_id'], unique=False)
    op.create_index('ix_billing_summary_period', 'billing_summaries', ['billing_year', 'billing_month'], unique=False)

    # Create alert_configurations table
    op.create_table('alert_configurations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('alert_type', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('service_type', sa.String(length=50), nullable=True),
    sa.Column('service_provider', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('threshold_value', sa.DECIMAL(precision=12, scale=6), nullable=False),
    sa.Column('threshold_operator', sa.String(length=10), nullable=False),
    sa.Column('time_window_minutes', sa.Integer(), nullable=False),
    sa.Column('evaluation_frequency_minutes', sa.Integer(), nullable=False),
    sa.Column('minimum_data_points', sa.Integer(), nullable=False),
    sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('notification_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cooldown_minutes', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_configurations_alert_type'), 'alert_configurations', ['alert_type'], unique=False)
    op.create_index(op.f('ix_alert_configurations_created_at'), 'alert_configurations', ['created_at'], unique=False)
    op.create_index(op.f('ix_alert_configurations_id'), 'alert_configurations', ['id'], unique=False)
    op.create_index(op.f('ix_alert_configurations_tenant_id'), 'alert_configurations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_alert_configurations_user_id'), 'alert_configurations', ['user_id'], unique=False)
    op.create_index('ix_alert_config_active', 'alert_configurations', ['is_active'], unique=False)
    op.create_index('ix_alert_config_service', 'alert_configurations', ['service_type', 'service_provider'], unique=False)
    op.create_index('ix_alert_config_tenant_type', 'alert_configurations', ['tenant_id', 'alert_type'], unique=False)

    # Create alert_instances table
    op.create_table('alert_instances',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('alert_config_id', sa.String(length=36), nullable=False),
    sa.Column('alert_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('triggered_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('acknowledged_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('acknowledged_by', sa.String(length=255), nullable=True),
    sa.Column('current_value', sa.DECIMAL(precision=12, scale=6), nullable=False),
    sa.Column('threshold_value', sa.DECIMAL(precision=12, scale=6), nullable=False),
    sa.Column('service_type', sa.String(length=50), nullable=True),
    sa.Column('service_provider', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('notifications_sent', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('last_notification_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('notification_count', sa.Integer(), nullable=False),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.Column('auto_resolved', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_instances_alert_type'), 'alert_instances', ['alert_type'], unique=False)
    op.create_index(op.f('ix_alert_instances_created_at'), 'alert_instances', ['created_at'], unique=False)
    op.create_index(op.f('ix_alert_instances_id'), 'alert_instances', ['id'], unique=False)
    op.create_index(op.f('ix_alert_instances_status'), 'alert_instances', ['status'], unique=False)
    op.create_index(op.f('ix_alert_instances_tenant_id'), 'alert_instances', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_alert_instances_triggered_at'), 'alert_instances', ['triggered_at'], unique=False)
    op.create_index(op.f('ix_alert_instances_user_id'), 'alert_instances', ['user_id'], unique=False)
    op.create_index('ix_alert_instance_config', 'alert_instances', ['alert_config_id'], unique=False)
    op.create_index('ix_alert_instance_service', 'alert_instances', ['service_type', 'service_provider'], unique=False)
    op.create_index('ix_alert_instance_tenant_status', 'alert_instances', ['tenant_id', 'status'], unique=False)

    # Convert usage_events to hypertable (TimescaleDB)
    try:
        op.execute("""
            SELECT create_hypertable(
                'usage_events',
                'timestamp',
                chunk_time_interval => INTERVAL '1 month',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        # TimescaleDB might not be available
        pass
    
    # Add retention policy (TimescaleDB)
    try:
        op.execute("""
            SELECT add_retention_policy(
                'usage_events',
                INTERVAL '365 days',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        # TimescaleDB might not be available
        pass


def downgrade() -> None:
    op.drop_table('alert_instances')
    op.drop_table('alert_configurations')
    op.drop_table('billing_summaries')
    op.drop_table('usage_aggregates')
    op.drop_table('usage_events')
    op.drop_table('billing_rules')
    op.drop_table('service_registry')
    op.drop_table('tenants')