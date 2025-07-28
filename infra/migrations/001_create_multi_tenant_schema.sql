-- Migration: Create multi-tenant FIFO COGS schema
-- Version: 001
-- Description: Initial schema with tenant isolation for COGS calculations

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE run_status AS ENUM ('pending', 'running', 'completed', 'failed', 'rolled_back');
CREATE TYPE movement_type AS ENUM ('sale', 'return', 'adjustment', 'rollback');

-- Table: cogs_runs
-- Tracks each COGS calculation run per tenant
CREATE TABLE cogs_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    status run_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    input_file_id UUID,
    error_message TEXT,
    created_by VARCHAR(255),
    rollback_of_run_id UUID REFERENCES cogs_runs(run_id),
    
    -- Statistics
    total_sales_processed INTEGER DEFAULT 0,
    total_cogs_calculated DECIMAL(15,2) DEFAULT 0,
    validation_errors_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT chk_completed_at CHECK (
        (status IN ('completed', 'failed', 'rolled_back') AND completed_at IS NOT NULL) 
        OR status IN ('pending', 'running')
    )
);

CREATE INDEX idx_cogs_runs_tenant_id ON cogs_runs(tenant_id);
CREATE INDEX idx_cogs_runs_status ON cogs_runs(status);
CREATE INDEX idx_cogs_runs_tenant_status ON cogs_runs(tenant_id, status);

-- Table: inventory_movements
-- Audit trail of all inventory changes
CREATE TABLE inventory_movements (
    movement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL REFERENCES cogs_runs(run_id),
    lot_id VARCHAR(100) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    movement_type movement_type NOT NULL,
    quantity INTEGER NOT NULL, -- Positive for additions, negative for removals
    remaining_after INTEGER NOT NULL CHECK (remaining_after >= 0),
    unit_cost DECIMAL(10,2) NOT NULL,
    reference_id VARCHAR(100), -- Sale ID or other reference
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure quantity makes sense for movement type
    CONSTRAINT chk_movement_quantity CHECK (
        (movement_type = 'sale' AND quantity < 0) OR
        (movement_type = 'return' AND quantity > 0) OR
        (movement_type IN ('adjustment', 'rollback'))
    )
);

CREATE INDEX idx_movements_tenant_id ON inventory_movements(tenant_id);
CREATE INDEX idx_movements_run_id ON inventory_movements(run_id);
CREATE INDEX idx_movements_lot_id ON inventory_movements(tenant_id, lot_id);
CREATE INDEX idx_movements_sku ON inventory_movements(tenant_id, sku);

-- Table: inventory_snapshots
-- Point-in-time inventory state per run
CREATE TABLE inventory_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL REFERENCES cogs_runs(run_id),
    lot_id VARCHAR(100) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    remaining_quantity INTEGER NOT NULL CHECK (remaining_quantity >= 0),
    original_quantity INTEGER NOT NULL CHECK (original_quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    freight_cost_per_unit DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (freight_cost_per_unit >= 0),
    received_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure remaining doesn't exceed original
    CONSTRAINT chk_quantity_bounds CHECK (remaining_quantity <= original_quantity)
);

CREATE INDEX idx_snapshots_tenant_id ON inventory_snapshots(tenant_id);
CREATE INDEX idx_snapshots_run_id ON inventory_snapshots(run_id);
CREATE INDEX idx_snapshots_current ON inventory_snapshots(tenant_id, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_snapshots_lot ON inventory_snapshots(tenant_id, lot_id);

-- Table: cogs_attribution
-- Main COGS attribution records
CREATE TABLE cogs_attribution (
    attribution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL REFERENCES cogs_runs(run_id),
    sale_id VARCHAR(100) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    sale_date DATE NOT NULL,
    quantity_sold INTEGER NOT NULL CHECK (quantity_sold > 0),
    total_cogs DECIMAL(12,2) NOT NULL CHECK (total_cogs >= 0),
    average_unit_cost DECIMAL(10,4) NOT NULL CHECK (average_unit_cost >= 0),
    is_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attribution_tenant_id ON cogs_attribution(tenant_id);
CREATE INDEX idx_attribution_run_id ON cogs_attribution(run_id);
CREATE INDEX idx_attribution_sku ON cogs_attribution(tenant_id, sku);
CREATE INDEX idx_attribution_sale_date ON cogs_attribution(tenant_id, sale_date);
CREATE INDEX idx_attribution_valid ON cogs_attribution(tenant_id, is_valid) WHERE is_valid = TRUE;

-- Table: cogs_attribution_details
-- Line-item details for each lot allocation
CREATE TABLE cogs_attribution_details (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attribution_id UUID NOT NULL REFERENCES cogs_attribution(attribution_id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,
    lot_id VARCHAR(100) NOT NULL,
    quantity_allocated INTEGER NOT NULL CHECK (quantity_allocated > 0),
    unit_cost DECIMAL(10,2) NOT NULL CHECK (unit_cost >= 0),
    total_cost DECIMAL(12,2) NOT NULL CHECK (total_cost >= 0),
    
    -- Ensure total_cost matches quantity * unit_cost
    CONSTRAINT chk_cost_calculation CHECK (total_cost = quantity_allocated * unit_cost)
);

CREATE INDEX idx_details_attribution ON cogs_attribution_details(attribution_id);
CREATE INDEX idx_details_tenant ON cogs_attribution_details(tenant_id);

-- Table: cogs_summary
-- Monthly COGS summary by SKU
CREATE TABLE cogs_summary (
    summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL REFERENCES cogs_runs(run_id),
    sku VARCHAR(100) NOT NULL,
    period CHAR(7) NOT NULL, -- YYYY-MM format
    total_quantity_sold INTEGER NOT NULL CHECK (total_quantity_sold > 0),
    total_cogs DECIMAL(12,2) NOT NULL CHECK (total_cogs >= 0),
    average_unit_cost DECIMAL(10,4) NOT NULL CHECK (average_unit_cost >= 0),
    is_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure period is valid format
    CONSTRAINT chk_period_format CHECK (period ~ '^\d{4}-\d{2}$')
);

CREATE INDEX idx_summary_tenant_id ON cogs_summary(tenant_id);
CREATE INDEX idx_summary_run_id ON cogs_summary(run_id);
CREATE INDEX idx_summary_period ON cogs_summary(tenant_id, period);
CREATE INDEX idx_summary_sku_period ON cogs_summary(tenant_id, sku, period);

-- Table: uploaded_files
-- Track files uploaded by tenants
CREATE TABLE uploaded_files (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'sales', 'lots', etc.
    file_size INTEGER NOT NULL CHECK (file_size > 0),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR(255),
    processed BOOLEAN DEFAULT FALSE,
    run_id UUID REFERENCES cogs_runs(run_id)
);

CREATE INDEX idx_files_tenant_id ON uploaded_files(tenant_id);
CREATE INDEX idx_files_processed ON uploaded_files(tenant_id, processed);

-- Table: validation_errors
-- Store validation errors from runs
CREATE TABLE validation_errors (
    error_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL REFERENCES cogs_runs(run_id),
    error_type VARCHAR(50) NOT NULL,
    sku VARCHAR(100),
    message TEXT NOT NULL,
    sale_date DATE,
    quantity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_errors_tenant_id ON validation_errors(tenant_id);
CREATE INDEX idx_errors_run_id ON validation_errors(run_id);

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE cogs_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE cogs_attribution ENABLE ROW LEVEL SECURITY;
ALTER TABLE cogs_attribution_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE cogs_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_errors ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for tenant isolation
-- Each tenant can only see their own data

-- cogs_runs policies
CREATE POLICY tenant_isolation_cogs_runs ON cogs_runs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- inventory_movements policies
CREATE POLICY tenant_isolation_inventory_movements ON inventory_movements
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- inventory_snapshots policies
CREATE POLICY tenant_isolation_inventory_snapshots ON inventory_snapshots
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- cogs_attribution policies
CREATE POLICY tenant_isolation_cogs_attribution ON cogs_attribution
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- cogs_attribution_details policies
CREATE POLICY tenant_isolation_cogs_attribution_details ON cogs_attribution_details
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- cogs_summary policies
CREATE POLICY tenant_isolation_cogs_summary ON cogs_summary
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- uploaded_files policies
CREATE POLICY tenant_isolation_uploaded_files ON uploaded_files
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- validation_errors policies
CREATE POLICY tenant_isolation_validation_errors ON validation_errors
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', TRUE));

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_cogs_runs_updated_at BEFORE UPDATE ON cogs_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE cogs_runs IS 'Tracks COGS calculation runs per tenant with rollback support';
COMMENT ON TABLE inventory_movements IS 'Audit trail of all inventory changes for full traceability';
COMMENT ON TABLE inventory_snapshots IS 'Point-in-time inventory state, supporting historical queries';
COMMENT ON TABLE cogs_attribution IS 'Main COGS attribution records linking sales to inventory costs';
COMMENT ON TABLE cogs_attribution_details IS 'Detailed breakdown of which lots fulfilled each sale';
COMMENT ON TABLE cogs_summary IS 'Pre-aggregated monthly summaries for reporting';
COMMENT ON TABLE uploaded_files IS 'Tracks files uploaded by tenants for processing';
COMMENT ON TABLE validation_errors IS 'Captures validation errors for debugging and reporting';