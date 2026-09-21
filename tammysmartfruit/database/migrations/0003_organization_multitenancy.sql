-- ==============================================================================
-- MIGRATION: 0003_organization_multitenancy.sql
-- MODULE OWNER: OrganizationModule (Module 2)
-- DESCRIPTION: Multi-Tenancy Organizations, Departments, Teams, Memberships,
--              Data Scope Assignments, and Inter-Organization Relationships.
-- ==============================================================================

-- 1. Organizations Table (Aggregate Root)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    org_code VARCHAR(40) UNIQUE NOT NULL, -- TAMMY_HQ, HTX_TAM_MY, PACKHOUSE_01, VINAFRUIT_LOGISTICS
    org_name_vi VARCHAR(150) NOT NULL,
    org_name_en VARCHAR(150) NOT NULL,
    org_type VARCHAR(40) NOT NULL, -- ECOSYSTEM_HQ, COOPERATIVE, FARMING_ENTERPRISE, PACKHOUSE_FACILITY, LOGISTICS_CARRIER, CERTIFICATION_BODY, BUYER_IMPORTER
    tax_id VARCHAR(30) UNIQUE,
    registration_number VARCHAR(50),
    contact_email VARCHAR(120),
    contact_phone VARCHAR(20),
    headquarters_address TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    parent_org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_organizations_code ON organizations(org_code);
CREATE INDEX idx_organizations_type ON organizations(org_type);

CREATE TRIGGER trg_organizations_updated_at
BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Departments Table
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dept_code VARCHAR(40) NOT NULL,
    dept_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (organization_id, dept_code)
);

CREATE TRIGGER trg_departments_updated_at
BEFORE UPDATE ON departments
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Teams Table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    team_code VARCHAR(40) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_lead_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (department_id, team_code)
);

CREATE TRIGGER trg_teams_updated_at
BEFORE UPDATE ON teams
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 4. User Organization Memberships
CREATE TABLE user_organization_memberships (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    membership_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- PENDING, ACTIVE, SUSPENDED, TERMINATED
    is_primary_organization BOOLEAN DEFAULT FALSE NOT NULL,
    joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    terminated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, organization_id)
);

CREATE INDEX idx_memberships_user ON user_organization_memberships(user_id);
CREATE INDEX idx_memberships_org ON user_organization_memberships(organization_id);

CREATE TRIGGER trg_memberships_updated_at
BEFORE UPDATE ON user_organization_memberships
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 5. Membership Roles (Role within a specific organization)
CREATE TABLE membership_roles (
    membership_id UUID NOT NULL REFERENCES user_organization_memberships(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (membership_id, role_id)
);

-- 6. Data Scope Assignments (Fine-grained Scope Enforcement)
CREATE TABLE data_scope_assignments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    membership_id UUID NOT NULL REFERENCES user_organization_memberships(id) ON DELETE CASCADE,
    scope_type VARCHAR(30) NOT NULL, -- OWN, ASSIGNED, COOPERATIVE, ORGANIZATION, ALL
    assigned_resource_type VARCHAR(50), -- GROWING_AREA, FARM, PLOT, WAREHOUSE, SHIPMENT
    assigned_resource_id UUID, -- Specific resource ID if scope is ASSIGNED
    granted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_data_scope_lookup ON data_scope_assignments(membership_id, scope_type);

-- 7. Inter-Organization Relationships (Federation & Cooperative Links)
CREATE TABLE organization_relationships (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    source_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    target_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    relationship_type VARCHAR(40) NOT NULL, -- HQ_SUBSIDIARY, COOPERATIVE_MEMBER, SUPPLIER_BUYER, LOGISTICS_PARTNER, CERTIFIER_CLIENT
    contract_reference VARCHAR(80),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (source_org_id, target_org_id, relationship_type)
);
