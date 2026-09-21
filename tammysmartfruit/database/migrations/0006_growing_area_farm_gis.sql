-- ==============================================================================
-- MIGRATION: 0006_growing_area_farm_gis.sql
-- MODULE OWNERS: GrowingAreaModule (5), FarmModule (6), PlotModule (7)
-- DESCRIPTION: PostGIS Spatial Polygons, PUC Registrations, Farms, Plots,
--              Tree Groups, and Farmer Assignments (SRID 4326).
-- ==============================================================================

-- 1. Growing Areas Master Table (Aggregate Root - Module 5)
CREATE TABLE growing_areas (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    area_code VARCHAR(50) UNIQUE NOT NULL, -- PUC-VN-TG-00125
    area_name VARCHAR(120) NOT NULL,
    puc_registration_code VARCHAR(60) UNIQUE NOT NULL, -- Official Plant Unit Code granted by Department of Plant Protection
    puc_issued_at DATE NOT NULL,
    puc_expires_at DATE NOT NULL,
    puc_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- PENDING_APPROVAL, ACTIVE, SUSPENDED, EXPIRED, REVOKED
    province_code VARCHAR(20) NOT NULL,
    district_code VARCHAR(20) NOT NULL,
    commune_code VARCHAR(20) NOT NULL,
    total_area_hectares NUMERIC(8,2) NOT NULL,
    boundary_polygon GEOMETRY(Polygon, 4326) NOT NULL,
    buffer_zone_polygon GEOMETRY(Polygon, 4326),
    centroid_point GEOMETRY(Point, 4326),
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_growing_areas_org ON growing_areas(organization_id);
CREATE INDEX idx_growing_areas_puc ON growing_areas(puc_registration_code);
CREATE INDEX idx_growing_areas_spatial ON growing_areas USING GIST(boundary_polygon);

CREATE TRIGGER trg_growing_areas_updated_at
BEFORE UPDATE ON growing_areas
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Farms Table (Aggregate Root - Module 6)
CREATE TABLE farms (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    growing_area_id UUID NOT NULL REFERENCES growing_areas(id) ON DELETE RESTRICT,
    farm_code VARCHAR(50) UNIQUE NOT NULL, -- FARM-TAMMY-001
    farm_name VARCHAR(120) NOT NULL,
    owner_farmer_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    address_line TEXT NOT NULL,
    total_plots_count INT DEFAULT 1 NOT NULL,
    farm_area_hectares NUMERIC(8,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_farms_org ON farms(organization_id);
CREATE INDEX idx_farms_growing_area ON farms(growing_area_id);
CREATE INDEX idx_farms_owner ON farms(owner_farmer_user_id);

CREATE TRIGGER trg_farms_updated_at
BEFORE UPDATE ON farms
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Plots Table (Aggregate Root - Module 7)
CREATE TABLE plots (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE RESTRICT,
    plot_code VARCHAR(50) UNIQUE NOT NULL, -- PLOT-TAMMY-001-A
    plot_name VARCHAR(100) NOT NULL,
    area_hectares NUMERIC(6,2) NOT NULL,
    boundary_polygon GEOMETRY(Polygon, 4326) NOT NULL,
    centroid_point GEOMETRY(Point, 4326) NOT NULL,
    soil_type VARCHAR(50),
    topography VARCHAR(50),
    irrigation_system VARCHAR(50), -- DRIP_IRRIGATION, SPRINKLER, FLOOD, MANUAL
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_plots_farm ON plots(farm_id);
CREATE INDEX idx_plots_spatial ON plots USING GIST(boundary_polygon);

CREATE TRIGGER trg_plots_updated_at
BEFORE UPDATE ON plots
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 4. Tree Groups Table (Blocks of Trees within a Plot)
CREATE TABLE tree_groups (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    plot_id UUID NOT NULL REFERENCES plots(id) ON DELETE RESTRICT,
    group_code VARCHAR(50) NOT NULL, -- TG-001-JACKFRUIT-THAI
    crop_variety_id UUID NOT NULL REFERENCES crop_varieties(id) ON DELETE RESTRICT,
    planting_date DATE NOT NULL,
    tree_count INT NOT NULL,
    row_spacing_meters NUMERIC(4,2) DEFAULT 6.00,
    tree_spacing_meters NUMERIC(4,2) DEFAULT 5.00,
    estimated_annual_yield_kg NUMERIC(10,2) NOT NULL,
    health_status VARCHAR(30) DEFAULT 'HEALTHY' NOT NULL, -- HEALTHY, MONITORING, DISEASE_INFESTED, RECOVERING
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (plot_id, group_code),
    CONSTRAINT chk_tree_count_positive CHECK (tree_count > 0)
);

CREATE INDEX idx_tree_groups_plot ON tree_groups(plot_id);
CREATE INDEX idx_tree_groups_variety ON tree_groups(crop_variety_id);

CREATE TRIGGER trg_tree_groups_updated_at
BEFORE UPDATE ON tree_groups
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 5. Farm Farmer Assignments Table
CREATE TABLE farm_farmer_assignments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    farmer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    assignment_role VARCHAR(40) DEFAULT 'PRIMARY_CULTIVATOR' NOT NULL, -- PRIMARY_CULTIVATOR, SEASONAL_WORKER, INSPECTION_LEAD
    contract_ref VARCHAR(80),
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    UNIQUE (farm_id, farmer_user_id)
);
