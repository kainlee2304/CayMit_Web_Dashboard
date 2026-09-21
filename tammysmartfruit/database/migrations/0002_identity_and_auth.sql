-- ==============================================================================
-- MIGRATION: 0002_identity_and_auth.sql
-- MODULE OWNER: IdentityModule (Module 1)
-- DESCRIPTION: Users, Credentials (Argon2id + PBKDF2 legacy migration), Roles,
--              Permissions, Sessions, MFA Settings, and Authentication Audit.
-- ==============================================================================

-- 1. Users Table (Aggregate Root)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    username VARCHAR(60) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone_number VARCHAR(20) UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    avatar_storage_key VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    is_suspended BOOLEAN DEFAULT FALSE NOT NULL,
    suspension_reason TEXT,
    preferred_locale VARCHAR(10) DEFAULT 'vi' NOT NULL, -- vi, en
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone_number);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. User Credentials Table (Password Hash & Migration Rehash Tracking)
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    password_algo VARCHAR(30) DEFAULT 'ARGON2ID' NOT NULL, -- ARGON2ID, PBKDF2_LEGACY
    argon2_memory_kb INT DEFAULT 65536,
    argon2_iterations INT DEFAULT 3,
    argon2_parallelism INT DEFAULT 4,
    pbkdf2_iterations INT,
    salt_hex VARCHAR(64),
    rehash_required BOOLEAN DEFAULT FALSE NOT NULL,
    password_changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    failed_login_attempts INT DEFAULT 0 NOT NULL,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TRIGGER trg_user_credentials_updated_at
BEFORE UPDATE ON user_credentials
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Roles Table (System Canonical Roles)
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    role_code VARCHAR(40) UNIQUE NOT NULL, -- admin_hq, technician, farmer, packhouse_lead, qa_qc, warehouse_keeper, logistics_driver, export_officer, auditor_inspector, buyer_partner, system_worker
    name_vi VARCHAR(80) NOT NULL,
    name_en VARCHAR(80) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Permissions Table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    permission_code VARCHAR(80) UNIQUE NOT NULL, -- harvest:create, harvest:verify, pallet:dispatch, cert:revoke
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(30) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. Role Permissions Junction
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

-- 6. User Roles Junction (Global System Roles)
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

-- 7. User Persistent Sessions (Session Metadata)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash CHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of session/refresh token
    device_name VARCHAR(100),
    user_agent TEXT,
    ip_address INET,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(100),
    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_sessions_lookup ON user_sessions(session_token_hash) WHERE is_revoked = FALSE;
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);

-- 8. MFA Settings Table
CREATE TABLE mfa_settings (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    totp_secret_encrypted VARCHAR(255),
    backup_codes_hash JSONB, -- Array of hashed backup codes
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TRIGGER trg_mfa_settings_updated_at
BEFORE UPDATE ON mfa_settings
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 9. Authentication Audit Log Table (Append-Only)
CREATE TABLE auth_audit_logs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    attempted_username VARCHAR(60),
    event_type VARCHAR(40) NOT NULL, -- LOGIN_SUCCESS, LOGIN_FAILED, PASSWORD_REHASHED, LOGOUT, REFRESH_TOKEN_REVOKED, MFA_CHALLENGE
    ip_address INET,
    user_agent TEXT,
    failure_reason VARCHAR(120),
    correlation_id VARCHAR(100),
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_auth_audit_user_time ON auth_audit_logs(user_id, occurred_at DESC);
CREATE INDEX idx_auth_audit_event ON auth_audit_logs(event_type, occurred_at DESC);

CREATE TRIGGER trg_auth_audit_immutable
BEFORE UPDATE OR DELETE ON auth_audit_logs
FOR EACH ROW EXECUTE FUNCTION trigger_prevent_modification_audit();
