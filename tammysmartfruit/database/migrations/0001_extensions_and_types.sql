-- ==============================================================================
-- MIGRATION: 0001_extensions_and_types.sql
-- DESCRIPTION: Enable essential PostgreSQL extensions, UUIDv7 generator function,
--              generic triggers for updated_at and append-only immutability.
-- AUTHORITATIVE: Tam Mỹ Smart Fruit Ecosystem - Phase 3 Physical Database Design
-- ==============================================================================

-- 1. Enable Required PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "postgis";
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not present on host, continuing with vanilla PostgreSQL table partitioning';
END $$;

-- 2. Define Custom UUIDv7 Generator Function (RFC 9562 Compliant)
-- UUIDv7 combines a 48-bit UNIX timestamp (ms) with 74 bits of cryptographically
-- strong random data. Ensures temporal sortability and optimal B-Tree index locality.
CREATE OR REPLACE FUNCTION generate_uuid_v7()
RETURNS UUID AS $$
DECLARE
    v_time DOUBLE PRECISION;
    v_millis BIGINT;
    v_bytes BYTEA;
BEGIN
    -- Get current epoch milliseconds
    v_time := EXTRACT(EPOCH FROM CLOCK_TIMESTAMP());
    v_millis := FLOOR(v_time * 1000.0)::BIGINT;
    
    -- Generate 16 random bytes
    v_bytes := gen_random_bytes(16);
    
    -- Set the first 6 bytes to milliseconds (48-bit big-endian timestamp)
    v_bytes := set_byte(v_bytes, 0, ((v_millis >> 40) & 255)::INT);
    v_bytes := set_byte(v_bytes, 1, ((v_millis >> 32) & 255)::INT);
    v_bytes := set_byte(v_bytes, 2, ((v_millis >> 24) & 255)::INT);
    v_bytes := set_byte(v_bytes, 3, ((v_millis >> 16) & 255)::INT);
    v_bytes := set_byte(v_bytes, 4, ((v_millis >> 8) & 255)::INT);
    v_bytes := set_byte(v_bytes, 5, (v_millis & 255)::INT);
    
    -- Set UUID version 7 (0111 in top 4 bits of byte 6)
    v_bytes := set_byte(v_bytes, 6, ((get_byte(v_bytes, 6) & 15) | 112)::INT);
    
    -- Set UUID variant (10xx in top 2 bits of byte 8)
    v_bytes := set_byte(v_bytes, 8, ((get_byte(v_bytes, 8) & 63) | 128)::INT);
    
    RETURN encode(v_bytes, 'hex')::UUID;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- 3. Generic Trigger Function: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Generic Trigger Function: Prevent UPDATE and DELETE on Append-Only tables
CREATE OR REPLACE FUNCTION trigger_prevent_modification_audit()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'CANNOT UPDATE IMMUTABLE AUDIT OR EVENT JOURNAL TABLE: %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'CANNOT DELETE FROM IMMUTABLE AUDIT OR EVENT JOURNAL TABLE: %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
