-- ==============================================================================
-- MIGRATION: 0021_blockchain_proofs.sql
-- MODULE OWNER: BlockchainModule (Module 30)
-- DESCRIPTION: Blockchain Proofs, Merkle Tree Batch Anchoring Jobs, Network Configs,
--              and Independent Public Verification Logs.
-- ==============================================================================

-- 1. Blockchain Network Configurations Table
CREATE TABLE blockchain_network_configs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    network_code VARCHAR(40) UNIQUE NOT NULL, -- POLYGON_MAINNET, ARBITRUM_ONE, ENTERPRISE_QUORUM, INTERNAL_HASH_LEDGER
    network_name VARCHAR(100) NOT NULL,
    rpc_endpoint_url VARCHAR(255) NOT NULL,
    chain_id BIGINT NOT NULL,
    contract_address VARCHAR(80),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_primary_network BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Blockchain Batch Anchoring Jobs Table
CREATE TABLE anchor_jobs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    network_id UUID NOT NULL REFERENCES blockchain_network_configs(id) ON DELETE RESTRICT,
    batch_number VARCHAR(50) UNIQUE NOT NULL, -- ANCHOR-BATCH-2026-08-28-001
    merkle_root CHAR(64) NOT NULL, -- SHA-256 Merkle Root of all items in this batch
    item_count INT NOT NULL,
    job_status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, -- PENDING, SUBMITTED_MEMPOOL, CONFIRMED_ON_CHAIN, FAILED_RETRYING
    transaction_hash VARCHAR(100),
    block_number BIGINT,
    gas_used BIGINT,
    signer_address VARCHAR(80),
    submitted_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_anchor_jobs_status ON anchor_jobs(job_status);
CREATE INDEX idx_anchor_jobs_tx ON anchor_jobs(transaction_hash);

-- 3. Blockchain Proofs Table (Aggregate Root - Module 30)
CREATE TABLE blockchain_proofs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    anchor_job_id UUID REFERENCES anchor_jobs(id) ON DELETE RESTRICT,
    network_id UUID NOT NULL REFERENCES blockchain_network_configs(id) ON DELETE RESTRICT,
    business_event_id UUID UNIQUE NOT NULL REFERENCES domain_event_history(event_id) ON DELETE RESTRICT,
    canonical_data_hash CHAR(64) NOT NULL, -- SHA-256 canonical hash of the individual event payload
    merkle_index INT,
    merkle_leaf_hash CHAR(64),
    merkle_proof_path JSONB, -- Array of sibling hashes to prove inclusion
    proof_status VARCHAR(30) DEFAULT 'PENDING_BATCH' NOT NULL, -- PENDING_BATCH, ANCHORED, VERIFICATION_FAILED
    anchored_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_blockchain_proofs_event ON blockchain_proofs(business_event_id);
CREATE INDEX idx_blockchain_proofs_hash ON blockchain_proofs(canonical_data_hash);

-- 4. Proof Verification History Table (Independent Auditor Check Log)
CREATE TABLE proof_verification_history (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    blockchain_proof_id UUID NOT NULL REFERENCES blockchain_proofs(id) ON DELETE CASCADE,
    verified_by_actor_type VARCHAR(40) NOT NULL, -- CONSUMER_QR_APP, CUSTOMS_INSPECTOR, CERTIFIER_AUDIT, AUTOMATED_CRON
    is_valid BOOLEAN NOT NULL,
    verification_latency_ms INT,
    checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
