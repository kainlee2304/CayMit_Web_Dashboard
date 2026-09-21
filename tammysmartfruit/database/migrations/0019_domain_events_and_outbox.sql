-- ==============================================================================
-- MIGRATION: 0019_domain_events_and_outbox.sql
-- MODULE OWNERS: Cross-Cutting Event Infrastructure
-- DESCRIPTION: Durable Append-Only Domain Event Journal (Canonical Source of Truth
--              for Lineage Rebuild), Outbox Queue with Lease Recovery, and Idempotency.
-- ==============================================================================

-- 1. Durable Domain Event History Table (Append-Only Event Journal)
CREATE TABLE domain_event_history (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(120) NOT NULL, -- HarvestBatchAcceptedEvent, ProcessingCompletedEvent, PalletAssembledEvent, BlockchainAnchorEligibleEvent
    event_version VARCHAR(20) NOT NULL, -- 1.0.0
    aggregate_type VARCHAR(80) NOT NULL, -- HarvestBatch, ProcessingBatch, Pallet, Shipment, ExportOrder
    aggregate_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_id VARCHAR(120),
    causation_id UUID,
    payload JSONB NOT NULL,
    payload_hash CHAR(64) NOT NULL, -- SHA-256 canonical hash of JSON payload
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_domain_events_agg ON domain_event_history(aggregate_type, aggregate_id);
CREATE INDEX idx_domain_events_type_time ON domain_event_history(event_type, occurred_at ASC);
CREATE INDEX idx_domain_events_org ON domain_event_history(organization_id);

-- Enforce Immutability on Domain Event Journal
CREATE TRIGGER trg_domain_event_history_immutable
BEFORE UPDATE OR DELETE ON domain_event_history
FOR EACH ROW EXECUTE FUNCTION trigger_prevent_modification_audit();

-- 2. Transactional Outbox Events Queue (Reliable Asynchronous Delivery)
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    event_version VARCHAR(20) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    payload JSONB NOT NULL,
    status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, -- PENDING, PROCESSING, COMPLETED, FAILED
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(80),
    lease_expires_at TIMESTAMPTZ,
    retry_count INT DEFAULT 0 NOT NULL,
    max_retries INT DEFAULT 5 NOT NULL,
    next_retry_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMPTZ
);

-- Dual Partial Indexes optimized for Worker Polling and Lease Recovery (PostgreSQL Immutable Compliant)
CREATE INDEX idx_outbox_pending_queue ON outbox_events (created_at ASC)
WHERE status = 'PENDING';

CREATE INDEX idx_outbox_processing_lease ON outbox_events (lease_expires_at ASC)
WHERE status = 'PROCESSING';

-- 3. Processed Events Consumer Idempotency Table
CREATE TABLE processed_events (
    event_id UUID NOT NULL,
    consumer_name VARCHAR(80) NOT NULL, -- TRACEABILITY_DAG_PROJECTION_WORKER, BLOCKCHAIN_BATCH_WORKER, NOTIFICATION_WORKER
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (event_id, consumer_name)
);
