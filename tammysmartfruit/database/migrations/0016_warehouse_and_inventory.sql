-- ==============================================================================
-- MIGRATION: 0016_warehouse_and_inventory.sql
-- MODULE OWNERS: WarehouseModule (18), InventoryModule (19)
-- DESCRIPTION: Cold Storage Warehouses, Storage Bins, Invariant-Protected Inventory
--              (No Negative Stock, No Double Outbound), Stock Movements & Cold Chain.
-- ==============================================================================

-- 1. Warehouses Master Table (Aggregate Root - Module 18)
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    warehouse_code VARCHAR(50) UNIQUE NOT NULL, -- WH-MEKONG-COLD-01
    warehouse_name VARCHAR(120) NOT NULL,
    warehouse_type VARCHAR(40) NOT NULL, -- COLD_STORAGE_FACILITY, PACKHOUSE_BUFFER, PORT_TRANSIT_DEPOT
    address_line TEXT NOT NULL,
    total_capacity_pallets INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_warehouses_org ON warehouses(organization_id);

CREATE TRIGGER trg_warehouses_updated_at
BEFORE UPDATE ON warehouses
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. Warehouse Zones Table
CREATE TABLE warehouse_zones (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    zone_code VARCHAR(40) NOT NULL, -- ZONE-RECEIVING, ZONE-COLD-STORAGE, ZONE-STAGING-OUT
    zone_name VARCHAR(80) NOT NULL,
    zone_type VARCHAR(40) NOT NULL, -- COLD_CHAMBER, DRY_STORAGE, LOADING_DOCK, QUARANTINE_AREA
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (warehouse_id, zone_code)
);

-- 3. Cold Rooms Table (Precise Environmental Enclosure)
CREATE TABLE cold_rooms (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    zone_id UUID NOT NULL REFERENCES warehouse_zones(id) ON DELETE CASCADE,
    room_code VARCHAR(40) NOT NULL, -- CR-01-JACKFRUIT-RIPEN, CR-02-EXPORT-CHILL
    target_temperature_c NUMERIC(4,1) DEFAULT 11.5 NOT NULL, -- 10°C to 13°C standard for fresh jackfruit
    min_allowable_temp_c NUMERIC(4,1) DEFAULT 10.0 NOT NULL,
    max_allowable_temp_c NUMERIC(4,1) DEFAULT 13.0 NOT NULL,
    max_pallet_capacity INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (zone_id, room_code)
);

-- 4. Storage Bins Table (Racks / Positions)
CREATE TABLE storage_bins (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    cold_room_id UUID NOT NULL REFERENCES cold_rooms(id) ON DELETE CASCADE,
    bin_code VARCHAR(40) NOT NULL, -- RACK-A-SHELF-01-BIN-04
    max_pallet_capacity INT DEFAULT 1 NOT NULL,
    current_pallet_count INT DEFAULT 0 NOT NULL,
    is_locked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (cold_room_id, bin_code),
    CONSTRAINT chk_bin_capacity CHECK (current_pallet_count >= 0 AND current_pallet_count <= max_pallet_capacity)
);

-- 5. Inventory Items Table (Aggregate Root - Module 19: Strict Concurrency Protected)
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    pallet_id UUID UNIQUE NOT NULL REFERENCES pallets(id) ON DELETE RESTRICT,
    storage_bin_id UUID REFERENCES storage_bins(id) ON DELETE RESTRICT,
    inventory_status VARCHAR(30) DEFAULT 'AVAILABLE' NOT NULL, -- AVAILABLE, RESERVED, QUARANTINED, IN_TRANSIT_OUT, DISPATCHED
    current_weight_kg NUMERIC(10,2) NOT NULL,
    quarantine_reason TEXT,
    row_version INT DEFAULT 1 NOT NULL, -- Optimistic locking concurrency control
    received_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    dispatched_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_inventory_weight_positive CHECK (current_weight_kg > 0)
);

CREATE INDEX idx_inventory_org_status ON inventory_items(organization_id, inventory_status);
CREATE INDEX idx_inventory_bin ON inventory_items(storage_bin_id);

CREATE TRIGGER trg_inventory_items_updated_at
BEFORE UPDATE ON inventory_items
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 6. Stock Movements Immutable Ledger Table
CREATE TABLE stock_movements (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    inventory_item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE RESTRICT,
    movement_type VARCHAR(40) NOT NULL, -- INBOUND_RECEIPT, INTERNAL_BIN_TRANSFER, RESERVATION_HOLD, QUARANTINE_LOCK, OUTBOUND_DISPATCH, AUDIT_ADJUSTMENT
    from_bin_id UUID REFERENCES storage_bins(id) ON DELETE RESTRICT,
    to_bin_id UUID REFERENCES storage_bins(id) ON DELETE RESTRICT,
    previous_status VARCHAR(30) NOT NULL,
    new_status VARCHAR(30) NOT NULL,
    reference_order_type VARCHAR(50), -- EXPORT_ORDER, DOMESTIC_SALES_ORDER, RECALL_ACTION
    reference_order_id UUID,
    actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    movement_notes TEXT,
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_stock_movements_item ON stock_movements(inventory_item_id);
CREATE INDEX idx_stock_movements_time ON stock_movements(occurred_at DESC);

-- 7. Inventory Active Reservations Table (Canonical State Machine with History Preservation)
CREATE TABLE inventory_reservations (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    inventory_item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE RESTRICT,
    reserved_for_order_type VARCHAR(50) NOT NULL, -- EXPORT_ORDER, DOMESTIC_ORDER
    reserved_for_order_id UUID NOT NULL,
    reserved_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    reservation_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- ACTIVE, FULFILLED, CANCELLED, RELEASED, EXPIRED
    released_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_reservation_status CHECK (reservation_status IN ('ACTIVE', 'FULFILLED', 'CANCELLED', 'RELEASED', 'EXPIRED')),
    CONSTRAINT chk_active_reservation_consistency CHECK (
        (reservation_status = 'ACTIVE' AND released_at IS NULL) OR
        (reservation_status != 'ACTIVE')
    )
);

-- Partial Unique Index: Exactly ONE active reservation permitted per inventory item at any given time
CREATE UNIQUE INDEX idx_unique_active_inventory_reservation 
ON inventory_reservations (inventory_item_id) 
WHERE (reservation_status = 'ACTIVE');

CREATE INDEX idx_reservations_order ON inventory_reservations(reserved_for_order_type, reserved_for_order_id);

-- 8. Cold Chain Temperature Excursion Logs Table
CREATE TABLE temperature_excursions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    cold_room_id UUID REFERENCES cold_rooms(id) ON DELETE RESTRICT,
    pallet_id UUID REFERENCES pallets(id) ON DELETE RESTRICT,
    excursion_start_time TIMESTAMPTZ NOT NULL,
    excursion_end_time TIMESTAMPTZ,
    recorded_peak_temp_c NUMERIC(4,1) NOT NULL,
    threshold_limit_temp_c NUMERIC(4,1) NOT NULL,
    cumulative_degree_hours NUMERIC(8,2) DEFAULT 0.00 NOT NULL,
    severity VARCHAR(20) DEFAULT 'WARNING' NOT NULL, -- WARNING, CRITICAL_SPOILAGE_RISK
    action_taken TEXT,
    resolved_by_user_id UUID REFERENCES users(id) ON DELETE RESTRICT
);
