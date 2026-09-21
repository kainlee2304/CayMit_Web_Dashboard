-- ==============================================================================
-- MIGRATION: 0010_iot_timescaledb.sql
-- MODULE OWNER: IoTModule (Module 11)
-- DESCRIPTION: Gateways, Devices, Physical Sensors, TimescaleDB Sensor Telemetry
--              Hypertable, Telemetry Evidence Snapshots & Environmental Alerts.
-- ==============================================================================

-- 1. IoT Gateways Master Table (Aggregate Root)
CREATE TABLE iot_gateways (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    gateway_code VARCHAR(50) UNIQUE NOT NULL, -- GW-ORCHARD-01, GW-COLD-STORAGE-02
    gateway_type VARCHAR(40) NOT NULL, -- LORAWAN_GATEWAY, MQTT_EDGE_BROKER, 4G_CELLULAR_GATEWAY
    ip_address INET,
    mac_address MACADDR,
    is_online BOOLEAN DEFAULT FALSE NOT NULL,
    last_heartbeat_at TIMESTAMPTZ,
    location_description TEXT,
    gps_point GEOMETRY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TRIGGER trg_iot_gateways_updated_at
BEFORE UPDATE ON iot_gateways
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 2. IoT Devices Table
CREATE TABLE iot_devices (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    gateway_id UUID REFERENCES iot_gateways(id) ON DELETE SET NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    device_code VARCHAR(50) UNIQUE NOT NULL, -- DEV-SOIL-PROBE-001, DEV-WEATHER-STATION-01, DEV-LOGGER-TRUCK-05
    device_model VARCHAR(80) NOT NULL,
    hardware_version VARCHAR(30),
    firmware_version VARCHAR(30),
    battery_powered BOOLEAN DEFAULT TRUE NOT NULL,
    battery_level_pct NUMERIC(4,1),
    last_communication_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_iot_devices_org ON iot_devices(organization_id);

CREATE TRIGGER trg_iot_devices_updated_at
BEFORE UPDATE ON iot_devices
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 3. Physical Sensors Table (Individual sensing elements)
CREATE TABLE sensors (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    device_id UUID NOT NULL REFERENCES iot_devices(id) ON DELETE CASCADE,
    sensor_code VARCHAR(50) NOT NULL, -- SENS-TEMP, SENS-HUMID, SENS-SOIL-MOIST, SENS-PH, SENS-CO2
    metric_code VARCHAR(40) NOT NULL, -- AIR_TEMP_C, AIR_HUMIDITY_PCT, SOIL_MOISTURE_PCT, SOIL_PH, SOIL_EC_MS_CM, LUX, AMBIENT_CO2_PPM
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    calibration_offset NUMERIC(8,4) DEFAULT 0.0000,
    last_reading_value NUMERIC(10,3),
    last_reading_time TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (device_id, sensor_code)
);

-- 4. Device Field Assignments (Associating sensors with Plots, Rooms, Trucks)
CREATE TABLE device_assignments (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    device_id UUID NOT NULL REFERENCES iot_devices(id) ON DELETE RESTRICT,
    assigned_target_type VARCHAR(40) NOT NULL, -- PLOT, TREE_GROUP, COLD_ROOM, WAREHOUSE_ZONE, TRANSPORT_VEHICLE, PALLET
    assigned_target_id UUID NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    unassigned_at TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX idx_device_assignments_target ON device_assignments(assigned_target_type, assigned_target_id) WHERE is_current = TRUE;

-- 5. Sensor Readings Time-Series Table (Composite PK: time, sensor_id for TimescaleDB Partitioning)
CREATE TABLE sensor_readings (
    time TIMESTAMPTZ NOT NULL,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE RESTRICT,
    device_id UUID NOT NULL REFERENCES iot_devices(id) ON DELETE RESTRICT,
    metric_code VARCHAR(40) NOT NULL,
    reading_value NUMERIC(10,3) NOT NULL,
    quality_flag VARCHAR(20) DEFAULT 'GOOD' NOT NULL, -- GOOD, SUSPECT, OUT_OF_RANGE, HARDWARE_ERROR
    battery_pct NUMERIC(4,1),
    signal_rssi INT,
    PRIMARY KEY (time, sensor_id)
);

CREATE INDEX idx_sensor_readings_query ON sensor_readings (sensor_id, time DESC);
CREATE INDEX idx_sensor_readings_metric ON sensor_readings (metric_code, time DESC);

-- Convert sensor_readings into TimescaleDB Hypertable partitioned by time (7 days chunk interval)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('sensor_readings', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
    END IF;
END $$;

-- 6. Telemetry Evidence Snapshots Table (Immune to Raw Telemetry Purge / Retention)
CREATE TABLE telemetry_evidence_snapshots (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE RESTRICT,
    device_id UUID NOT NULL REFERENCES iot_devices(id) ON DELETE RESTRICT,
    metric_code VARCHAR(40) NOT NULL,
    recorded_value NUMERIC(10,3) NOT NULL,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    observed_at TIMESTAMPTZ NOT NULL,
    source_reading_time TIMESTAMPTZ NOT NULL,
    evidence_purpose VARCHAR(60) NOT NULL, -- COLD_CHAIN_COMPLIANCE, PHI_WEATHER_PROOF, QUALITY_CONTROL, DISPUTE_RESOLUTION
    canonical_payload JSONB NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_telemetry_evidence_org ON telemetry_evidence_snapshots(organization_id);
CREATE INDEX idx_telemetry_evidence_sensor ON telemetry_evidence_snapshots(sensor_id, observed_at);
CREATE INDEX idx_telemetry_evidence_hash ON telemetry_evidence_snapshots(sha256_hash);

-- 7. Environmental Alert Rules Table
CREATE TABLE iot_alert_rules (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    rule_name VARCHAR(100) NOT NULL,
    target_type VARCHAR(40) NOT NULL, -- PLOT, COLD_ROOM, TRANSPORT_VEHICLE
    target_id UUID, -- NULL applies to all targets of this type
    metric_code VARCHAR(40) NOT NULL,
    min_threshold NUMERIC(10,3),
    max_threshold NUMERIC(10,3),
    consecutive_breaches_required INT DEFAULT 3 NOT NULL, -- 3 consecutive breaches before alert
    severity VARCHAR(20) DEFAULT 'HIGH' NOT NULL, -- WARNING, HIGH, CRITICAL_EMERGENCY
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 8. IoT Environmental Alerts Incident Table
CREATE TABLE iot_alerts (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    rule_id UUID NOT NULL REFERENCES iot_alert_rules(id) ON DELETE RESTRICT,
    device_id UUID NOT NULL REFERENCES iot_devices(id) ON DELETE RESTRICT,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE RESTRICT,
    breach_value NUMERIC(10,3) NOT NULL,
    threshold_value NUMERIC(10,3) NOT NULL,
    alert_status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, -- ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_ALARM
    triggered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    acknowledged_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX idx_iot_alerts_status ON iot_alerts(alert_status, triggered_at DESC);
