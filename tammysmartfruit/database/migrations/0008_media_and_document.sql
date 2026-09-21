-- ==============================================================================
-- MIGRATION: 0008_media_and_document.sql
-- MODULE OWNERS: MediaModule (12), DocumentModule (33)
-- DESCRIPTION: S3/MinIO Object Storage Metadata, Perceptual Hashes (pHash),
--              Digital Documents, Versions, and Multi-Level Data Classifications.
-- ==============================================================================

-- 1. Media Assets Table (Aggregate Root - Module 12)
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    storage_bucket VARCHAR(80) NOT NULL, -- tammy-media-prod, tammy-documents-prod
    object_key VARCHAR(255) UNIQUE NOT NULL, -- uploads/2026/08/28/photos/photo_xyz.jpg
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL, -- image/jpeg, image/png, application/pdf, video/mp4
    file_size_bytes BIGINT NOT NULL,
    sha256_hash CHAR(64) NOT NULL, -- SHA-256 binary integrity hash
    phash_hex VARCHAR(64), -- Perceptual hash for image duplicate / fraud detection
    image_width INT,
    image_height INT,
    gps_extracted_point GEOMETRY(Point, 4326),
    captured_at TIMESTAMPTZ,
    data_classification VARCHAR(30) DEFAULT 'INTERNAL' NOT NULL, -- PUBLIC, PARTNER, INTERNAL, CONFIDENTIAL
    uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_media_assets_org ON media_assets(organization_id);
CREATE INDEX idx_media_assets_sha256 ON media_assets(sha256_hash);
CREATE INDEX idx_media_assets_phash ON media_assets(phash_hex);

-- 2. Digital Documents Table (Aggregate Root - Module 33)
CREATE TABLE digital_documents (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    document_code VARCHAR(60) UNIQUE NOT NULL, -- DOC-2026-PHYTO-00125, DOC-INVOICE-00991
    document_title VARCHAR(150) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- PHYTOSANITARY_CERT, INVOICE, PACKING_LIST, LAB_ANALYSIS, CERTIFICATE_OF_ORIGIN, CUSTOMS_DECLARATION
    issuer_name VARCHAR(120),
    issued_date DATE,
    expiry_date DATE,
    status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- DRAFT, ACTIVE, EXPIRED, ARCHIVED, REVOKED
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_digital_documents_org ON digital_documents(organization_id);
CREATE INDEX idx_digital_documents_code ON digital_documents(document_code);

CREATE TRIGGER trg_digital_documents_updated_at
BEFORE UPDATE ON digital_documents
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Document Versions Table
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    document_id UUID NOT NULL REFERENCES digital_documents(id) ON DELETE CASCADE,
    media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
    version_number INT NOT NULL,
    change_summary TEXT,
    is_current BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (document_id, version_number)
);

-- 4. Entity Document & Media Attachment Links
CREATE TABLE entity_document_links (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    entity_type VARCHAR(60) NOT NULL, -- FARM_ACTIVITY, HARVEST_BATCH, QC_INSPECTION, SHIPMENT, EXPORT_ORDER
    entity_id UUID NOT NULL,
    media_asset_id UUID REFERENCES media_assets(id) ON DELETE RESTRICT,
    document_id UUID REFERENCES digital_documents(id) ON DELETE RESTRICT,
    attachment_purpose VARCHAR(60) NOT NULL, -- FIELD_EVIDENCE, QC_PROOF, LAB_REPORT, BILL_OF_LADING, CUSTOMS_STAMP
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_entity_doc_links ON entity_document_links(entity_type, entity_id);
