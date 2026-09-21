"""
Global Multi-Tenant Search Service
Fast unified search across Farmers, Growing Areas, Farms, and Plots with DataScope enforcement.
"""

from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import Principal, DataScope
from app.modules.search.schemas import SearchResultItem, GlobalSearchResponse

class GlobalSearchService:

    @classmethod
    async def search(
        cls,
        db: AsyncSession,
        query: str,
        principal: Principal,
        limit: int = 20
    ) -> GlobalSearchResponse:
        """Execute multi-entity search with DataScope filtering."""
        if not query or len(query.strip()) < 1:
            return GlobalSearchResponse(query=query, total_count=0, results=[])

        q = f"%{query.strip()}%"
        results: List[SearchResultItem] = []
        org_filter = ""
        params: Dict[str, Any] = {"q": q, "limit": limit}

        if principal.data_scope != DataScope.ALL and principal.organization_id:
            org_filter = " AND organization_id = :org_id"
            params["org_id"] = str(uuid.UUID(principal.organization_id))

        # 1. Search Growing Areas
        ga_query = text(f"""
            SELECT id, area_code, area_name, puc_registration_code, organization_id, puc_status
            FROM growing_areas
            WHERE (area_code ILIKE :q OR area_name ILIKE :q OR puc_registration_code ILIKE :q)
            {org_filter}
            LIMIT :limit
        """)
        ga_res = await db.execute(ga_query, params)
        for r in ga_res.fetchall():
            results.append(SearchResultItem(
                id=r.id,
                category="GROWING_AREA",
                title=r.area_name,
                subtitle=f"PUC: {r.puc_registration_code}",
                code=r.area_code,
                organization_id=r.organization_id,
                status=r.puc_status,
                extra_data={"puc": r.puc_registration_code}
            ))

        # 2. Search Farms
        farm_query = text(f"""
            SELECT f.id, f.farm_code, f.farm_name, f.organization_id, f.is_active, u.full_name AS owner_name
            FROM farms f
            LEFT JOIN users u ON u.id = f.owner_farmer_user_id
            WHERE (f.farm_code ILIKE :q OR f.farm_name ILIKE :q OR u.full_name ILIKE :q)
            {org_filter}
            LIMIT :limit
        """)
        farm_res = await db.execute(farm_query, params)
        for r in farm_res.fetchall():
            results.append(SearchResultItem(
                id=r.id,
                category="FARM",
                title=r.farm_name,
                subtitle=f"Chủ hộ: {r.owner_name or 'N/A'}",
                code=r.farm_code,
                organization_id=r.organization_id,
                status="ACTIVE" if r.is_active else "INACTIVE"
            ))

        # 3. Search Plots
        plot_query = text(f"""
            SELECT p.id, p.plot_code, p.plot_name, f.organization_id, f.farm_name, p.is_active
            FROM plots p
            JOIN farms f ON p.farm_id = f.id
            WHERE (p.plot_code ILIKE :q OR p.plot_name ILIKE :q)
            {org_filter.replace('organization_id', 'f.organization_id')}
            LIMIT :limit
        """)
        plot_res = await db.execute(plot_query, params)
        for r in plot_res.fetchall():
            results.append(SearchResultItem(
                id=r.id,
                category="PLOT",
                title=f"{r.plot_name} ({r.plot_code})",
                subtitle=f"Nông trại: {r.farm_name}",
                code=r.plot_code,
                organization_id=r.organization_id,
                status="ACTIVE" if r.is_active else "INACTIVE"
            ))

        # 4. Search Farmers
        farmer_filter = ""
        if principal.data_scope != DataScope.ALL and principal.organization_id:
            farmer_filter = " AND m.organization_id = :org_id"

        farmer_query = text(f"""
            SELECT u.id, u.username, u.full_name AS full_name_vi, u.phone_number, m.organization_id, u.is_active
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id AND r.role_code = 'farmer'
            LEFT JOIN user_organization_memberships m ON m.user_id = u.id AND m.membership_status = 'ACTIVE'
            WHERE (u.full_name ILIKE :q OR u.username ILIKE :q OR u.phone_number ILIKE :q)
            {farmer_filter}
            LIMIT :limit
        """)
        farmer_res = await db.execute(farmer_query, params)
        for r in farmer_res.fetchall():
            results.append(SearchResultItem(
                id=r.id,
                category="FARMER",
                title=r.full_name_vi,
                subtitle=f"SĐT: {r.phone_number} | @{r.username}",
                code=r.username,
                organization_id=r.organization_id,
                status="ACTIVE" if r.is_active else "INACTIVE"
            ))

        return GlobalSearchResponse(
            query=query,
            total_count=len(results),
            results=results[:limit]
        )
