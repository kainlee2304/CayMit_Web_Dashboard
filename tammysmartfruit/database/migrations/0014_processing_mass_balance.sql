-- ==============================================================================
-- MIGRATION: 0014_processing_mass_balance.sql
-- MODULE OWNER: ProcessingModule (Module 16)
-- DESCRIPTION: Processing Operations (1:1, 1:N, N:1, N:N Split/Merge Lineage),
--              Mass Balance Conservation Invariant, Documented Losses & Rejects.
-- ==============================================================================

-- 1. Processing Batches Table (Aggregate Root)
CREATE TABLE processing_batches (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    processing_code VARCHAR(50) UNIQUE NOT NULL, -- PRO-2026-000412
    process_type VARCHAR(50) NOT NULL, -- WASH_BRUSH_DISINFECT, VAPOR_HEAT_TREATMENT_VHT, ETHYLENE_DEGREE_RIPEN, FRESH_CUT_VACUUM
    facility_location VARCHAR(100) NOT NULL,
    mass_balance_policy_id UUID NOT NULL REFERENCES mass_balance_policies(id) ON DELETE RESTRICT,
    total_input_weight_kg NUMERIC(10,2) NOT NULL,
    total_output_weight_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    total_documented_loss_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    total_reject_weight_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    unexplained_discrepancy_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    mass_balance_status VARCHAR(30) DEFAULT 'IN_PROGRESS' NOT NULL, -- IN_PROGRESS, BALANCED_PASSED, IMBALANCE_VIOLATION, FORCE_CLOSED_INVESTIGATION
    processing_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, ACTIVE_PROCESSING, COMPLETED, CANCELLED
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    supervisor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_input_positive CHECK (total_input_weight_kg > 0)
);

CREATE INDEX idx_processing_batches_org ON processing_batches(organization_id);
CREATE INDEX idx_processing_batches_status ON processing_batches(processing_status);
CREATE INDEX idx_processing_batches_balance ON processing_batches(mass_balance_status);

CREATE TRIGGER trg_processing_batches_updated_at
BEFORE UPDATE ON processing_batches
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Processing Inputs Junction Table (Supports N:1 and N:N Merge Lineage)
CREATE TABLE processing_inputs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    processing_batch_id UUID NOT NULL REFERENCES processing_batches(id) ON DELETE CASCADE,
    source_entity_type VARCHAR(50) NOT NULL, -- HARVEST_BATCH, PROCESSING_BATCH
    source_entity_id UUID NOT NULL,
    quantity_consumed_kg NUMERIC(10,2) NOT NULL,
    consumed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_quantity_consumed_positive CHECK (quantity_consumed_kg > 0),
    UNIQUE (processing_batch_id, source_entity_type, source_entity_id)
);

CREATE INDEX idx_processing_inputs_batch ON processing_inputs(processing_batch_id);
CREATE INDEX idx_processing_inputs_source ON processing_inputs(source_entity_type, source_entity_id);

-- 3. Processing Outputs Table (Supports 1:N and N:N Split Lineage)
CREATE TABLE processing_outputs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    processing_batch_id UUID NOT NULL REFERENCES processing_batches(id) ON DELETE CASCADE,
    output_code VARCHAR(60) UNIQUE NOT NULL, -- PRO-2026-000412-OUT-A
    quality_grade_id UUID NOT NULL REFERENCES quality_grades(id) ON DELETE RESTRICT,
    quantity_produced_kg NUMERIC(10,2) NOT NULL,
    item_count INT,
    packaging_readiness VARCHAR(30) DEFAULT 'READY_FOR_PACKING' NOT NULL, -- READY_FOR_PACKING, PACKED, ALLOCATED
    produced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_quantity_produced_positive CHECK (quantity_produced_kg > 0)
);

CREATE INDEX idx_processing_outputs_batch ON processing_outputs(processing_batch_id);

-- 4. Documented Processing Losses Table (Peel, Core Trimmings, Evaporation)
CREATE TABLE processing_losses (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    processing_batch_id UUID NOT NULL REFERENCES processing_batches(id) ON DELETE CASCADE,
    loss_category VARCHAR(50) NOT NULL, -- PEEL_RIND_REMOVAL, CORE_STEM_TRIMMING, MOISTURE_VHT_EVAPORATION, DEFECT_TRIMMING
    loss_weight_kg NUMERIC(10,2) NOT NULL,
    loss_percentage_of_input NUMERIC(5,2) NOT NULL,
    loss_reason_notes TEXT,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_loss_weight_positive CHECK (loss_weight_kg > 0)
);

CREATE INDEX idx_processing_losses_batch ON processing_losses(processing_batch_id);

-- 5. Processing Rejects Table (Damaged or substandard fruits sent to disposal/byproducts)
CREATE TABLE processing_rejects (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    processing_batch_id UUID NOT NULL REFERENCES processing_batches(id) ON DELETE CASCADE,
    reject_reason VARCHAR(60) NOT NULL, -- INTERNAL_BROWNING_DISCOVERED, OVERRIPE_FERMENTATION, SEVERE_PEST_TUNNEL
    reject_weight_kg NUMERIC(10,2) NOT NULL,
    disposal_or_secondary_use VARCHAR(50) NOT NULL, -- COMPOST_FERTILIZER, ANIMAL_FEED, BIOMASS_ENERGY, INCINERATION
    authorized_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rejected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_reject_weight_positive CHECK (reject_weight_kg > 0)
);

CREATE INDEX idx_processing_rejects_batch ON processing_rejects(processing_batch_id);
