-- ==============================================================================
-- MIGRATION: 0013_harvest_and_quality.sql
-- MODULE OWNERS: HarvestModule (14), QualityModule (15)
-- DESCRIPTION: Harvest Batches (with 100% Upstream Master Data Inheritance),
--              Scales Weight Verification, QC Inspections, Brix Tests, Defect Logs.
-- ==============================================================================

-- 1. Harvest Batches Table (Aggregate Root - Module 14)
CREATE TABLE harvest_batches (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    season_id UUID NOT NULL REFERENCES crop_seasons(id) ON DELETE RESTRICT,
    harvest_code VARCHAR(50) UNIQUE NOT NULL, -- HAR-2026-000125
    harvest_date DATE NOT NULL,
    harvest_type VARCHAR(30) DEFAULT 'PARTIAL_HARVEST' NOT NULL, -- PARTIAL_HARVEST, FINAL_STRIP_HARVEST
    total_fruit_count INT NOT NULL,
    total_gross_weight_kg NUMERIC(10,2) NOT NULL,
    total_tare_weight_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    total_net_weight_kg NUMERIC(10,2) NOT NULL,
    harvest_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, SUBMITTED, QC_IN_PROGRESS, ACCEPTED, REJECTED, MERGED_TO_PROCESSING
    phi_compliance_status VARCHAR(30) DEFAULT 'VERIFIED_SAFE' NOT NULL, -- VERIFIED_SAFE, VIOLATION_SUSPECT, EXEMPT
    is_yield_exceeded BOOLEAN DEFAULT FALSE NOT NULL,
    is_locked BOOLEAN DEFAULT FALSE NOT NULL, -- Locked after Four-Eyes Approval
    harvest_lead_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_net_weight_positive CHECK (total_net_weight_kg > 0),
    CONSTRAINT chk_fruit_count_positive CHECK (total_fruit_count > 0)
);

CREATE INDEX idx_harvest_batches_season ON harvest_batches(season_id);
CREATE INDEX idx_harvest_batches_status ON harvest_batches(harvest_status);
CREATE INDEX idx_harvest_batches_org ON harvest_batches(organization_id);

CREATE TRIGGER trg_harvest_batches_updated_at
BEFORE UPDATE ON harvest_batches
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Harvest Items Table (Individual Fruit / Crate Lineage)
CREATE TABLE harvest_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    harvest_batch_id UUID NOT NULL REFERENCES harvest_batches(id) ON DELETE CASCADE,
    item_code VARCHAR(60) NOT NULL, -- HAR-2026-000125-ITEM-001
    tree_group_id UUID REFERENCES tree_groups(id) ON DELETE RESTRICT,
    fruit_weight_kg NUMERIC(6,2) NOT NULL,
    initial_grade_code_id UUID NOT NULL REFERENCES quality_grades(id) ON DELETE RESTRICT,
    is_defect_present BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_item_weight_positive CHECK (fruit_weight_kg > 0)
);

CREATE INDEX idx_harvest_items_batch ON harvest_items(harvest_batch_id);

-- 3. Harvest Scale Weight Records Table (Calibrated Digital Scale Verification)
CREATE TABLE harvest_weight_records (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    harvest_batch_id UUID NOT NULL REFERENCES harvest_batches(id) ON DELETE CASCADE,
    scale_device_serial VARCHAR(60) NOT NULL,
    scale_calibration_cert_no VARCHAR(80),
    gross_weight_kg NUMERIC(10,2) NOT NULL,
    tare_weight_kg NUMERIC(10,2) NOT NULL,
    net_weight_kg NUMERIC(10,2) NOT NULL,
    weighed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    operator_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT
);

-- 4. Quality Inspections Table (Aggregate Root - Module 15: Quality Control)
CREATE TABLE quality_inspections (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    inspection_code VARCHAR(50) UNIQUE NOT NULL, -- QC-2026-000877
    inspection_stage VARCHAR(40) NOT NULL, -- RECEIVING_STATION, POST_PROCESSING, PRE_PACKING, CONTAINER_LOADING
    target_entity_type VARCHAR(50) NOT NULL, -- HARVEST_BATCH, PROCESSING_BATCH, CARTON, PALLET
    target_entity_id UUID NOT NULL,
    inspector_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    samples_examined_count INT NOT NULL,
    average_brix NUMERIC(4,1) NOT NULL,
    final_assigned_grade_id UUID NOT NULL REFERENCES quality_grades(id) ON DELETE RESTRICT,
    overall_decision VARCHAR(30) NOT NULL, -- APPROVED_FOR_EXPORT, APPROVED_FOR_DOMESTIC, REJECTED_PROCESSING_ONLY, QUARANTINE_DISPOSAL
    rejection_reason TEXT,
    ai_assistance_used BOOLEAN DEFAULT FALSE NOT NULL,
    ai_inference_job_id UUID REFERENCES ai_inference_jobs(id) ON DELETE SET NULL,
    inspected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_quality_inspections_target ON quality_inspections(target_entity_type, target_entity_id);
CREATE INDEX idx_quality_inspections_org ON quality_inspections(organization_id);

-- 5. Quality Samples Table (Representative fruits drawn for destructive testing)
CREATE TABLE quality_samples (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    inspection_id UUID NOT NULL REFERENCES quality_inspections(id) ON DELETE CASCADE,
    sample_index INT NOT NULL,
    sample_weight_kg NUMERIC(6,2) NOT NULL,
    flesh_color_code VARCHAR(40), -- DEEP_YELLOW, ORANGE_RED, PALE_YELLOW
    aroma_profile VARCHAR(40), -- EXCELLENT_FRAGRANT, NORMAL, WEAK
    firmness_kg_cm2 NUMERIC(5,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 6. Refractometer Brix Tests Table
CREATE TABLE brix_tests (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    sample_id UUID NOT NULL REFERENCES quality_samples(id) ON DELETE CASCADE,
    refractometer_model VARCHAR(80) NOT NULL, -- ATAGO PAL-1 Digital Pocket Refractometer
    refractometer_serial VARCHAR(60) NOT NULL,
    brix_reading NUMERIC(4,1) NOT NULL,
    test_temperature_c NUMERIC(4,1) DEFAULT 25.0 NOT NULL,
    tested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_brix_range CHECK (brix_reading >= 0.0 AND brix_reading <= 40.0)
);

-- 7. Defect Findings Table
CREATE TABLE defect_findings (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    sample_id UUID NOT NULL REFERENCES quality_samples(id) ON DELETE CASCADE,
    disease_type_id UUID REFERENCES disease_types(id) ON DELETE RESTRICT,
    defect_category VARCHAR(50) NOT NULL, -- INTERNAL_BROWNING, FUNGAL_ROT, FRUIT_BORER_TUNNEL, SUNSCALD, MECHANICAL_BRUISE
    affected_surface_pct NUMERIC(5,2) NOT NULL,
    severity VARCHAR(20) NOT NULL -- MINOR_COSMETIC, MODERATE, SEVERE_DISQUALIFYING
);
