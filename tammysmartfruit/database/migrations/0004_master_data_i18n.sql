-- ==============================================================================
-- MIGRATION: 0004_master_data_i18n.sql
-- MODULE OWNER: MasterDataModule (Module 3)
-- DESCRIPTION: System Master Data with strict code-based keys and independent
--              i18n localized translation tables (VI / EN).
-- ==============================================================================

-- 1. Crops Master Table (Aggregate Root)
CREATE TABLE crops (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    crop_code VARCHAR(40) UNIQUE NOT NULL, -- JACKFRUIT, DURIAN, MANGO, DRAGONFRUIT
    scientific_name VARCHAR(100) NOT NULL, -- Artocarpus heterophyllus
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Crop Translations
CREATE TABLE crop_translations (
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL, -- vi, en
    name VARCHAR(80) NOT NULL,
    description TEXT,
    PRIMARY KEY (crop_id, locale)
);

-- 3. Crop Varieties Master Table
CREATE TABLE crop_varieties (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE RESTRICT,
    variety_code VARCHAR(50) UNIQUE NOT NULL, -- JACKFRUIT_THAI, JACKFRUIT_RED_INDONESIAN, JACKFRUIT_SEEDLESS, JACKFRUIT_TA_SUPER_SWEET
    standard_growth_days INT, -- e.g. 110 - 125 days from fruit bagging
    optimal_brix_min NUMERIC(4,1) DEFAULT 14.0,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Crop Variety Translations
CREATE TABLE crop_variety_translations (
    variety_id UUID NOT NULL REFERENCES crop_varieties(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL, -- vi, en
    name VARCHAR(100) NOT NULL,
    characteristics TEXT,
    PRIMARY KEY (variety_id, locale)
);

-- 5. Quality Grades Master Table
CREATE TABLE quality_grades (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE RESTRICT,
    grade_code VARCHAR(40) NOT NULL, -- GRADE_A_EXPORT, GRADE_B_DOMESTIC, GRADE_C_PROCESSING
    min_brix NUMERIC(4,1) NOT NULL,
    min_weight_kg NUMERIC(6,2) NOT NULL,
    max_weight_kg NUMERIC(6,2),
    allow_cosmetic_defects BOOLEAN DEFAULT FALSE NOT NULL,
    is_export_eligible BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (crop_id, grade_code)
);

-- 6. Quality Grade Translations
CREATE TABLE quality_grade_translations (
    grade_id UUID NOT NULL REFERENCES quality_grades(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(80) NOT NULL,
    description TEXT,
    PRIMARY KEY (grade_id, locale)
);

-- 7. Activity Types Master Table
CREATE TABLE activity_types (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    activity_code VARCHAR(50) UNIQUE NOT NULL, -- PLANTING, WATERING, FERTILIZING, PRUNING, BAGGING, PESTICIDE_SPRAY, HARVESTING
    requires_material BOOLEAN DEFAULT FALSE NOT NULL,
    requires_gps_photo BOOLEAN DEFAULT TRUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE activity_type_translations (
    activity_type_id UUID NOT NULL REFERENCES activity_types(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(80) NOT NULL,
    instructions TEXT,
    PRIMARY KEY (activity_type_id, locale)
);

-- 8. Measurement Units Master Table
CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    unit_code VARCHAR(30) UNIQUE NOT NULL, -- KG, TON, CARTON, PALLET, HECTARE, BRIX, DEGREE_C, PERCENT, LITER
    unit_type VARCHAR(30) NOT NULL, -- MASS, COUNT, AREA, QUALITY, TEMPERATURE, VOLUME
    is_si_base BOOLEAN DEFAULT FALSE NOT NULL,
    conversion_to_base NUMERIC(14,6) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE unit_translations (
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    PRIMARY KEY (unit_id, locale)
);

-- 9. Disease & Pest Types Master Table
CREATE TABLE disease_types (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    crop_id UUID NOT NULL REFERENCES crops(id) ON DELETE RESTRICT,
    disease_code VARCHAR(60) NOT NULL, -- STEM_BORER, PINK_DISEASE, STEM_CRACKING, FRUIT_BORER, FRUIT_ROT
    scientific_name VARCHAR(100),
    severity_level VARCHAR(20) DEFAULT 'HIGH' NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL_QUARANTINE
    quarantine_risk BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (crop_id, disease_code)
);

CREATE TABLE disease_type_translations (
    disease_id UUID NOT NULL REFERENCES disease_types(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    symptoms TEXT,
    treatment_protocol TEXT,
    PRIMARY KEY (disease_id, locale)
);

-- 10. Market Codes Master Table (Target Export Countries)
CREATE TABLE market_codes (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    market_code VARCHAR(20) UNIQUE NOT NULL, -- VN, CN, US, EU, JP, KR, AU
    iso_country_code CHAR(2) NOT NULL,
    requires_puc BOOLEAN DEFAULT TRUE NOT NULL,
    requires_phc BOOLEAN DEFAULT TRUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE market_code_translations (
    market_id UUID NOT NULL REFERENCES market_codes(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(80) NOT NULL,
    quarantine_notes TEXT,
    PRIMARY KEY (market_id, locale)
);

-- 11. Packaging Specifications Master Table
CREATE TABLE packaging_specs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    spec_code VARCHAR(40) UNIQUE NOT NULL, -- CARTON_10KG_EXPORT, CARTON_15KG_BULK, PALLET_STANDARD_120X100
    package_type VARCHAR(30) NOT NULL, -- CARTON, PUNNET, CRATE, PALLET
    target_net_weight_kg NUMERIC(8,2) NOT NULL,
    tare_weight_kg NUMERIC(6,3) NOT NULL,
    dimensions_cm_lxwxh VARCHAR(40),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 12. Certificate Types Master Table
CREATE TABLE certificate_types (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    cert_code VARCHAR(40) UNIQUE NOT NULL, -- VIETGAP, GLOBALGAP, ORGANIC_USDA, ORGANIC_EU, HACCP, PUC, PHC
    accreditation_body VARCHAR(100),
    is_export_mandatory BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE certificate_type_translations (
    cert_type_id UUID NOT NULL REFERENCES certificate_types(id) ON DELETE CASCADE,
    locale VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    PRIMARY KEY (cert_type_id, locale)
);

-- 13. Material Types Master Table (Agricultural Inputs)
CREATE TABLE material_types (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    type_code VARCHAR(40) UNIQUE NOT NULL, -- BIO_FERTILIZER, CHEMICAL_FERTILIZER, BIO_PESTICIDE, CHEMICAL_PESTICIDE, GROWTH_REGULATOR
    is_quarantine_restricted BOOLEAN DEFAULT FALSE NOT NULL,
    is_organic_allowed BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
