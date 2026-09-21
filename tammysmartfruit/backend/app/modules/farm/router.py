"""
Farm, Farmer, and Plot REST API Endpoints (Modules 6 & 7)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.farm.service import FarmService
from app.modules.spatial.service import SpatialService
from app.modules.spatial.schemas import GeofenceEvaluationInput, GeofenceEvaluationResult
from app.modules.farm.schemas import (
    FarmerProfileCreate, FarmerProfileResponse,
    FarmCreate, FarmUpdate, FarmResponse, FarmDetailResponse,
    PlotCreate, PlotUpdate, PlotResponse
)

router = APIRouter(tags=["Farms & Plots"])

# --- Farmer Profile Endpoints ---
@router.get("/farmers", response_model=List[FarmerProfileResponse])
async def list_farmers(
    search: Optional[str] = Query(None, description="Search by name, username, or phone"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """List farmer profiles within authorized tenant data scope."""
    return await FarmService.list_farmers(db, principal=principal, search=search)

@router.post("/farmers", response_model=FarmerProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_farmer(
    payload: FarmerProfileCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Register a new farmer account and cooperative membership."""
    principal.require_permission("user:create")
    return await FarmService.create_farmer(db, data=payload, principal=principal)

# --- Farm Endpoints ---
@router.get("/farms", response_model=List[FarmResponse])
async def list_farms(
    growing_area_id: Optional[uuid.UUID] = Query(None),
    farmer_id: Optional[uuid.UUID] = Query(None),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """List farms with DataScope filtering."""
    return await FarmService.list_farms(
        db, principal=principal, growing_area_id=growing_area_id, farmer_id=farmer_id
    )

@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    payload: FarmCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Register a new farm under a Growing Area."""
    principal.require_permission("farm:create")
    return await FarmService.create_farm(db, data=payload, principal=principal)

@router.get("/farms/{farm_id}", response_model=FarmDetailResponse)
async def get_farm(
    farm_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Get full farm details with all plots and spatial boundaries."""
    return await FarmService.get_farm_by_id(db, farm_id=farm_id, principal=principal)

# --- Plot Endpoints ---
@router.get("/plots", response_model=List[PlotResponse])
async def list_plots(
    farm_id: Optional[uuid.UUID] = Query(None),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """List agricultural plots with GeoJSON polygon boundaries."""
    return await FarmService.list_plots(db, principal=principal, farm_id=farm_id)

@router.post("/plots", response_model=PlotResponse, status_code=status.HTTP_201_CREATED)
async def create_plot(
    payload: PlotCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Create a new plot with PostGIS polygon geometry validation."""
    principal.require_permission("farm:create")
    return await FarmService.create_plot(db, data=payload, principal=principal)

@router.get("/plots/{plot_id}", response_model=PlotResponse)
async def get_plot(
    plot_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Get plot details with PostGIS polygon boundary and tree groups."""
    return await FarmService.get_plot_by_id(db, plot_id=plot_id, principal=principal)

@router.post("/plots/{plot_id}/geofence-check", response_model=GeofenceEvaluationResult)
async def check_plot_geofence(
    plot_id: uuid.UUID,
    payload: GeofenceEvaluationInput,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate if captured GPS coordinate is INSIDE, NEAR_BOUNDARY, or OUTSIDE plot polygon."""
    # Ensure plot is accessible
    await FarmService.get_plot_by_id(db, plot_id=plot_id, principal=principal)
    return await SpatialService.evaluate_geofence(
        db,
        lat=payload.latitude,
        lng=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        plot_id=plot_id
    )
