"""
Farm, Farmer Profile, and Plot Domain Service (Modules 6 & 7)
Enforces PostGIS geometry validation, Multi-Tenant DataScope isolation,
Audit Logging, and Domain Event dispatching.
"""

import json
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.rbac import Principal, DataScope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException, ValidationException
from app.core.security import hash_password_argon2
from app.modules.identity.models import User, UserCredential, UserRole, Role
from app.modules.organization.models import Organization, UserOrganizationMembership, MembershipRole, DataScopeAssignment
from app.modules.growing_area.models import GrowingArea
from app.modules.farm.models import Farm, Plot, TreeGroup, FarmFarmerAssignment
from app.modules.master_data.models import CropVariety, CropVarietyTranslation
from app.modules.farm.schemas import (
    FarmerProfileCreate, FarmerProfileResponse,
    FarmCreate, FarmUpdate, FarmResponse, FarmDetailResponse,
    PlotCreate, PlotUpdate, PlotResponse, TreeGroupCreate, TreeGroupResponse
)
from app.modules.spatial.service import SpatialService
from app.modules.audit.service import AuditService
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.service import OutboxService

class FarmService:

    # =========================================================================
    # 1. FARMER PROFILE OPERATIONS
    # =========================================================================

    @classmethod
    async def list_farmers(
        cls,
        db: AsyncSession,
        principal: Principal,
        search: Optional[str] = None
    ) -> List[FarmerProfileResponse]:
        """List farmer profiles with DataScope tenant filtering."""
        query_str = """
            SELECT 
                u.id, u.username, u.full_name AS full_name_vi, u.phone_number, u.email,
                u.is_active, u.created_at,
                m.organization_id, o.org_name_vi AS org_name, m.membership_status,
                COUNT(DISTINCT f.id) AS farms_count,
                COALESCE(SUM(f.farm_area_hectares), 0.0) AS total_area_hectares
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id AND r.role_code = 'farmer'
            LEFT JOIN user_organization_memberships m ON m.user_id = u.id AND m.membership_status = 'ACTIVE'
            LEFT JOIN organizations o ON o.id = m.organization_id
            LEFT JOIN farms f ON f.owner_farmer_user_id = u.id AND f.is_active = TRUE
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        if principal.data_scope == DataScope.OWN:
            query_str += " AND u.id = :user_id"
            params["user_id"] = str(uuid.UUID(principal.user_id))
        elif principal.data_scope != DataScope.ALL and principal.organization_id:
            query_str += " AND m.organization_id = :org_id"
            params["org_id"] = str(uuid.UUID(principal.organization_id))

        if search:
            query_str += " AND (u.full_name ILIKE :search OR u.username ILIKE :search OR u.phone_number ILIKE :search)"
            params["search"] = f"%{search}%"

        query_str += " GROUP BY u.id, m.organization_id, o.org_name_vi, m.membership_status ORDER BY u.created_at DESC"

        res = await db.execute(text(query_str), params)
        rows = res.fetchall()

        return [
            FarmerProfileResponse(
                id=r.id,
                username=r.username,
                full_name_vi=r.full_name_vi,
                phone_number=r.phone_number,
                email=r.email,
                organization_id=r.organization_id,
                org_name=r.org_name,
                membership_status=r.membership_status,
                farms_count=r.farms_count,
                total_area_hectares=float(r.total_area_hectares),
                is_active=r.is_active,
                created_at=r.created_at
            )
            for r in rows
        ]

    @classmethod
    async def create_farmer(
        cls,
        db: AsyncSession,
        data: FarmerProfileCreate,
        principal: Principal
    ) -> FarmerProfileResponse:
        """Register a new farmer account, credential, membership, and 'farmer' role."""
        if principal.data_scope != DataScope.ALL and principal.organization_id != str(data.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # Check existing username
        u_check = await db.execute(select(User).where(User.username == data.username))
        if u_check.scalar_one_or_none():
            raise ConflictException(message_key="errors.identity.usernameExists", code="USERNAME_EXISTS")

        # 1. Create User
        new_user = User(
            username=data.username,
            full_name=data.full_name_vi,
            phone_number=data.phone_number,
            email=data.email,
            is_active=True
        )
        db.add(new_user)
        await db.flush()

        # 2. Create Credential
        password_hash = hash_password_argon2(data.password or "Farmer@123456")
        cred = UserCredential(
            user_id=new_user.id,
            password_hash=password_hash,
            password_algo="ARGON2ID"
        )
        db.add(cred)

        # 3. Assign Role 'farmer'
        role_res = await db.execute(select(Role).where(Role.role_code == "farmer"))
        farmer_role = role_res.scalar_one()
        user_role = UserRole(
            user_id=new_user.id,
            role_id=farmer_role.id,
            granted_by=uuid.UUID(principal.user_id)
        )
        db.add(user_role)

        # 4. Assign Organization Membership
        membership = UserOrganizationMembership(
            user_id=new_user.id,
            organization_id=data.organization_id,
            membership_status="ACTIVE"
        )
        db.add(membership)
        await db.flush()

        # Add membership role
        mem_role = MembershipRole(
            membership_id=membership.id,
            role_id=farmer_role.id
        )
        db.add(mem_role)

        # Add DataScope OWN
        scope_assign = DataScopeAssignment(
            membership_id=membership.id,
            scope_type="OWN"
        )
        db.add(scope_assign)

        # 5. Audit & Domain Event
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="CREATE",
            resource_type="FarmerProfile",
            resource_id=new_user.id,
            organization_id=data.organization_id,
            details={"username": data.username, "full_name": data.full_name_vi}
        )

        event = DomainEventEnvelope(
            event_type="FarmerProfileCreatedEvent",
            aggregate_type="FarmerProfile",
            aggregate_id=new_user.id,
            organization_id=data.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={"username": data.username, "full_name_vi": data.full_name_vi}
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return FarmerProfileResponse(
            id=new_user.id,
            username=new_user.username,
            full_name_vi=new_user.full_name,
            phone_number=new_user.phone_number,
            email=new_user.email,
            organization_id=data.organization_id,
            membership_status="ACTIVE",
            farms_count=0,
            total_area_hectares=0.0,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )

    # =========================================================================
    # 2. FARM OPERATIONS
    # =========================================================================

    @classmethod
    async def create_farm(
        cls,
        db: AsyncSession,
        data: FarmCreate,
        principal: Principal
    ) -> FarmResponse:
        """Create new Farm under Growing Area with DataScope validation."""
        if principal.data_scope != DataScope.ALL and principal.organization_id != str(data.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # Check unique farm_code
        fc_res = await db.execute(select(Farm).where(Farm.farm_code == data.farm_code))
        if fc_res.scalar_one_or_none():
            raise ConflictException(message_key="errors.farm.codeAlreadyExists", code="FARM_CODE_EXISTS")

        # Verify Growing Area belongs to same organization
        ga_res = await db.execute(select(GrowingArea).where(GrowingArea.id == data.growing_area_id))
        ga = ga_res.scalar_one_or_none()
        if not ga or ga.organization_id != data.organization_id:
            raise ValidationException(
                message_key="errors.farm.invalidGrowingArea",
                code="INVALID_GROWING_AREA",
                field_errors=[{"field": "growing_area_id", "message": "Growing Area not found in this organization"}]
            )

        # Verify Owner Farmer belongs to organization if provided
        if data.owner_farmer_user_id:
            m_res = await db.execute(
                select(UserOrganizationMembership).where(
                    and_(
                        UserOrganizationMembership.user_id == data.owner_farmer_user_id,
                        UserOrganizationMembership.organization_id == data.organization_id,
                        UserOrganizationMembership.membership_status == "ACTIVE"
                    )
                )
            )
            if not m_res.scalar_one_or_none():
                raise ValidationException(
                    message_key="errors.farm.farmerNotMember",
                    code="FARMER_NOT_ORG_MEMBER",
                    field_errors=[{"field": "owner_farmer_user_id", "message": "Farmer is not an active member of this organization"}]
                )

        farm = Farm(
            organization_id=data.organization_id,
            growing_area_id=data.growing_area_id,
            farm_code=data.farm_code,
            farm_name=data.farm_name,
            owner_farmer_user_id=data.owner_farmer_user_id,
            address_line=data.address_line,
            total_plots_count=0,
            farm_area_hectares=data.farm_area_hectares,
            is_active=True
        )
        db.add(farm)
        await db.flush()

        # If owner provided, add assignment
        if data.owner_farmer_user_id:
            assign = FarmFarmerAssignment(
                farm_id=farm.id,
                farmer_user_id=data.owner_farmer_user_id,
                assignment_role="PRIMARY_CULTIVATOR",
                is_active=True
            )
            db.add(assign)

        # Audit & Domain Event
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="CREATE",
            resource_type="Farm",
            resource_id=farm.id,
            organization_id=data.organization_id,
            details={"farm_code": data.farm_code, "farm_name": data.farm_name}
        )

        event = DomainEventEnvelope(
            event_type="FarmCreatedEvent",
            aggregate_type="Farm",
            aggregate_id=farm.id,
            organization_id=data.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={"farm_code": data.farm_code, "farm_name": data.farm_name, "growing_area_id": str(data.growing_area_id)}
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return await cls.get_farm_by_id(db, farm.id, principal)

    @classmethod
    async def list_farms(
        cls,
        db: AsyncSession,
        principal: Principal,
        growing_area_id: Optional[uuid.UUID] = None,
        farmer_id: Optional[uuid.UUID] = None
    ) -> List[FarmResponse]:
        """List farms with DataScope enforcement."""
        query_str = """
            SELECT 
                f.id, f.organization_id, o.org_name_vi AS org_name,
                f.growing_area_id, ga.area_name AS growing_area_name, ga.puc_registration_code,
                f.farm_code, f.farm_name, f.owner_farmer_user_id, u.full_name AS owner_name,
                f.address_line, f.total_plots_count, f.farm_area_hectares,
                f.is_active, f.created_at, f.updated_at
            FROM farms f
            JOIN organizations o ON o.id = f.organization_id
            JOIN growing_areas ga ON ga.id = f.growing_area_id
            LEFT JOIN users u ON u.id = f.owner_farmer_user_id
            LEFT JOIN farm_farmer_assignments fa ON fa.farm_id = f.id AND fa.is_active = TRUE
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        # DataScope isolation
        if principal.data_scope == DataScope.OWN:
            query_str += " AND (f.owner_farmer_user_id = :user_id OR fa.farmer_user_id = :user_id)"
            params["user_id"] = str(uuid.UUID(principal.user_id))
        elif principal.data_scope != DataScope.ALL and principal.organization_id:
            query_str += " AND f.organization_id = :org_id"
            params["org_id"] = str(uuid.UUID(principal.organization_id))

        if growing_area_id:
            query_str += " AND f.growing_area_id = :ga_id"
            params["ga_id"] = str(growing_area_id)
        if farmer_id:
            query_str += " AND (f.owner_farmer_user_id = :f_id OR fa.farmer_user_id = :f_id)"
            params["f_id"] = str(farmer_id)

        query_str += " GROUP BY f.id, o.org_name_vi, ga.area_name, ga.puc_registration_code, u.full_name ORDER BY f.created_at DESC"

        res = await db.execute(text(query_str), params)
        rows = res.fetchall()

        return [
            FarmResponse(
                id=r.id,
                organization_id=r.organization_id,
                org_name=r.org_name,
                growing_area_id=r.growing_area_id,
                growing_area_name=r.growing_area_name,
                puc_registration_code=r.puc_registration_code,
                farm_code=r.farm_code,
                farm_name=r.farm_name,
                owner_farmer_user_id=r.owner_farmer_user_id,
                owner_name=r.owner_name,
                address_line=r.address_line,
                total_plots_count=r.total_plots_count,
                farm_area_hectares=float(r.farm_area_hectares),
                is_active=r.is_active,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
            for r in rows
        ]

    @classmethod
    async def get_farm_by_id(
        cls,
        db: AsyncSession,
        farm_id: uuid.UUID,
        principal: Principal
    ) -> FarmDetailResponse:
        """Fetch farm details with all plots and spatial boundaries."""
        query_str = """
            SELECT 
                f.id, f.organization_id, o.org_name_vi AS org_name,
                f.growing_area_id, ga.area_name AS growing_area_name, ga.puc_registration_code,
                f.farm_code, f.farm_name, f.owner_farmer_user_id, u.full_name AS owner_name,
                f.address_line, f.total_plots_count, f.farm_area_hectares,
                f.is_active, f.created_at, f.updated_at
            FROM farms f
            JOIN organizations o ON o.id = f.organization_id
            JOIN growing_areas ga ON ga.id = f.growing_area_id
            LEFT JOIN users u ON u.id = f.owner_farmer_user_id
            WHERE f.id = :farm_id
        """
        res = await db.execute(text(query_str), {"farm_id": str(farm_id)})
        r = res.fetchone()
        if not r:
            raise NotFoundException(message_key="errors.farm.notFound", code="FARM_NOT_FOUND")

        # DataScope check
        if principal.data_scope == DataScope.OWN and str(r.owner_farmer_user_id) != principal.user_id:
            # Check assignment
            assign_check = await db.execute(
                select(FarmFarmerAssignment).where(
                    and_(
                        FarmFarmerAssignment.farm_id == farm_id,
                        FarmFarmerAssignment.farmer_user_id == uuid.UUID(principal.user_id),
                        FarmFarmerAssignment.is_active == True
                    )
                )
            )
            if not assign_check.scalar_one_or_none():
                raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")
        elif principal.data_scope != DataScope.ALL and principal.organization_id != str(r.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # Fetch Plots with GeoJSON boundaries
        plots_list = await cls.list_plots(db, principal=principal, farm_id=farm_id)

        return FarmDetailResponse(
            id=r.id,
            organization_id=r.organization_id,
            org_name=r.org_name,
            growing_area_id=r.growing_area_id,
            growing_area_name=r.growing_area_name,
            puc_registration_code=r.puc_registration_code,
            farm_code=r.farm_code,
            farm_name=r.farm_name,
            owner_farmer_user_id=r.owner_farmer_user_id,
            owner_name=r.owner_name,
            address_line=r.address_line,
            total_plots_count=len(plots_list),
            farm_area_hectares=float(r.farm_area_hectares),
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
            plots=plots_list
        )

    # =========================================================================
    # 3. PLOT OPERATIONS & POSTGIS POLYGONS
    # =========================================================================

    @classmethod
    async def create_plot(
        cls,
        db: AsyncSession,
        data: PlotCreate,
        principal: Principal
    ) -> PlotResponse:
        """Create new Plot with PostGIS spatial polygon validation and area computation."""
        # 1. Fetch Farm to verify scope & organization
        farm_res = await db.execute(select(Farm).where(Farm.id == data.farm_id))
        farm = farm_res.scalar_one_or_none()
        if not farm:
            raise NotFoundException(message_key="errors.farm.notFound", code="FARM_NOT_FOUND")

        if principal.data_scope == DataScope.OWN and str(farm.owner_farmer_user_id) != principal.user_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")
        elif principal.data_scope != DataScope.ALL and principal.organization_id != str(farm.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # 2. Check plot_code uniqueness
        p_check = await db.execute(select(Plot).where(Plot.plot_code == data.plot_code))
        if p_check.scalar_one_or_none():
            raise ConflictException(message_key="errors.plot.codeAlreadyExists", code="PLOT_CODE_EXISTS")

        # 3. PostGIS Geometry Validation & Area Calculation
        await SpatialService.validate_polygon_geometry(db, data.boundary_polygon)
        area_ha = await SpatialService.calculate_area_hectares(db, data.boundary_polygon)
        c_lng, c_lat = await SpatialService.get_centroid(db, data.boundary_polygon)

        geojson_str = json.dumps(data.boundary_polygon)
        new_plot_id = uuid.uuid4()

        # 4. Insert into PostgreSQL with PostGIS geometry
        insert_query = text("""
            INSERT INTO plots (
                id, farm_id, plot_code, plot_name, area_hectares,
                boundary_polygon, centroid_point, soil_type, topography,
                irrigation_system, is_active, created_at, updated_at
            ) VALUES (
                :id, :farm_id, :plot_code, :plot_name, :area_ha,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326),
                ST_SetSRID(ST_Point(:c_lng, :c_lat), 4326),
                :soil, :topo, :irrig, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """)
        await db.execute(insert_query, {
            "id": new_plot_id,
            "farm_id": data.farm_id,
            "plot_code": data.plot_code,
            "plot_name": data.plot_name,
            "area_ha": area_ha,
            "geom_json": geojson_str,
            "c_lng": c_lng,
            "c_lat": c_lat,
            "soil": data.soil_type,
            "topo": data.topography,
            "irrig": data.irrigation_system
        })

        # 5. Insert Tree Groups if provided
        if data.tree_groups:
            for tg in data.tree_groups:
                tree_group = TreeGroup(
                    plot_id=new_plot_id,
                    group_code=tg.group_code,
                    crop_variety_id=tg.crop_variety_id,
                    planting_date=tg.planting_date,
                    tree_count=tg.tree_count,
                    row_spacing_meters=tg.row_spacing_meters,
                    tree_spacing_meters=tg.tree_spacing_meters,
                    estimated_annual_yield_kg=tg.estimated_annual_yield_kg,
                    health_status=tg.health_status,
                    is_active=True
                )
                db.add(tree_group)

        # 6. Update Farm total plots count
        await db.execute(
            text("UPDATE farms SET total_plots_count = (SELECT COUNT(*) FROM plots WHERE farm_id = :fid) WHERE id = :fid"),
            {"fid": data.farm_id}
        )

        # 7. Audit & Domain Event
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="CREATE",
            resource_type="Plot",
            resource_id=new_plot_id,
            organization_id=farm.organization_id,
            details={"plot_code": data.plot_code, "area_ha": area_ha}
        )

        event = DomainEventEnvelope(
            event_type="PlotCreatedEvent",
            aggregate_type="Plot",
            aggregate_id=new_plot_id,
            organization_id=farm.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={"plot_code": data.plot_code, "farm_id": str(data.farm_id), "area_hectares": area_ha}
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return await cls.get_plot_by_id(db, new_plot_id, principal)

    @classmethod
    async def list_plots(
        cls,
        db: AsyncSession,
        principal: Principal,
        farm_id: Optional[uuid.UUID] = None
    ) -> List[PlotResponse]:
        """List plots with GeoJSON geometries and DataScope filtering."""
        query = select(Plot).join(Farm, Plot.farm_id == Farm.id).options(
            selectinload(Plot.farm),
            selectinload(Plot.tree_groups).selectinload(TreeGroup.variety).selectinload(CropVariety.translations)
        )

        if principal.data_scope == DataScope.OWN:
            query = query.where(Farm.owner_farmer_user_id == uuid.UUID(principal.user_id))
        elif principal.data_scope != DataScope.ALL and principal.organization_id:
            query = query.where(Farm.organization_id == uuid.UUID(principal.organization_id))

        if farm_id:
            query = query.where(Plot.farm_id == farm_id)

        query = query.order_by(Plot.created_at.asc())

        res = await db.execute(query)
        plots = res.scalars().all()

        output = []
        for p in plots:
            tg_out = []
            for tg in (p.tree_groups or []):
                v_name = tg.variety.variety_code if tg.variety else "Jackfruit"
                if tg.variety and tg.variety.translations:
                    v_name = tg.variety.translations[0].name
                tg_out.append(TreeGroupResponse(
                    id=tg.id,
                    plot_id=tg.plot_id,
                    group_code=tg.group_code,
                    crop_variety_id=tg.crop_variety_id,
                    variety_code=tg.variety.variety_code if tg.variety else "JKF-RD",
                    variety_name=v_name,
                    planting_date=tg.planting_date,
                    tree_count=tg.tree_count,
                    row_spacing_meters=float(tg.row_spacing_meters) if tg.row_spacing_meters else None,
                    tree_spacing_meters=float(tg.tree_spacing_meters) if tg.tree_spacing_meters else None,
                    estimated_annual_yield_kg=float(tg.estimated_annual_yield_kg) if tg.estimated_annual_yield_kg else 0.0,
                    health_status=tg.health_status,
                    is_active=tg.is_active
                ))

            b_geo = p.boundary_polygon if isinstance(p.boundary_polygon, dict) else json.loads(p.boundary_polygon) if isinstance(p.boundary_polygon, str) else None
            c_geo = p.centroid_point if isinstance(p.centroid_point, dict) else json.loads(p.centroid_point) if isinstance(p.centroid_point, str) else None

            output.append(PlotResponse(
                id=p.id,
                farm_id=p.farm_id,
                farm_name=p.farm.farm_name if p.farm else "",
                organization_id=p.farm.organization_id if p.farm else uuid.uuid4(),
                plot_code=p.plot_code,
                plot_name=p.plot_name,
                area_hectares=float(p.area_hectares) if p.area_hectares else 0.0,
                boundary_geojson=b_geo,
                centroid_geojson=c_geo,
                soil_type=p.soil_type,
                topography=p.topography,
                irrigation_system=p.irrigation_system,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
                tree_groups=tg_out
            ))

        return output

    @classmethod
    async def get_plot_by_id(
        cls,
        db: AsyncSession,
        plot_id: uuid.UUID,
        principal: Principal
    ) -> PlotResponse:
        """Fetch single plot with full PostGIS geometry and tree groups."""
        query = select(Plot).where(Plot.id == plot_id).options(
            selectinload(Plot.farm),
            selectinload(Plot.tree_groups).selectinload(TreeGroup.variety).selectinload(CropVariety.translations)
        )
        res = await db.execute(query)
        p = res.scalar_one_or_none()
        if not p:
            raise NotFoundException(message_key="errors.plot.notFound", code="PLOT_NOT_FOUND")

        # DataScope check
        if principal.data_scope == DataScope.OWN and str(p.farm.owner_farmer_user_id) != principal.user_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")
        elif principal.data_scope != DataScope.ALL and principal.organization_id != str(p.farm.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        tg_out = []
        for tg in (p.tree_groups or []):
            v_name = tg.variety.variety_code if tg.variety else "Jackfruit"
            if tg.variety and tg.variety.translations:
                v_name = tg.variety.translations[0].name
            tg_out.append(TreeGroupResponse(
                id=tg.id,
                plot_id=tg.plot_id,
                group_code=tg.group_code,
                crop_variety_id=tg.crop_variety_id,
                variety_code=tg.variety.variety_code if tg.variety else "JKF-RD",
                variety_name=v_name,
                planting_date=tg.planting_date,
                tree_count=tg.tree_count,
                row_spacing_meters=float(tg.row_spacing_meters) if tg.row_spacing_meters else None,
                tree_spacing_meters=float(tg.tree_spacing_meters) if tg.tree_spacing_meters else None,
                estimated_annual_yield_kg=float(tg.estimated_annual_yield_kg) if tg.estimated_annual_yield_kg else 0.0,
                health_status=tg.health_status,
                is_active=tg.is_active
            ))

        b_geo = p.boundary_polygon if isinstance(p.boundary_polygon, dict) else json.loads(p.boundary_polygon) if isinstance(p.boundary_polygon, str) else None
        c_geo = p.centroid_point if isinstance(p.centroid_point, dict) else json.loads(p.centroid_point) if isinstance(p.centroid_point, str) else None

        return PlotResponse(
            id=p.id,
            farm_id=p.farm_id,
            farm_name=p.farm.farm_name if p.farm else "",
            organization_id=p.farm.organization_id if p.farm else uuid.uuid4(),
            plot_code=p.plot_code,
            plot_name=p.plot_name,
            area_hectares=float(p.area_hectares) if p.area_hectares else 0.0,
            boundary_geojson=b_geo,
            centroid_geojson=c_geo,
            soil_type=p.soil_type,
            topography=p.topography,
            irrigation_system=p.irrigation_system,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
            tree_groups=tg_out
        )
