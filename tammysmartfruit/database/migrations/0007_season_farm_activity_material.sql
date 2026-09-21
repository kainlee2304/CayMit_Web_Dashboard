-- ==============================================================================
-- MIGRATION: 0007_season_farm_activity_material.sql
-- MODULE OWNERS: SeasonModule (8), ActivityModule (9), MaterialModule (10)
-- DESCRIPTION: Crop Seasons Lifecycle, Yield Forecasts, Agricultural Inputs,
--              Farm Diary Activities, and PHI (Pre-Harvest Interval) Tracking.
-- TABLE OWNERSHIP:
--   - SeasonModule (8): crop_seasons, yield_estimates
--   - ActivityModule (9): farm_activities
--   - MaterialModule (10): materials, material_batches, material_usages
-- ==============================================================================

-- 1. Crop Seasons Table (Aggregate Root - Module 8)
CREATE TABLE crop_seasons (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    plot_id UUID NOT NULL REFERENCES plots(id) ON DELETE RESTRICT,
    season_code VARCHAR(50) UNIQUE NOT NULL, -- SEA-2026-PLOT01-M01
    season_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    expected_harvest_start DATE NOT NULL,
    expected_harvest_end DATE NOT NULL,
    actual_harvest_end DATE,
    forecasted_yield_kg NUMERIC(10,2) NOT NULL,
    actual_harvested_yield_kg NUMERIC(10,2) DEFAULT 0.00 NOT NULL,
    season_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, PLANNED, ACTIVE, HARVESTING, COMPLETED, CLOSED
    closed_at TIMESTAMPTZ,
    closed_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_season_dates CHECK (expected_harvest_start >= start_date AND expected_harvest_end >= expected_harvest_start)
);

CREATE INDEX idx_seasons_plot ON crop_seasons(plot_id);
CREATE INDEX idx_seasons_status ON crop_seasons(season_status);

CREATE TRIGGER trg_crop_seasons_updated_at
BEFORE UPDATE ON crop_seasons
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Yield Estimate History (Module 8)
CREATE TABLE yield_estimates (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    season_id UUID NOT NULL REFERENCES crop_seasons(id) ON DELETE CASCADE,
    estimation_method VARCHAR(50) NOT NULL, -- TREE_COUNT_SAMPLING, AI_CANOPY_DENSITY, HISTORICAL_AVERAGE, MANUAL_INSPECTION
    estimated_yield_kg NUMERIC(10,2) NOT NULL,
    confidence_level_pct NUMERIC(5,2) DEFAULT 90.00,
    estimated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    estimated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notes TEXT
);

-- 3. Materials Master Table (Aggregate Root - Module 10)
CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    material_type_id UUID NOT NULL REFERENCES material_types(id) ON DELETE RESTRICT,
    material_code VARCHAR(50) UNIQUE NOT NULL, -- MAT-NPK-BIO-01, MAT-NEEM-OIL-02
    brand_name VARCHAR(120) NOT NULL,
    manufacturer VARCHAR(120) NOT NULL,
    active_ingredient VARCHAR(150),
    active_ingredient_concentration VARCHAR(50),
    pre_harvest_interval_days INT DEFAULT 0 NOT NULL, -- PHI (Cách ly an toàn trước thu hoạch)
    standard_dosage_per_ha VARCHAR(100),
    is_organic_certified BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_materials_org ON materials(organization_id);

CREATE TRIGGER trg_materials_updated_at
BEFORE UPDATE ON materials
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 4. Material Batches Table (Inventory & Expiry Management - Module 10)
CREATE TABLE material_batches (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    material_id UUID NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    batch_number VARCHAR(60) NOT NULL,
    manufacturing_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    initial_quantity NUMERIC(10,2) NOT NULL,
    remaining_quantity NUMERIC(10,2) NOT NULL,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    storage_location VARCHAR(80),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (material_id, batch_number),
    CONSTRAINT chk_remaining_non_negative CHECK (remaining_quantity >= 0)
);

-- 5. Farm Activities Table (Aggregate Root - Module 9: Farm Diary)
CREATE TABLE farm_activities (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    season_id UUID NOT NULL REFERENCES crop_seasons(id) ON DELETE RESTRICT,
    activity_type_id UUID NOT NULL REFERENCES activity_types(id) ON DELETE RESTRICT,
    activity_code VARCHAR(50) UNIQUE NOT NULL, -- ACT-2026-000451
    performed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    performed_at TIMESTAMPTZ NOT NULL,
    gps_point GEOMETRY(Point, 4326),
    gps_accuracy_meters NUMERIC(6,2),
    is_geofence_verified BOOLEAN DEFAULT FALSE NOT NULL,
    duration_hours NUMERIC(4,2),
    weather_condition VARCHAR(40), -- SUNNY, CLOUDY, RAIN, HIGH_HUMIDITY
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_farm_activities_season ON farm_activities(season_id);
CREATE INDEX idx_farm_activities_time ON farm_activities(performed_at DESC);
CREATE INDEX idx_farm_activities_spatial ON farm_activities USING GIST(gps_point);

CREATE TRIGGER trg_farm_activities_updated_at
BEFORE UPDATE ON farm_activities
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 6. Material Usages Table (Owned by Module 10: MaterialModule)
CREATE TABLE material_usages (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    activity_id UUID NOT NULL REFERENCES farm_activities(id) ON DELETE CASCADE,
    material_batch_id UUID NOT NULL REFERENCES material_batches(id) ON DELETE RESTRICT,
    quantity_applied NUMERIC(10,2) NOT NULL,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    phi_days_applied INT NOT NULL,
    earliest_safe_harvest_date DATE NOT NULL, -- calculated: (activity.performed_at::date + phi_days_applied)
    application_method VARCHAR(50), -- FOLIAR_SPRAY, SOIL_DRENCH, ROOT_FERTILIZE
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_quantity_applied_positive CHECK (quantity_applied > 0)
);

CREATE INDEX idx_material_usages_activity ON material_usages(activity_id);
CREATE INDEX idx_material_usages_batch ON material_usages(material_batch_id);
CREATE INDEX idx_material_usages_phi_date ON material_usages(earliest_safe_harvest_date);
