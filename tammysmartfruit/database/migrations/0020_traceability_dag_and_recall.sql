-- ==============================================================================
-- MIGRATION: 0020_traceability_dag_and_recall.sql
-- MODULE OWNERS: TraceabilityModule (28), RecallModule (29)
-- DESCRIPTION: Event-Derived Lineage DAG Read Projection (Nodes, Edges, Ratios),
--              Public Trace Projections, Product Recalls, and Blast Radius Analysis.
-- ==============================================================================

-- 1. Trace Nodes Table (Read-Optimized Projection - Module 28)
CREATE TABLE trace_nodes (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    node_type VARCHAR(60) NOT NULL, -- PLOT, SEASON, HARVEST_BATCH, PROCESSING_BATCH, CARTON, PALLET, SHIPMENT
    node_code VARCHAR(80) UNIQUE NOT NULL, -- HAR-2026-000125, PRO-2026-000412, PAL-2026-000104
    entity_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    data_hash CHAR(64) NOT NULL, -- SHA-256 canonical hash of node entity state
    blockchain_proof_id UUID, -- References blockchain_proofs(id)
    projection_version INT DEFAULT 1 NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_trace_nodes_code ON trace_nodes(node_code);
CREATE INDEX idx_trace_nodes_entity ON trace_nodes(node_type, entity_id);

-- 2. Trace Edges Table (Directed Lineage Graph: Split, Merge, Transform, Aggregate)
CREATE TABLE trace_edges (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    source_node_id UUID NOT NULL REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    target_node_id UUID NOT NULL REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    relationship_type VARCHAR(60) NOT NULL, -- HARVESTED_FROM, PROCESSED_INTO, PACKED_INTO, AGGREGATED_TO, DISPATCHED_IN
    input_quantity NUMERIC(10,2),
    output_quantity NUMERIC(10,2),
    contribution_ratio NUMERIC(6,4) NOT NULL, -- Ratio (0.0001 to 1.0000) indicating exact lineage mass share
    unit_id UUID REFERENCES units(id) ON DELETE RESTRICT,
    event_id UUID NOT NULL REFERENCES domain_event_history(event_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_contribution_ratio CHECK (contribution_ratio > 0.0000 AND contribution_ratio <= 1.0000),
    UNIQUE (source_node_id, target_node_id, relationship_type)
);

CREATE INDEX idx_trace_edges_source ON trace_edges(source_node_id);
CREATE INDEX idx_trace_edges_target ON trace_edges(target_node_id);
CREATE INDEX idx_trace_edges_event ON trace_edges(event_id);

-- 3. Public Trace Cache Projections (Fast Read-Only View for Consumer QR Scans)
CREATE TABLE public_trace_cache (
    trace_code VARCHAR(64) PRIMARY KEY,
    product_brand_name VARCHAR(120) NOT NULL,
    crop_variety_name VARCHAR(100) NOT NULL,
    harvest_date DATE NOT NULL,
    growing_area_name VARCHAR(120) NOT NULL,
    puc_code VARCHAR(60) NOT NULL,
    packing_date DATE NOT NULL,
    quality_grade_name VARCHAR(80) NOT NULL,
    certificates_json JSONB NOT NULL, -- Array of verified certificates
    journey_milestones_json JSONB NOT NULL, -- Timeline array of verified milestones
    blockchain_tx_hash VARCHAR(100),
    last_refreshed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Product Recalls Master Table (Aggregate Root - Module 29)
CREATE TABLE product_recalls (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    recall_code VARCHAR(50) UNIQUE NOT NULL, -- REC-2026-000008
    initiator_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    root_cause_category VARCHAR(60) NOT NULL, -- PESTICIDE_MRL_BREACH, QUARANTINE_PEST_INFESTATION, BACTERIAL_CONTAMINATION, PACKAGING_DEFECT
    root_cause_description TEXT NOT NULL,
    compromised_source_node_id UUID NOT NULL REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    recall_severity VARCHAR(30) NOT NULL, -- CLASS_I_CRITICAL_HEALTH, CLASS_II_MARKET_WITHDRAWAL, CLASS_III_QUALITY_DEFECT
    recall_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- ACTIVE, NOTIFICATIONS_SENT, RECOVERY_IN_PROGRESS, CLOSED_AUDITED
    total_recalled_weight_kg NUMERIC(10,2) NOT NULL,
    total_recovered_weight_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    initiated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_recalls_org ON product_recalls(organization_id);
CREATE INDEX idx_recalls_status ON product_recalls(recall_status);

CREATE TRIGGER trg_product_recalls_updated_at
BEFORE UPDATE ON product_recalls
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 5. Recall Affected Items Table (Calculated Blast Radius from DAG Traversal)
CREATE TABLE recall_affected_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    recall_id UUID NOT NULL REFERENCES product_recalls(id) ON DELETE CASCADE,
    affected_trace_node_id UUID NOT NULL REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    affected_entity_type VARCHAR(50) NOT NULL, -- PALLET, CARTON, SHIPMENT, EXPORT_ORDER
    current_custodian_org_id UUID REFERENCES organizations(id) ON DELETE RESTRICT,
    quarantine_status VARCHAR(30) DEFAULT 'FLAGGED' NOT NULL, -- FLAGGED, ISOLATED_IN_WAREHOUSE, RECOVERED_DESTROYED, UNRECOVERED_CONSUMED
    affected_weight_kg NUMERIC(10,2) NOT NULL,
    notified_at TIMESTAMPTZ,
    recovered_at TIMESTAMPTZ,
    UNIQUE (recall_id, affected_trace_node_id)
);

CREATE INDEX idx_recall_items_node ON recall_affected_items(affected_trace_node_id);
