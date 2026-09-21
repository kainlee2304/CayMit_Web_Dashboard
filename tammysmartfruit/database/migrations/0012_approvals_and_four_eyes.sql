-- ==============================================================================
-- MIGRATION: 0012_approvals_and_four_eyes.sql
-- MODULE OWNER: ApprovalModule (Module 31)
-- DESCRIPTION: Four-Eyes Principle Approval Engine, Approval Requests,
--              Multi-Step Workflows, and Immutable Action Logs.
-- ==============================================================================

-- 1. Approval Requests Table (Aggregate Root)
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    request_code VARCHAR(50) UNIQUE NOT NULL, -- APR-2026-000889
    entity_type VARCHAR(60) NOT NULL, -- HARVEST_BATCH, PROCESSING_BATCH, PALLET_QC, SHIPMENT_DISPATCH, CLAIM_CORRECTION, CERTIFICATE_REVISION
    entity_id UUID NOT NULL,
    requested_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approval_type VARCHAR(50) NOT NULL, -- FOUR_EYES_STANDARD, TECHNICAL_DIRECTOR_ESCALATION, EXPORT_COMPLIANCE_SIGN_OFF
    current_status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, -- PENDING, IN_REVIEW, APPROVED, REJECTED, RETURNED_FOR_EDIT, CANCELLED
    submission_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_approvals_entity ON approval_requests(entity_type, entity_id);
CREATE INDEX idx_approvals_status ON approval_requests(current_status);
CREATE INDEX idx_approvals_org ON approval_requests(organization_id);

-- 2. Approval Steps Table
CREATE TABLE approval_steps (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    step_sequence INT NOT NULL, -- 1: Technician Review, 2: Packhouse Director Sign-Off
    step_name VARCHAR(100) NOT NULL,
    required_role_id UUID REFERENCES roles(id) ON DELETE RESTRICT,
    assigned_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    step_status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, -- PENDING, IN_PROGRESS, APPROVED, REJECTED, SKIPPED
    is_mandatory BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (request_id, step_sequence)
);

-- 3. Approval Actions Immutable Audit Table (Enforcing 4-Eyes Principle)
CREATE TABLE approval_actions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE RESTRICT,
    step_id UUID NOT NULL REFERENCES approval_steps(id) ON DELETE RESTRICT,
    actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action_decision VARCHAR(30) NOT NULL, -- APPROVED, REJECTED, RETURNED_FOR_AMENDMENT
    action_comments TEXT,
    digital_signature VARCHAR(255),
    acted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_approval_actions_request ON approval_actions(request_id);

-- 4. Four-Eyes Trigger Validation Function: Ensure Actor <> Creator
CREATE OR REPLACE FUNCTION check_four_eyes_constraint()
RETURNS TRIGGER AS $$
DECLARE
    v_creator_id UUID;
BEGIN
    SELECT requested_by_user_id INTO v_creator_id
    FROM approval_requests
    WHERE id = NEW.request_id;
    
    IF NEW.actor_user_id = v_creator_id THEN
        RAISE EXCEPTION 'FOUR-EYES PRINCIPLE VIOLATION: Creator (%) cannot approve their own request (%)', NEW.actor_user_id, NEW.request_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_four_eyes
BEFORE INSERT ON approval_actions
FOR EACH ROW EXECUTE FUNCTION check_four_eyes_constraint();
