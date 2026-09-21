-- ==============================================================================
-- MIGRATION: 0011_data_trust_claims_evidence.sql
-- MODULE OWNERS: DataTrustModule (24), ClaimModule (25), EvidenceModule (26), RiskModule (27)
-- DESCRIPTION: Data Claims Model, Verification Pipeline, Evidence Links, Risk Engine
--              Assessments, Disputes, Revocations, and Immutable Correction History.
-- ==============================================================================

-- 1. Data Claims Master Table (Aggregate Root - Module 25)
CREATE TABLE data_claims (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    claim_type VARCHAR(80) NOT NULL, -- CROP_VARIETY, AREA_PUC, PHI_SAFE, QUALITY_GRADE, BIO_SAFETY, HARVEST_WEIGHT
    subject_type VARCHAR(60) NOT NULL, -- TREE_GROUP, PLOT, HARVEST_BATCH, PROCESSING_BATCH, CARTON, PALLET, SHIPMENT
    subject_id UUID NOT NULL,
    value_code VARCHAR(80) NOT NULL, -- JACKFRUIT_THAI, GRADE_A_EXPORT, PASSED_PHI, 1500_KG
    value_json JSONB,
    declared_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    declared_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    source_type VARCHAR(60) NOT NULL, -- FARMER_DECLARATION, TECHNICIAN_INSPECTION, LAB_RESULT, AI_INFERENCE, IOT_TELEMETRY, CERTIFIER_AUDIT
    assurance_level VARCHAR(40) DEFAULT 'LEVEL_0_DECLARED' NOT NULL, -- LEVEL_0_DECLARED, LEVEL_1_SYSTEM_VALIDATED, LEVEL_2_ORGANIZATION_VERIFIED, LEVEL_3_INDEPENDENT_CERTIFIED
    verification_status VARCHAR(40) DEFAULT 'PENDING' NOT NULL, -- PENDING, VERIFIED, REJECTED, DISPUTED, REVOKED, SUPERSEDED
    verified_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    verified_at TIMESTAMPTZ,
    verification_method VARCHAR(80),
    approval_request_id UUID, -- References approval_requests(id)
    risk_score NUMERIC(5,2) DEFAULT 0.00 NOT NULL,
    is_current BOOLEAN DEFAULT TRUE NOT NULL,
    superseded_by_claim_id UUID REFERENCES data_claims(id) ON DELETE SET NULL,
    blockchain_proof_id UUID, -- References blockchain_proofs(id)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_claims_subject ON data_claims(subject_type, subject_id) WHERE is_current = TRUE;
CREATE INDEX idx_claims_org ON data_claims(organization_id);
CREATE INDEX idx_claims_status ON data_claims(verification_status);
CREATE INDEX idx_claims_assurance ON data_claims(assurance_level);

CREATE TRIGGER trg_data_claims_updated_at
BEFORE UPDATE ON data_claims
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Claim Status Transition History Table (Append-Only)
CREATE TABLE claim_status_history (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    previous_status VARCHAR(40) NOT NULL,
    new_status VARCHAR(40) NOT NULL,
    previous_assurance_level VARCHAR(40) NOT NULL,
    new_assurance_level VARCHAR(40) NOT NULL,
    transition_reason TEXT,
    transitioned_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_claim_history_claim ON claim_status_history(claim_id, occurred_at ASC);

-- 3. Evidence Records Table (Aggregate Root - Module 26)
CREATE TABLE evidence_records (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    evidence_type VARCHAR(60) NOT NULL, -- GEOTAGGED_PHOTO, IOT_SENSOR_SNAPSHOT, AI_INFERENCE_RESULT, LAB_CERTIFICATE_PDF, PHYSICAL_MEASUREMENT
    media_asset_id UUID REFERENCES media_assets(id) ON DELETE RESTRICT,
    telemetry_evidence_snapshot_id UUID REFERENCES telemetry_evidence_snapshots(id) ON DELETE RESTRICT,
    ai_inference_job_id UUID REFERENCES ai_inference_jobs(id) ON DELETE RESTRICT,
    evidence_hash CHAR(64) NOT NULL, -- SHA-256 integrity hash of evidence data
    captured_at TIMESTAMPTZ NOT NULL,
    gps_point GEOMETRY(Point, 4326),
    metadata_json JSONB,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_evidence_records_org ON evidence_records(organization_id);
CREATE INDEX idx_evidence_records_hash ON evidence_records(evidence_hash);
CREATE INDEX idx_evidence_records_telemetry ON evidence_records(telemetry_evidence_snapshot_id);

-- 4. Claim Evidence Junction Links Table
CREATE TABLE claim_evidence_links (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    evidence_id UUID NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT,
    relevance_weight NUMERIC(4,2) DEFAULT 1.00 NOT NULL,
    linked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    linked_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    UNIQUE (claim_id, evidence_id)
);

CREATE INDEX idx_claim_evidence_claim ON claim_evidence_links(claim_id);

-- 5. Verification Sessions Table (Module 24: Data Trust Verification)
CREATE TABLE verification_sessions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    verifier_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    session_status VARCHAR(30) DEFAULT 'IN_PROGRESS' NOT NULL, -- IN_PROGRESS, COMPLETED_APPROVED, COMPLETED_REJECTED, CANCELLED
    verification_method VARCHAR(80) NOT NULL, -- ON_SITE_PHYSICAL_INSPECTION, BRIX_REFRACTOMETER_TEST, SATELLITE_GEOFENCE_AUDIT, LAB_PCR_ANALYSIS
    digital_signature_hash VARCHAR(255),
    session_notes TEXT,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_verification_sessions_claim ON verification_sessions(claim_id);

-- 6. Verification Steps Table
CREATE TABLE verification_steps (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    session_id UUID NOT NULL REFERENCES verification_sessions(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    step_name VARCHAR(100) NOT NULL, -- GPS_PERIMETER_CHECK, MATURITY_COLOR_CHECK, BRIX_MIN_CHECK, PHI_SAFE_DATE_CHECK
    is_passed BOOLEAN NOT NULL,
    measured_value VARCHAR(100),
    step_notes TEXT,
    checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 7. Risk Assessments Table (Aggregate Root - Module 27: Risk Engine)
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    subject_type VARCHAR(60) NOT NULL, -- HARVEST_BATCH, PROCESSING_BATCH, SHIPMENT, FARM_ACTIVITY
    subject_id UUID NOT NULL,
    risk_policy_id UUID NOT NULL REFERENCES risk_policies(id) ON DELETE RESTRICT,
    overall_risk_score NUMERIC(5,2) NOT NULL, -- 0.00 to 100.00
    risk_decision VARCHAR(30) NOT NULL, -- ALLOW_ANCHOR, REQUIRE_HUMAN_INSPECTION, QUARANTINE_REJECT
    assessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assessed_by_system_worker VARCHAR(80) DEFAULT 'RISK_ENGINE_WORKER_V1' NOT NULL
);

CREATE INDEX idx_risk_assessments_subject ON risk_assessments(subject_type, subject_id);

-- 8. Risk Factor Evaluation Breakdown Table
CREATE TABLE risk_factors (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    assessment_id UUID NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
    factor_code VARCHAR(60) NOT NULL, -- GPS_OUT_OF_PLOT, DUPLICATE_PHOTO_PHASH, PHI_HARVEST_CONFLICT, YIELD_SURGE_ANOMALY, COLD_CHAIN_TEMPERATURE_SPIKE
    raw_risk_points NUMERIC(5,2) NOT NULL,
    factor_weight NUMERIC(4,2) NOT NULL,
    weighted_score NUMERIC(5,2) NOT NULL,
    explanation TEXT NOT NULL,
    evidence_reference_id UUID
);

CREATE INDEX idx_risk_factors_assessment ON risk_factors(assessment_id);

-- 9. Immutable Claim Disputes Table
CREATE TABLE claim_disputes (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    disputed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    dispute_reason TEXT NOT NULL,
    dispute_status VARCHAR(30) DEFAULT 'OPEN' NOT NULL, -- OPEN, UNDER_INVESTIGATION, RESOLVED_UPHELD, RESOLVED_DISMISSED
    investigation_findings TEXT,
    resolved_by_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    raised_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMPTZ
);

-- 10. Immutable Claim Corrections Table (Never Overwrite Linkage)
CREATE TABLE claim_corrections (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    original_claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    replacement_claim_id UUID NOT NULL REFERENCES data_claims(id) ON DELETE RESTRICT,
    correction_reason TEXT NOT NULL,
    authorized_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    corrected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_different_claims CHECK (original_claim_id <> replacement_claim_id)
);
