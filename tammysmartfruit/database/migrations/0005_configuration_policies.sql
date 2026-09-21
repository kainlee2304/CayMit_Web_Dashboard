-- ==============================================================================
-- MIGRATION: 0005_configuration_policies.sql
-- MODULE OWNER: ConfigurationModule (Module 4)
-- DESCRIPTION: Versioned, effective-date aware, and auditable system policies:
--              Mass Balance Tolerance, Risk Engine, Evidence, Assurance, Geofence,
--              Blockchain Anchoring, and Market Export Compliance.
-- ==============================================================================

-- 1. System Configurations Master Table (Aggregate Root)
CREATE TABLE system_configurations (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    config_key VARCHAR(80) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TRIGGER trg_system_configurations_updated_at
BEFORE UPDATE ON system_configurations
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Versioned Mass Balance Tolerance Policies
CREATE TABLE mass_balance_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL, -- v1.0, v1.1
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE RESTRICT,
    process_stage VARCHAR(40) NOT NULL, -- HARVEST_TO_PROCESSING, PROCESSING_TO_PACKING, PACKING_TO_PALLET
    tolerance_pct NUMERIC(5,3) NOT NULL, -- e.g. 0.015 (1.5% for fresh jackfruit), 0.005 (0.5% for carton packing)
    max_acceptable_unexplained_loss_pct NUMERIC(5,3) DEFAULT 0.005 NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL, -- DRAFT, ACTIVE, SUPERSEDED, ARCHIVED
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);

CREATE INDEX idx_mass_balance_policy_lookup ON mass_balance_policies(crop_id, process_stage, status, effective_from);

-- 3. Versioned Risk Engine Policies
CREATE TABLE risk_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    weights_configuration JSONB NOT NULL, -- { "gps_drift_weight": 25, "duplicate_photo_weight": 40, "phi_violation_weight": 35, "yield_anomaly_weight": 20 }
    max_allowed_anchor_risk NUMERIC(5,2) DEFAULT 25.00 NOT NULL, -- Threshold for ALLOW_ANCHOR decision
    auto_quarantine_risk_threshold NUMERIC(5,2) DEFAULT 60.00 NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);

-- 4. Versioned Evidence Requirements Policies
CREATE TABLE evidence_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    entity_type VARCHAR(60) NOT NULL, -- HARVEST_BATCH, FARM_ACTIVITY_SPRAY, QC_INSPECTION, SHIPMENT_DISPATCH
    required_evidence_types JSONB NOT NULL, -- ["GEOTAGGED_PHOTO", "PHASH_VERIFICATION", "AI_INFERENCE_CONFIRMATION"]
    min_evidence_count INT DEFAULT 1 NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);

-- 5. Versioned Assurance Level Promotion Policies
CREATE TABLE assurance_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    target_assurance_level VARCHAR(40) NOT NULL, -- LEVEL_1_SYSTEM_VALIDATED, LEVEL_2_ORGANIZATION_VERIFIED, LEVEL_3_INDEPENDENT_CERTIFIED
    criteria_rules JSONB NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);

-- 6. Versioned Geofence Precision Policies
CREATE TABLE geofence_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    max_drift_distance_meters NUMERIC(6,2) DEFAULT 30.00 NOT NULL, -- Allowable GPS drift near plot perimeter
    satellite_min_accuracy_meters NUMERIC(6,2) DEFAULT 15.00 NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);

-- 7. Versioned Blockchain Anchoring Policies
CREATE TABLE blockchain_anchoring_policies (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    policy_code VARCHAR(50) NOT NULL,
    policy_version VARCHAR(20) NOT NULL,
    allowed_event_types JSONB NOT NULL, -- ["HarvestBatchAcceptedEvent", "PackingBatchCompletedEvent", "PalletAssembledEvent", "ShipmentDispatchedEvent", "ExportConfirmedEvent"]
    batch_interval_seconds INT DEFAULT 3600 NOT NULL, -- Anchor every 1 hour
    min_batch_size INT DEFAULT 1 NOT NULL,
    max_batch_size INT DEFAULT 500 NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (policy_code, policy_version)
);
