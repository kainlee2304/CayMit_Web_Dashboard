"""
API V1 Router Aggregator
Mounts all Modular Monolith V1 Domain Endpoints.
"""

from fastapi import APIRouter
from app.modules.identity.router import router as auth_router
from app.modules.organization.router import router as org_router
from app.modules.master_data.router import router as master_data_router
from app.modules.growing_area.router import router as growing_area_router
from app.modules.farm.router import router as farm_router
from app.modules.claims.router import router as claims_router
from app.modules.search.router import router as search_router
from app.modules.season.router import router as season_router
from app.modules.farm_activity.router import router as farm_activity_router
from app.modules.material.router import router as material_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(org_router)
api_v1_router.include_router(master_data_router)
api_v1_router.include_router(growing_area_router)
api_v1_router.include_router(farm_router)
api_v1_router.include_router(claims_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(season_router)
api_v1_router.include_router(farm_activity_router)
api_v1_router.include_router(material_router)
