-- ==============================================================================
-- MIGRATION: 0015_packing_and_brands.sql
-- MODULE OWNER: PackingModule (Module 17)
-- DESCRIPTION: Brand Master Data, Eligibility Rules & Authorizations, Carton Packing,
--              Pallet Aggregation (SSCC-18), and Cryptographic QR Trace Tokens.
-- ==============================================================================

-- 1. Brands Master Table (Aggregate Root)
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    brand_code VARCHAR(50) UNIQUE NOT NULL, -- BRAND-TAMMY-PREMIUM, BRAND-MEKONG-GOLD
    brand_name VARCHAR(120) NOT NULL,
    brand_owner_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    logo_media_asset_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    trademark_registration_no VARCHAR(80),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Brand Eligibility Rules Table (Policy Engine for Brand Usage)
CREATE TABLE brand_eligibility_rules (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    required_crop_variety_id UUID NOT NULL REFERENCES crop_varieties(id) ON DELETE RESTRICT,
    min_quality_grade_id UUID NOT NULL REFERENCES quality_grades(id) ON DELETE RESTRICT,
    min_brix NUMERIC(4,1) NOT NULL,
    required_certificate_type_id UUID REFERENCES certificate_types(id) ON DELETE RESTRICT,
    allowed_market_id UUID REFERENCES market_codes(id) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Brand Authorizations Table (Licenses given to packing facilities)
CREATE TABLE brand_authorizations (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    authorized_packhouse_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    license_agreement_ref VARCHAR(80),
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (brand_id, authorized_packhouse_org_id)
);

-- 4. Packing Batches Table (Aggregate Root)
CREATE TABLE packing_batches (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    packing_code VARCHAR(50) UNIQUE NOT NULL, -- PAC-2026-000329
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    packaging_spec_id UUID NOT NULL REFERENCES packaging_specs(id) ON DELETE RESTRICT,
    total_cartons_count INT DEFAULT 0 NOT NULL,
    total_net_weight_kg NUMERIC(10,2) NOT NULL,
    packing_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, PACKING_IN_PROGRESS, QC_APPROVED, COMPLETED
    packing_date DATE NOT NULL,
    packhouse_lead_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_packing_batches_org ON packing_batches(organization_id);
CREATE INDEX idx_packing_batches_brand ON packing_batches(brand_id);

CREATE TRIGGER trg_packing_batches_updated_at
BEFORE UPDATE ON packing_batches
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 5. Packing Inputs Junction Table
CREATE TABLE packing_inputs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    packing_batch_id UUID NOT NULL REFERENCES packing_batches(id) ON DELETE CASCADE,
    processing_output_id UUID NOT NULL REFERENCES processing_outputs(id) ON DELETE RESTRICT,
    quantity_allocated_kg NUMERIC(10,2) NOT NULL,
    allocated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (packing_batch_id, processing_output_id)
);

-- 6. Product Cartons Table
CREATE TABLE cartons (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    packing_batch_id UUID NOT NULL REFERENCES packing_batches(id) ON DELETE CASCADE,
    carton_code VARCHAR(60) UNIQUE NOT NULL, -- CAR-2026-000329-0001
    net_weight_kg NUMERIC(6,2) NOT NULL,
    gross_weight_kg NUMERIC(6,2) NOT NULL,
    fruit_pieces_count INT NOT NULL,
    is_palletized BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_cartons_batch ON cartons(packing_batch_id);

-- 7. Pallets Master Table (Aggregate Root: Shipping Aggregation Unit)
CREATE TABLE pallets (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    pallet_code VARCHAR(50) UNIQUE NOT NULL, -- PAL-2026-000104
    sscc_18_code VARCHAR(20) UNIQUE NOT NULL, -- GS1 Serial Shipping Container Code (18 digits)
    target_market_id UUID REFERENCES market_codes(id) ON DELETE RESTRICT,
    total_cartons_count INT DEFAULT 0 NOT NULL,
    total_gross_weight_kg NUMERIC(10,2) NOT NULL,
    total_net_weight_kg NUMERIC(10,2) NOT NULL,
    pallet_qc_status VARCHAR(30) DEFAULT 'PENDING_QC' NOT NULL, -- PENDING_QC, QC_PASSED, QUARANTINE_HOLD, REJECTED
    pallet_inventory_status VARCHAR(30) DEFAULT 'IN_PACKHOUSE' NOT NULL, -- IN_PACKHOUSE, WAREHOUSE_STORED, RESERVED, DISPATCHED, DELIVERED
    assembled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assembled_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_pallets_org ON pallets(organization_id);
CREATE INDEX idx_pallets_sscc ON pallets(sscc_18_code);
CREATE INDEX idx_pallets_inv_status ON pallets(pallet_inventory_status);

CREATE TRIGGER trg_pallets_updated_at
BEFORE UPDATE ON pallets
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 8. Pallet Items Junction Table
CREATE TABLE pallet_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    pallet_id UUID NOT NULL REFERENCES pallets(id) ON DELETE CASCADE,
    carton_id UUID UNIQUE NOT NULL REFERENCES cartons(id) ON DELETE RESTRICT,
    layer_number INT DEFAULT 1,
    position_index INT DEFAULT 1,
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_pallet_items_pallet ON pallet_items(pallet_id);

-- 9. Cryptographically-Random Public QR Trace Tokens Table
CREATE TABLE qr_trace_tokens (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    trace_code VARCHAR(64) UNIQUE NOT NULL, -- Cryptographically strong random token e.g. "tk_7f9a2b4e8c1d5f"
    entity_type VARCHAR(40) NOT NULL, -- CARTON, PALLET, HARVEST_BATCH
    entity_id UUID UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    total_scan_count INT DEFAULT 0 NOT NULL,
    last_scanned_at TIMESTAMPTZ,
    last_scan_ip INET,
    last_scan_country VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_qr_trace_tokens_code ON qr_trace_tokens(trace_code);
