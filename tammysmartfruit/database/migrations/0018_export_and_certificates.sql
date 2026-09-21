-- ==============================================================================
-- MIGRATION: 0018_export_and_certificates.sql
-- MODULE OWNERS: ExportModule (22), CertificateModule (23)
-- DESCRIPTION: International Buyers, Export Sales Orders, Market Compliance Engine,
--              Customs Clearance, and Full Lifecycle Agricultural Certificates.
-- ==============================================================================

-- 1. Buyers Master Table (Aggregate Root - Module 22)
CREATE TABLE buyers (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    buyer_code VARCHAR(50) UNIQUE NOT NULL, -- BUYER-GLOBAL-FRESH-USA, BUYER-TOKYO-FRUIT-JP
    company_name VARCHAR(150) NOT NULL,
    country_code CHAR(2) NOT NULL, -- US, JP, KR, CN
    contact_person VARCHAR(100) NOT NULL,
    contact_email VARCHAR(120) NOT NULL,
    contact_phone VARCHAR(30),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Export Sales Orders Table (Aggregate Root)
CREATE TABLE export_orders (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    buyer_id UUID NOT NULL REFERENCES buyers(id) ON DELETE RESTRICT,
    target_market_id UUID NOT NULL REFERENCES market_codes(id) ON DELETE RESTRICT,
    order_code VARCHAR(50) UNIQUE NOT NULL, -- EXP-2026-000045
    contract_reference VARCHAR(80) NOT NULL,
    incoterms VARCHAR(10) DEFAULT 'FOB' NOT NULL, -- FOB, CIF, CFR, DDP
    total_pallets_ordered INT NOT NULL,
    total_net_weight_kg NUMERIC(10,2) NOT NULL,
    total_order_value_usd NUMERIC(12,2) NOT NULL,
    order_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, COMPLIANCE_CHECK_PASSED, ALLOCATED, CUSTOMS_CLEARED, DISPATCHED, COMPLETED, CANCELLED
    compliance_status VARCHAR(30) DEFAULT 'PENDING_EVALUATION' NOT NULL, -- PENDING_EVALUATION, FULLY_COMPLIANT, NON_COMPLIANT_BLOCKED
    shipment_id UUID REFERENCES shipments(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_export_orders_buyer ON export_orders(buyer_id);
CREATE INDEX idx_export_orders_status ON export_orders(order_status);

CREATE TRIGGER trg_export_orders_updated_at
BEFORE UPDATE ON export_orders
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Export Order Line Items Table
CREATE TABLE export_order_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    export_order_id UUID NOT NULL REFERENCES export_orders(id) ON DELETE CASCADE,
    pallet_id UUID UNIQUE NOT NULL REFERENCES pallets(id) ON DELETE RESTRICT,
    pallet_agreed_price_usd NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Versioned Market Requirement Sets (Compliance Engine)
CREATE TABLE market_requirement_sets (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    market_id UUID NOT NULL REFERENCES market_codes(id) ON DELETE RESTRICT,
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE RESTRICT,
    set_code VARCHAR(50) NOT NULL, -- REQ-US-JACKFRUIT-2026
    set_version VARCHAR(20) NOT NULL, -- v1.0, v1.1
    effective_from DATE NOT NULL,
    effective_until DATE,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (market_id, crop_id, set_version)
);

-- 5. Market Requirement Rules Table
CREATE TABLE market_requirement_rules (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    requirement_set_id UUID NOT NULL REFERENCES market_requirement_sets(id) ON DELETE CASCADE,
    rule_type VARCHAR(60) NOT NULL, -- MANDATORY_CERTIFICATE, MAX_PESTICIDE_MRL, MIN_BRIX_THRESHOLD, VAPOR_HEAT_TREATMENT_MANDATORY, PROHIBITED_CHEMICAL
    rule_criteria JSONB NOT NULL,
    is_blocking BOOLEAN DEFAULT TRUE NOT NULL
);

-- 6. Compliance Evaluation Records Table
CREATE TABLE compliance_evaluations (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    export_order_id UUID NOT NULL REFERENCES export_orders(id) ON DELETE CASCADE,
    requirement_set_id UUID NOT NULL REFERENCES market_requirement_sets(id) ON DELETE RESTRICT,
    is_compliant BOOLEAN NOT NULL,
    evaluation_breakdown_json JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    evaluated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT
);

-- 7. Customs Records Table
CREATE TABLE customs_records (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    export_order_id UUID UNIQUE NOT NULL REFERENCES export_orders(id) ON DELETE RESTRICT,
    customs_declaration_no VARCHAR(60) NOT NULL,
    customs_office_name VARCHAR(100) NOT NULL,
    customs_status VARCHAR(30) DEFAULT 'SUBMITTED' NOT NULL, -- SUBMITTED, PHYSICAL_INSPECTION_HOLD, GREEN_CHANNEL_CLEARED, CLEARED, REJECTED
    cleared_at TIMESTAMPTZ,
    customs_officer_name VARCHAR(100),
    customs_stamp_document_id UUID REFERENCES digital_documents(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 8. Agricultural Certificates Master Table (Aggregate Root - Module 23)
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    certificate_type_id UUID NOT NULL REFERENCES certificate_types(id) ON DELETE RESTRICT,
    certificate_number VARCHAR(80) UNIQUE NOT NULL, -- CERT-GLOBALGAP-2026-VN-998877
    issuing_authority VARCHAR(150) NOT NULL, -- Control Union, Bureau Veritas, Quatest 3
    holder_name VARCHAR(150) NOT NULL,
    issue_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    certificate_status VARCHAR(30) DEFAULT 'DECLARED' NOT NULL, -- DECLARED, PENDING_VERIFICATION, VERIFIED, EXPIRED, REVOKED, REJECTED
    digital_document_id UUID REFERENCES digital_documents(id) ON DELETE RESTRICT,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_cert_dates CHECK (expiry_date > issue_date)
);

CREATE INDEX idx_certificates_org ON certificates(organization_id);
CREATE INDEX idx_certificates_status ON certificates(certificate_status);
CREATE INDEX idx_certificates_type ON certificates(certificate_type_id);

CREATE TRIGGER trg_certificates_updated_at
BEFORE UPDATE ON certificates
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 9. Certificate Scope Assignments Table (Linking Certificate to Growing Areas, Farms, Plots, Packhouses)
CREATE TABLE certificate_scope_assignments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE CASCADE,
    scope_target_type VARCHAR(40) NOT NULL, -- GROWING_AREA, FARM, PLOT, PACKHOUSE_FACILITY
    scope_target_id UUID NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (certificate_id, scope_target_type, scope_target_id)
);

CREATE INDEX idx_cert_scope_target ON certificate_scope_assignments(scope_target_type, scope_target_id);

-- 10. Certificate Verifications Table (Audit by Third-Party Inspector)
CREATE TABLE certificate_verifications (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE RESTRICT,
    verifier_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    verification_method VARCHAR(60) NOT NULL, -- ONLINE_ACCREDITATION_DATABASE_LOOKUP, DIRECT_ISSUER_CONFIRMATION, PHYSICAL_AUDIT
    verification_outcome VARCHAR(30) NOT NULL, -- VALID_CONFIRMED, EXPIRED_UNRENEWED, REVOKED_FRAUD, INVALID_SCOPE
    verification_notes TEXT,
    verified_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 11. Certificate Status History Table (Append-Only)
CREATE TABLE certificate_status_history (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE RESTRICT,
    previous_status VARCHAR(30) NOT NULL,
    new_status VARCHAR(30) NOT NULL,
    change_reason TEXT NOT NULL,
    changed_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
