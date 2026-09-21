-- ==============================================================================
-- MIGRATION: 0023_views_and_functions.sql
-- MODULE OWNERS: Traceability, Processing, Quality, Agronomy Cross-Cutting
-- DESCRIPTION: High-performance Recursive Lineage Functions, Mass Balance
--              Conservation Verifiers, PHI Safety & Geofence Check Functions.
-- ==============================================================================

-- 1. Recursive Backward Lineage Traversal Function (Carton/Pallet -> Upstream Farm)
CREATE OR REPLACE FUNCTION fn_get_backward_lineage(p_target_node_code VARCHAR)
RETURNS TABLE (
    depth INT,
    node_id UUID,
    node_type VARCHAR(60),
    node_code VARCHAR(80),
    relationship VARCHAR(60),
    contribution_ratio NUMERIC(6,4),
    data_hash CHAR(64)
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE lineage_tree AS (
        -- Anchor Member
        SELECT 
            1 AS depth,
            n.id AS node_id,
            n.node_type,
            n.node_code,
            CAST('ROOT' AS VARCHAR(60)) AS relationship,
            CAST(1.0000 AS NUMERIC(6,4)) AS contribution_ratio,
            n.data_hash
        FROM trace_nodes n
        WHERE n.node_code = p_target_node_code
        
        UNION ALL
        
        -- Recursive Member
        SELECT 
            lt.depth + 1,
            parent.id,
            parent.node_type,
            parent.node_code,
            e.relationship_type,
            e.contribution_ratio,
            parent.data_hash
        FROM trace_nodes parent
        JOIN trace_edges e ON e.source_node_id = parent.id
        JOIN lineage_tree lt ON lt.node_id = e.target_node_id
    )
    SELECT * FROM lineage_tree ORDER BY depth ASC;
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. Recursive Forward Lineage & Blast Radius Analysis Function (Compromised Plot -> Affected Pallets)
CREATE OR REPLACE FUNCTION fn_get_forward_lineage(p_source_node_code VARCHAR)
RETURNS TABLE (
    depth INT,
    node_id UUID,
    node_type VARCHAR(60),
    node_code VARCHAR(80),
    relationship VARCHAR(60),
    contribution_ratio NUMERIC(6,4)
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE forward_tree AS (
        -- Anchor Member
        SELECT 
            1 AS depth,
            n.id AS node_id,
            n.node_type,
            n.node_code,
            CAST('SOURCE_ROOT' AS VARCHAR(60)) AS relationship,
            CAST(1.0000 AS NUMERIC(6,4)) AS contribution_ratio
        FROM trace_nodes n
        WHERE n.node_code = p_source_node_code
        
        UNION ALL
        
        -- Recursive Member
        SELECT 
            ft.depth + 1,
            child.id,
            child.node_type,
            child.node_code,
            e.relationship_type,
            e.contribution_ratio
        FROM trace_nodes child
        JOIN trace_edges e ON e.target_node_id = child.id
        JOIN forward_tree ft ON ft.node_id = e.source_node_id
    )
    SELECT * FROM forward_tree ORDER BY depth ASC;
END;
$$ LANGUAGE plpgsql STABLE;

-- 3. Mass Balance Conservation Verification Function
CREATE OR REPLACE FUNCTION fn_verify_processing_mass_balance(p_processing_batch_id UUID)
RETURNS TABLE (
    total_input NUMERIC(10,2),
    total_accounted_output NUMERIC(10,2),
    discrepancy NUMERIC(10,2),
    allowed_tolerance_pct NUMERIC(5,3),
    max_allowed_discrepancy NUMERIC(10,2),
    is_balanced BOOLEAN
) AS $$
DECLARE
    v_input NUMERIC(10,2);
    v_output NUMERIC(10,2);
    v_loss NUMERIC(10,2);
    v_reject NUMERIC(10,2);
    v_policy_id UUID;
    v_tolerance NUMERIC(5,3);
    v_accounted NUMERIC(10,2);
    v_diff NUMERIC(10,2);
    v_max_diff NUMERIC(10,2);
BEGIN
    -- Get batch totals and policy
    SELECT 
        total_input_weight_kg, 
        mass_balance_policy_id 
    INTO v_input, v_policy_id
    FROM processing_batches
    WHERE id = p_processing_batch_id;
    
    -- Sum actual outputs
    SELECT COALESCE(SUM(quantity_produced_kg), 0.00) INTO v_output
    FROM processing_outputs
    WHERE processing_batch_id = p_processing_batch_id;
    
    -- Sum actual losses
    SELECT COALESCE(SUM(loss_weight_kg), 0.00) INTO v_loss
    FROM processing_losses
    WHERE processing_batch_id = p_processing_batch_id;
    
    -- Sum actual rejects
    SELECT COALESCE(SUM(reject_weight_kg), 0.00) INTO v_reject
    FROM processing_rejects
    WHERE processing_batch_id = p_processing_batch_id;
    
    -- Get tolerance
    SELECT tolerance_pct INTO v_tolerance
    FROM mass_balance_policies
    WHERE id = v_policy_id;
    
    IF v_tolerance IS NULL THEN
        v_tolerance := 0.015; -- Fallback 1.5%
    END IF;
    
    v_accounted := v_output + v_loss + v_reject;
    v_diff := ABS(v_input - v_accounted);
    v_max_diff := v_input * v_tolerance;
    
    RETURN QUERY
    SELECT 
        v_input,
        v_accounted,
        v_diff,
        v_tolerance,
        v_max_diff,
        (v_diff <= v_max_diff);
END;
$$ LANGUAGE plpgsql STABLE;

-- 4. Pre-Harvest Interval (PHI) Compliance Check Function
CREATE OR REPLACE FUNCTION fn_check_phi_compliance(p_season_id UUID, p_harvest_date DATE)
RETURNS TABLE (
    is_compliant BOOLEAN,
    violating_activity_code VARCHAR(50),
    material_name VARCHAR(120),
    spray_date TIMESTAMPTZ,
    phi_days INT,
    safe_harvest_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        FALSE AS is_compliant,
        fa.activity_code,
        m.brand_name,
        fa.performed_at,
        mu.phi_days_applied,
        mu.earliest_safe_harvest_date
    FROM farm_activities fa
    JOIN material_usages mu ON mu.activity_id = fa.id
    JOIN materials m ON m.id = (SELECT material_id FROM material_batches WHERE id = mu.material_batch_id)
    WHERE fa.season_id = p_season_id
      AND mu.earliest_safe_harvest_date > p_harvest_date
    LIMIT 1;
    
    -- If no records returned, it means 100% compliant
END;
$$ LANGUAGE plpgsql STABLE;

-- 5. Geofence Verification Helper Function (Checks if lat/long is within Plot Polygon)
CREATE OR REPLACE FUNCTION fn_verify_geofence_point(p_plot_id UUID, p_latitude NUMERIC, p_longitude NUMERIC)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_inside BOOLEAN;
    v_point GEOMETRY(Point, 4326);
BEGIN
    v_point := ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326);
    
    SELECT ST_Contains(boundary_polygon, v_point) INTO v_is_inside
    FROM plots
    WHERE id = p_plot_id;
    
    RETURN COALESCE(v_is_inside, FALSE);
END;
$$ LANGUAGE plpgsql STABLE;
