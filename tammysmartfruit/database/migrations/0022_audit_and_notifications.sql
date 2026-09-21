-- ==============================================================================
-- MIGRATION: 0022_audit_and_notifications.sql
-- MODULE OWNERS: AuditModule (32), NotificationModule (34), ReportingModule (35)
-- DESCRIPTION: Append-Only Immutable Audit Trail (with Trigger Mutation Lock),
--              Multi-Channel Notifications, and Analytical Report Snapshots.
-- ==============================================================================

-- 1. System Audit Logs Table (Append-Only - Module 32)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    actor_role VARCHAR(40),
    action VARCHAR(40) NOT NULL, -- CREATE, UPDATE, DELETE, VERIFY, APPROVE, DISPUTE, RECALL, ANCHOR
    resource_type VARCHAR(60) NOT NULL, -- HARVEST_BATCH, DATA_CLAIM, PALLET, EXPORT_ORDER, USER_CREDENTIAL
    resource_id UUID NOT NULL,
    request_id VARCHAR(100),
    correlation_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    state_before_json JSONB, -- Redacted of sensitive credentials/secrets
    state_after_json JSONB,  -- Redacted of sensitive credentials/secrets
    change_diff_json JSONB,
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id, occurred_at DESC);
CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id, occurred_at DESC);

-- Trigger to Enforce Total Immutability (Blocks UPDATE and DELETE)
CREATE TRIGGER trg_audit_logs_immutable
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION trigger_prevent_modification_audit();

-- 2. Notifications Table (Aggregate Root - Module 34)
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    notification_type VARCHAR(50) NOT NULL, -- RECALL_ALERT, COLD_CHAIN_EXCURSION, FOUR_EYES_APPROVAL_NEEDED, HARVEST_READY, PHI_SAFE_REACHED
    title VARCHAR(150) NOT NULL,
    body_content TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'INFO' NOT NULL, -- INFO, WARNING, HIGH, CRITICAL_URGENT
    action_url VARCHAR(255),
    reference_entity_type VARCHAR(50),
    reference_entity_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_notifications_org ON notifications(organization_id);

-- 3. Notification Recipients Table
CREATE TABLE notification_recipients (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    recipient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    read_at TIMESTAMPTZ,
    channel_dispatched VARCHAR(30) DEFAULT 'IN_APP_WEBSOCKET' NOT NULL, -- IN_APP_WEBSOCKET, SMTP_EMAIL, SMS_GATEWAY, MOBILE_PUSH
    is_delivered BOOLEAN DEFAULT FALSE NOT NULL,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_notif_recipients_user ON notification_recipients(recipient_user_id, is_read, created_at DESC);

-- 4. User Notification Preferences Table
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    allow_in_app BOOLEAN DEFAULT TRUE NOT NULL,
    allow_email BOOLEAN DEFAULT TRUE NOT NULL,
    allow_sms BOOLEAN DEFAULT FALSE NOT NULL,
    allow_push BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, notification_type)
);

-- 5. Analytical Report Snapshots Table (Module 35: Reporting)
CREATE TABLE analytical_report_snapshots (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    report_type VARCHAR(60) NOT NULL, -- WEEKLY_YIELD_SUMMARY, PEST_DISEASE_DISTRIBUTION, MASS_BALANCE_RECONCILIATION, COLD_CHAIN_COMPLIANCE_RATE
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    summary_metrics_json JSONB NOT NULL,
    generated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_report_snapshots_org_type ON analytical_report_snapshots(organization_id, report_type);
