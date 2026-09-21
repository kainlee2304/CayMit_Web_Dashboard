"""
Spatial PostGIS & Geofence Policy Test Suite
Executes real spatial queries against PostgreSQL 16 + PostGIS extension.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.spatial.service import SpatialService
from app.modules.spatial.schemas import GeofenceStatus
from app.modules.farm.models import Plot
from app.core.errors import ValidationException

@pytest.mark.asyncio
async def test_valid_polygon_geometry_and_area_calculation(db_session: AsyncSession):
    # Valid square polygon (~ 1km x 1km = ~100 ha)
    valid_poly = {
        "type": "Polygon",
        "coordinates": [[
            [108.6000, 15.4000],
            [108.6100, 15.4000],
            [108.6100, 15.4100],
            [108.6000, 15.4100],
            [108.6000, 15.4000]
        ]]
    }
    # 1. Validation
    is_valid = await SpatialService.validate_polygon_geometry(db_session, valid_poly)
    assert is_valid is True

    # 2. Area Calculation in Hectares
    area_ha = await SpatialService.calculate_area_hectares(db_session, valid_poly)
    assert area_ha > 100.0 and area_ha < 130.0

    # 3. Centroid calculation
    lng, lat = await SpatialService.get_centroid(db_session, valid_poly)
    assert round(lng, 3) == 108.605
    assert round(lat, 3) == 15.405

@pytest.mark.asyncio
async def test_self_intersecting_polygon_is_rejected_by_postgis(db_session: AsyncSession):
    # Invalid "Bowtie" Self-Intersecting Polygon
    invalid_bowtie_poly = {
        "type": "Polygon",
        "coordinates": [[
            [108.6000, 15.4000],
            [108.6100, 15.4100],
            [108.6100, 15.4000],
            [108.6000, 15.4100],
            [108.6000, 15.4000]
        ]]
    }
    with pytest.raises(ValidationException) as exc_info:
        await SpatialService.validate_polygon_geometry(db_session, invalid_bowtie_poly)
    assert exc_info.value.code == "INVALID_GEOMETRY"

@pytest.mark.asyncio
async def test_real_geofence_policy_evaluation(db_session: AsyncSession):
    # Find seeded Plot A: PLOT-TAMMY-001-A ([108.6210, 15.4210] to [108.6260, 15.4260])
    res = await db_session.execute(select(Plot).where(Plot.plot_code == "PLOT-TAMMY-001-A"))
    plot = res.scalar_one()

    # 1. Point strictly INSIDE plot center ([108.6235, 15.4235])
    res_inside = await SpatialService.evaluate_geofence(
        db=db_session,
        lat=15.4235,
        lng=108.6235,
        accuracy_meters=4.0,
        plot_id=plot.id
    )
    assert res_inside.status == GeofenceStatus.INSIDE
    assert res_inside.is_trusted is True
    assert res_inside.risk_points == 0.0

    # 2. Point NEAR BOUNDARY (10 meters outside perimeter: lat=15.4209, lng=108.6235)
    res_near = await SpatialService.evaluate_geofence(
        db=db_session,
        lat=15.4209,
        lng=108.6235,
        accuracy_meters=5.0,
        plot_id=plot.id
    )
    assert res_near.status == GeofenceStatus.NEAR_BOUNDARY
    assert res_near.distance_meters > 0.0 and res_near.distance_meters <= 25.0
    assert res_near.risk_points == 5.0

    # 3. Point completely OUTSIDE (500 meters away: lat=15.4150, lng=108.6235)
    res_outside = await SpatialService.evaluate_geofence(
        db=db_session,
        lat=15.4150,
        lng=108.6235,
        accuracy_meters=5.0,
        plot_id=plot.id
    )
    assert res_outside.status == GeofenceStatus.OUTSIDE
    assert res_outside.distance_meters > 25.0
    assert res_outside.is_trusted is False
    assert res_outside.risk_points == 80.0

    # 4. Point with LOW ACCURACY (> 50m accuracy error)
    res_low_acc = await SpatialService.evaluate_geofence(
        db=db_session,
        lat=15.4235,
        lng=108.6235,
        accuracy_meters=65.0,
        plot_id=plot.id
    )
    assert res_low_acc.status == GeofenceStatus.LOW_ACCURACY
    assert res_low_acc.is_trusted is False
    assert res_low_acc.risk_points == 25.0

@pytest.mark.asyncio
async def test_bbox_viewport_spatial_query(db_session: AsyncSession):
    # Query bounding box covering Tam My area ([108.60, 15.40] to [108.65, 15.45])
    plots = await SpatialService.get_plots_in_bbox(
        db=db_session,
        min_lng=108.60,
        min_lat=15.40,
        max_lng=108.65,
        max_lat=15.45
    )
    assert len(plots) >= 1
    assert any(p["plot_code"] == "PLOT-TAMMY-001-A" for p in plots)
    assert "boundary_geojson" in plots[0]
