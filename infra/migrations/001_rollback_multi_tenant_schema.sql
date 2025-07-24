-- Rollback Migration: Remove multi-tenant FIFO COGS schema
-- Version: 001
-- Description: Drops all tables and types created in 001_create_multi_tenant_schema.sql

-- Drop triggers first
DROP TRIGGER IF EXISTS update_cogs_runs_updated_at ON cogs_runs;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS validation_errors;
DROP TABLE IF EXISTS uploaded_files;
DROP TABLE IF EXISTS cogs_summary;
DROP TABLE IF EXISTS cogs_attribution_details;
DROP TABLE IF EXISTS cogs_attribution;
DROP TABLE IF EXISTS inventory_snapshots;
DROP TABLE IF EXISTS inventory_movements;
DROP TABLE IF EXISTS cogs_runs;

-- Drop enum types
DROP TYPE IF EXISTS movement_type;
DROP TYPE IF EXISTS run_status;

-- Note: We don't drop the uuid-ossp extension as it might be used by other schemas