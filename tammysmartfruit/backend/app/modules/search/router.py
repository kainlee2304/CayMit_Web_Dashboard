"""
Global Search REST API Router
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal
from app.modules.search.service import GlobalSearchService
from app.modules.search.schemas import GlobalSearchResponse

router = APIRouter(prefix="/search", tags=["Global Search"])

@router.get("", response_model=GlobalSearchResponse)
async def search_agricultural_entities(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Global search across Farmers, Growing Areas, Farms, and Plots with DataScope enforcement."""
    return await GlobalSearchService.search(db, query=q, principal=principal, limit=limit)
