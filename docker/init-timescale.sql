-- Initialize TimescaleDB extensions and optimizations
-- This script runs during database initialization

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create database user and grant permissions
-- (These are already created by the POSTGRES_* env vars, but included for completeness)
-- CREATE USER usage_user WITH ENCRYPTED PASSWORD 'usage_password';
-- GRANT ALL PRIVILEGES ON DATABASE usage_tracking TO usage_user;

-- Set some optimizations for TimescaleDB
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();

-- Create a function to automatically convert tables to hypertables
CREATE OR REPLACE FUNCTION auto_create_hypertable()
RETURNS event_trigger AS $$
DECLARE
    table_name text;
    schema_name text;
BEGIN
    SELECT schemaname, tablename INTO schema_name, table_name
    FROM pg_tables 
    WHERE tablename = TG_TABLE_NAME;
    
    -- Only convert usage_events table
    IF table_name = 'usage_events' THEN
        PERFORM create_hypertable(
            format('%I.%I', schema_name, table_name),
            'timestamp',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create event trigger (will be activated after table creation)
-- CREATE EVENT TRIGGER auto_hypertable_trigger 
-- ON ddl_command_end 
-- WHEN TAG IN ('CREATE TABLE') 
-- EXECUTE FUNCTION auto_create_hypertable();