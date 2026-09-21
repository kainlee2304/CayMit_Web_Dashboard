-- ==============================================================================
-- MIGRATION: 0017_logistics_and_shipment.sql
-- MODULE OWNERS: LogisticsModule (20), ShipmentModule (21)
-- DESCRIPTION: Logistics Carriers, Refrigerated Vehicles, Shipment Orders,
--              State Machine, Container Seals, and En-Route GPS/Temp Checkpoints.
-- ==============================================================================

-- 1. Carriers Table (Aggregate Root - Module 20)
CREATE TABLE carriers (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    carrier_code VARCHAR(50) UNIQUE NOT NULL, -- CARRIER-VINAFRUIT-LOGISTICS
    carrier_name VARCHAR(120) NOT NULL,
    transport_license_no VARCHAR(80),
    contact_phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Vehicles Table (Refrigerated Trucks / Reefer Containers)
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    carrier_id UUID NOT NULL REFERENCES carriers(id) ON DELETE RESTRICT,
    license_plate VARCHAR(30) UNIQUE NOT NULL,
    vehicle_type VARCHAR(40) NOT NULL, -- REEFER_TRUCK_5T, REEFER_TRUCK_15T, REEFER_CONTAINER_40FT
    refrigeration_unit_brand VARCHAR(80), -- Thermo King, Carrier Transicold
    min_temperature_capability_c NUMERIC(4,1) DEFAULT -20.0 NOT NULL,
    max_temperature_capability_c NUMERIC(4,1) DEFAULT 20.0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Drivers Table
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    carrier_id UUID NOT NULL REFERENCES carriers(id) ON DELETE RESTRICT,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    driver_license_number VARCHAR(50) UNIQUE NOT NULL,
    license_class VARCHAR(10) NOT NULL, -- C, D, E, FC
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Shipments Table (Aggregate Root - Module 21)
CREATE TABLE shipments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    shipment_code VARCHAR(50) UNIQUE NOT NULL, -- SHP-2026-000088
    carrier_id UUID NOT NULL REFERENCES carriers(id) ON DELETE RESTRICT,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE RESTRICT,
    origin_warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    destination_facility_name VARCHAR(150) NOT NULL,
    destination_port VARCHAR(80), -- Cat Lai Port, Tan Son Nhat Airport
    target_market_id UUID NOT NULL REFERENCES market_codes(id) ON DELETE RESTRICT,
    total_pallets_count INT NOT NULL,
    total_gross_weight_kg NUMERIC(10,2) NOT NULL,
    shipment_status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL, -- DRAFT, READY_FOR_PICKUP, PICKED_UP, IN_TRANSIT, AT_PORT, CUSTOMS_CLEARING, EXPORTED, DELIVERED, CANCELLED
    scheduled_departure_at TIMESTAMPTZ NOT NULL,
    actual_departure_at TIMESTAMPTZ,
    actual_arrival_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_shipments_org ON shipments(organization_id);
CREATE INDEX idx_shipments_status ON shipments(shipment_status);

CREATE TRIGGER trg_shipments_updated_at
BEFORE UPDATE ON shipments
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 5. Shipment Items Table (Pallet Assignment & No-Double-Dispatch Active Guard)
CREATE TABLE shipment_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    pallet_id UUID NOT NULL REFERENCES pallets(id) ON DELETE RESTRICT,
    pallet_weight_kg NUMERIC(10,2) NOT NULL,
    assignment_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- ACTIVE, DELIVERED, RELEASED, CANCELLED
    loaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    released_at TIMESTAMPTZ,
    UNIQUE (shipment_id, pallet_id)
);

-- Partial Unique Index: A Pallet cannot belong to more than one ACTIVE shipment assignment simultaneously
CREATE UNIQUE INDEX idx_unique_active_pallet_shipment
ON shipment_items (pallet_id)
WHERE (assignment_status = 'ACTIVE' AND released_at IS NULL);

CREATE INDEX idx_shipment_items_pallet ON shipment_items(pallet_id);

-- 6. Container Seal Assignments Table
CREATE TABLE container_assignments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    shipment_id UUID UNIQUE NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    container_number VARCHAR(30) NOT NULL, -- e.g. TEMU-123456-7
    seal_number VARCHAR(40) NOT NULL, -- High-security bolt seal e.g. VN-CUS-998877
    tare_weight_kg NUMERIC(8,2) NOT NULL,
    verified_sealed_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    sealed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 7. Shipment En-Route Checkpoints & Cold Chain Telemetry
CREATE TABLE shipment_checkpoints (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    checkpoint_name VARCHAR(100) NOT NULL, -- DEPARTURE_PACKHOUSE, HIGHWAY_REST_STOP, PORT_TERMINAL_GATE, CUSTOMS_INSPECTION_YARD
    gps_point GEOMETRY(Point, 4326) NOT NULL,
    recorded_temperature_c NUMERIC(4,1) NOT NULL,
    is_seal_intact BOOLEAN DEFAULT TRUE NOT NULL,
    checkpoint_status VARCHAR(30) DEFAULT 'PASSED' NOT NULL, -- PASSED, EXCURSION_FLAGGED, SEAL_BROKEN_ALERT
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    recorded_by_driver_id UUID REFERENCES drivers(id) ON DELETE RESTRICT,
    notes TEXT
);

CREATE INDEX idx_shipment_checkpoints_shipment ON shipment_checkpoints(shipment_id, recorded_at ASC);
