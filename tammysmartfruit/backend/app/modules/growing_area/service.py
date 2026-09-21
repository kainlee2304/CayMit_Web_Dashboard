"""
Growing Area Service (Module 5)
Handles PUC lifecycle, PostGIS boundary calculations, RBAC filtering, and domain events.
"""

import json
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.rbac import Principal, DataScope, enforce_data_scope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException
from app.modules.growing_area.models import GrowingArea
from app.modules.growing_area.schemas import (
    GrowingAreaCreate, GrowingAreaUpdate, GrowingAreaResponse, GrowingAreaDetailResponse
)
from app.modules.spatial.service import SpatialService
from app.modules.audit.service import AuditService
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.service import OutboxService

class GrowingAreaService:

    @classmethod
    async def create_growing_area(
        cls,
        db: AsyncSession,
        data: GrowingAreaCreate,
        principal: Principal
    ) -> GrowingAreaResponse:
        """Create growing area with PostGIS spatial polygon validation and area computation."""
        # 1. Scope and RBAC Check
        if principal.data_scope != DataScope.ALL and principal.organization_id != str(data.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # 2. Check Uniqueness
        code_check = await db.execute(
            select(GrowingArea).where(
                (GrowingArea.area_code == data.area_code) | 
                (GrowingArea.puc_registration_code == data.puc_registration_code)
            )
        )
        if code_check.scalar_one_or_none():
            raise ConflictException(
                message_key="errors.growing_area.codeAlreadyExists",
                code="GROWING_AREA_CODE_EXISTS"
            )

        # 3. PostGIS Geometry Validation & Area Calculation
        await SpatialService.validate_polygon_geometry(db, data.boundary_polygon)
        area_ha = await SpatialService.calculate_area_hectares(db, data.boundary_polygon)
        centroid_lng, centroid_lat = await SpatialService.get_centroid(db, data.boundary_polygon)

        geojson_str = json.dumps(data.boundary_polygon)
        
        # 4. Insert into PostgreSQL with PostGIS geometry functions
        insert_query = text("""
            INSERT INTO growing_areas (
                id, organization_id, area_code, area_name, puc_registration_code,
                puc_issued_at, puc_expires_at, puc_status, province_code, district_code,
                commune_code, total_area_hectares, boundary_polygon, centroid_point,
                created_by, created_at, updated_at
            ) VALUES (
                :id, :org_id, :area_code, :area_name, :puc_code,
                :puc_issued, :puc_expires, :puc_status, :province, :district,
                :commune, :area_ha,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326),
                ST_SetSRID(ST_Point(:c_lng, :c_lat), 4326),
                :created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id, created_at, updated_at
        """)
        new_id = uuid.uuid4()
        res = await db.execute(insert_query, {
            "id": new_id,
            "org_id": data.organization_id,
            "area_code": data.area_code,
            "area_name": data.area_name,
            "puc_code": data.puc_registration_code,
            "puc_issued": data.puc_issued_at,
            "puc_expires": data.puc_expires_at,
            "puc_status": data.puc_status,
            "province": data.province_code,
            "district": data.district_code,
            "commune": data.commune_code,
            "area_ha": area_ha,
            "geom_json": geojson_str,
            "c_lng": centroid_lng,
            "c_lat": centroid_lat,
            "created_by": uuid.UUID(principal.user_id)
        })
        row = res.fetchone()

        # 5. Audit Logging
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="CREATE",
            resource_type="GrowingArea",
            resource_id=new_id,
            organization_id=data.organization_id,
            details={"area_code": data.area_code, "puc": data.puc_registration_code, "area_ha": area_ha}
        )

        # 6. Domain Event Enqueueing
        event = DomainEventEnvelope(
            event_type="GrowingAreaRegisteredEvent",
            aggregate_type="GrowingArea",
            aggregate_id=new_id,
            organization_id=data.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "area_code": data.area_code,
                "puc_registration_code": data.puc_registration_code,
                "area_name": data.area_name,
                "total_area_hectares": area_ha
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return await cls.get_growing_area_by_id(db, new_id, principal)

    @classmethod
    async def list_growing_areas(
        cls,
        db: AsyncSession,
        principal: Principal,
        province_code: Optional[str] = None,
        puc_status: Optional[str] = None
    ) -> List[GrowingAreaResponse]:
        """List growing areas with DataScope filtering and GeoJSON boundary extraction."""
        query_str = """
            SELECT 
                g.id, g.organization_id, o.org_name_vi AS org_name,
                g.area_code, g.area_name, g.puc_registration_code,
                g.puc_issued_at, g.puc_expires_at, g.puc_status,
                g.province_code, g.district_code, g.commune_code,
                g.total_area_hectares,
                ST_AsGeoJSON(g.boundary_polygon)::json AS boundary_geojson,
                ST_AsGeoJSON(g.centroid_point)::json AS centroid_geojson,
                COUNT(f.id) AS farms_count,
                g.created_at, g.updated_at
            FROM growing_areas g
            JOIN organizations o ON g.organization_id = o.id
            LEFT JOIN farms f ON f.growing_area_id = g.id
            WHERE 1=1
        """
        query = select(GrowingArea).options(
            selectinload(GrowingArea.organization),
            selectinload(GrowingArea.farms)
        )

        if principal.data_scope != DataScope.ALL and principal.organization_id:
            query = query.where(GrowingArea.organization_id == uuid.UUID(principal.organization_id))
        if province_code:
            query = query.where(GrowingArea.province_code == province_code)
        if puc_status:
            query = query.where(GrowingArea.puc_status == puc_status)

        query = query.order_by(GrowingArea.created_at.desc())

        res = await db.execute(query)
        areas = res.scalars().all()

        return [
            GrowingAreaResponse(
                id=ga.id,
                organization_id=ga.organization_id,
                org_name=ga.organization.org_name_vi if ga.organization else "HTX Tam Mỹ",
                area_code=ga.area_code,
                area_name=ga.area_name,
                puc_registration_code=ga.puc_registration_code,
                puc_issued_at=ga.puc_issued_at,
                puc_expires_at=ga.puc_expires_at,
                puc_status=ga.puc_status,
                province_code=ga.province_code,
                district_code=ga.district_code,
                commune_code=ga.commune_code,
                total_area_hectares=float(ga.total_area_hectares) if ga.total_area_hectares else 0.0,
                boundary_geojson=ga.boundary_polygon if isinstance(ga.boundary_polygon, dict) else json.loads(ga.boundary_polygon) if isinstance(ga.boundary_polygon, str) else None,
                centroid_geojson=ga.centroid_point if isinstance(ga.centroid_point, dict) else json.loads(ga.centroid_point) if isinstance(ga.centroid_point, str) else None,
                farms_count=len(ga.farms) if ga.farms else 0,
                created_at=ga.created_at,
                updated_at=ga.updated_at
            )
            for ga in areas
        ]

    @classmethod
    async def get_growing_area_by_id(
        cls,
        db: AsyncSession,
        area_id: uuid.UUID,
        principal: Principal
    ) -> GrowingAreaDetailResponse:
        """Fetch single growing area with full GeoJSON and associated farms."""
        query = select(GrowingArea).where(GrowingArea.id == area_id).options(
            selectinload(GrowingArea.organization),
            selectinload(GrowingArea.farms)
        )
        res = await db.execute(query)
        ga = res.scalar_one_or_none()
        if not ga:
            raise NotFoundException(message_key="errors.growing_area.notFound", code="GROWING_AREA_NOT_FOUND")

        if principal.data_scope != DataScope.ALL and principal.organization_id != str(ga.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        farms_list = [
            {
                "id": str(f.id),
                "farm_code": f.farm_code,
                "farm_name": f.farm_name,
                "farm_area_hectares": float(f.farm_area_hectares) if f.farm_area_hectares else 0.0,
                "is_active": f.is_active
            }
            for f in (ga.farms or [])
        ]

        return GrowingAreaDetailResponse(
            id=ga.id,
            organization_id=ga.organization_id,
            org_name=ga.organization.org_name_vi if ga.organization else "HTX Tam Mỹ",
            area_code=ga.area_code,
            area_name=ga.area_name,
            puc_registration_code=ga.puc_registration_code,
            puc_issued_at=ga.puc_issued_at,
            puc_expires_at=ga.puc_expires_at,
            puc_status=ga.puc_status,
            province_code=ga.province_code,
            district_code=ga.district_code,
            commune_code=ga.commune_code,
            total_area_hectares=float(ga.total_area_hectares) if ga.total_area_hectares else 0.0,
            boundary_geojson=ga.boundary_polygon if isinstance(ga.boundary_polygon, dict) else json.loads(ga.boundary_polygon) if isinstance(ga.boundary_polygon, str) else None,
            centroid_geojson=ga.centroid_point if isinstance(ga.centroid_point, dict) else json.loads(ga.centroid_point) if isinstance(ga.centroid_point, str) else None,
            farms_count=len(ga.farms) if ga.farms else 0,
            created_at=ga.created_at,
            updated_at=ga.updated_at,
            farms=farms_list
        )

    @classmethod
    async def verify_growing_area(
        cls,
        db: AsyncSession,
        area_id: uuid.UUID,
        new_status: str,
        principal: Principal
    ) -> GrowingAreaDetailResponse:
        """Contextual state verification action (ACTIVE, SUSPENDED, REVOKED)."""
        area = await cls.get_growing_area_by_id(db, area_id, principal)

        allowed_transitions = ["ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED"]
        if new_status not in allowed_transitions:
            raise ForbiddenException(message_key="errors.growing_area.invalidStatusTransition", code="INVALID_STATUS")

        update_query = text("""
            UPDATE growing_areas
            SET puc_status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        await db.execute(update_query, {"status": new_status, "id": area_id})

        # Audit
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="VERIFY",
            resource_type="GrowingArea",
            resource_id=area_id,
            organization_id=area.organization_id,
            details={"old_status": area.puc_status, "new_status": new_status}
        )

        return await cls.get_growing_area_by_id(db, area_id, principal)
