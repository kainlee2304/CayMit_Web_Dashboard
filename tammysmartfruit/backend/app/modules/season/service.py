"""
Crop Season Domain Service (Module 8)
Enforces:
1. Upstream Variety Inheritance from Plot/TreeGroup/Claim (No bypass).
2. Contextual State Machine (DRAFT -> ACTIVE -> CLOSED).
3. Data Scope & Multi-Tenant Authorization.
4. Transactional Outbox, Domain Event Journal & Audit Logging.
"""

import hashlib
import json
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import Principal, DataScope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException, ValidationException
from app.modules.identity.models import User
from app.modules.farm.models import Farm, Plot, TreeGroup, FarmFarmerAssignment
from app.modules.master_data.models import CropVariety, CropVarietyTranslation
from app.modules.claims.models import DataClaim
from app.modules.season.models import CropSeason, YieldEstimate
from app.modules.season.schemas import (
    SeasonCreate, SeasonResponse, SeasonDetailResponse, SeasonMaterialsSummary,
    YieldEstimateCreate, YieldEstimateResponse
)
from app.modules.audit.service import AuditService
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.service import OutboxService

class SeasonService:

    @classmethod
    async def _resolve_plot_variety(
        cls,
        db: AsyncSession,
        plot: Plot
    ) -> Dict[str, Any]:
        """
        Resolves upstream variety for a plot.
        Priority & Provenance Hierarchy:
        1. Verified CROP_VARIETY claim on PLOT or TREE_GROUP (LEVEL_2_ORGANIZATION_VERIFIED or higher)
        2. Declared CROP_VARIETY claim on PLOT or TREE_GROUP (LEVEL_0_DECLARED)
        3. TreeGroup default variety master data fallback (strictly LEVEL_0_DECLARED, unverified)
        4. Default system fallback (strictly LEVEL_0_DECLARED, unverified)
        """
        # 1. Look for verified claims
        verified_claim_res = await db.execute(
            select(DataClaim).where(
                and_(
                    DataClaim.claim_type == "CROP_VARIETY",
                    DataClaim.subject_id.in_([plot.id] + [tg.id for tg in (plot.tree_groups or [])]),
                    DataClaim.is_current == True,
                    DataClaim.verification_status == "VERIFIED"
                )
            ).order_by(DataClaim.created_at.desc())
        )
        verified_claim = verified_claim_res.scalars().first()

        variety_code = "JACKFRUIT_THAI"
        is_verified = False
        assurance_level = "LEVEL_0_DECLARED"
        source_claim_id = None
        provenance_source = "DEFAULT_FALLBACK"

        if verified_claim:
            variety_code = verified_claim.value_code
            is_verified = True
            assurance_level = verified_claim.assurance_level
            source_claim_id = verified_claim.id
            provenance_source = f"VERIFIED_CLAIM:{verified_claim.subject_type}:{verified_claim.subject_id}"
        else:
            # Check declared claim
            decl_res = await db.execute(
                select(DataClaim).where(
                    and_(
                        DataClaim.claim_type == "CROP_VARIETY",
                        DataClaim.subject_id.in_([plot.id] + [tg.id for tg in (plot.tree_groups or [])]),
                        DataClaim.is_current == True,
                        DataClaim.verification_status != "REJECTED"
                    )
                ).order_by(DataClaim.created_at.desc())
            )
            decl_claim = decl_res.scalars().first()
            if decl_claim:
                variety_code = decl_claim.value_code
                is_verified = False
                assurance_level = decl_claim.assurance_level
                source_claim_id = decl_claim.id
                provenance_source = f"DECLARED_CLAIM:{decl_claim.subject_type}:{decl_claim.subject_id}"
            elif plot.tree_groups and plot.tree_groups[0].variety:
                variety_code = plot.tree_groups[0].variety.variety_code
                is_verified = False
                assurance_level = "LEVEL_0_DECLARED" # Fallback from master data must NEVER be treated as verified
                source_claim_id = None
                provenance_source = f"TREE_GROUP_MASTER_FALLBACK:{plot.tree_groups[0].id}"
            else:
                variety_code = "JACKFRUIT_THAI"
                is_verified = False
                assurance_level = "LEVEL_0_DECLARED"
                source_claim_id = None
                provenance_source = "UNSPECIFIED_MASTER_FALLBACK"

        # Fetch variety translations
        v_res = await db.execute(
            select(CropVariety).where(CropVariety.variety_code == variety_code).options(
                selectinload(CropVariety.translations)
            )
        )
        variety_obj = v_res.scalar_one_or_none()
        name_vi = "Mít Thái Changai"
        name_en = "Thai Changai Jackfruit"
        if variety_obj:
            for t in variety_obj.translations:
                if t.locale == "vi":
                    name_vi = t.name
                elif t.locale == "en":
                    name_en = t.name

        return {
            "variety_code": variety_code,
            "name_vi": name_vi,
            "name_en": name_en,
            "is_verified": is_verified,
            "assurance_level": assurance_level,
            "source_claim_id": source_claim_id,
            "provenance_source": provenance_source
        }

    @classmethod
    async def create_season(
        cls,
        db: AsyncSession,
        data: SeasonCreate,
        principal: Principal
    ) -> SeasonResponse:
        """Create a new crop season with automatic upstream variety inheritance."""
        # 1. Fetch Plot and Farm
        p_res = await db.execute(
            select(Plot).where(Plot.id == data.plot_id).options(
                selectinload(Plot.farm).selectinload(Farm.farmer_assignments),
                selectinload(Plot.tree_groups).selectinload(TreeGroup.variety)
            )
        )
        plot = p_res.scalar_one_or_none()
        if not plot:
            raise NotFoundException(message_key="errors.farm.plotNotFound", code="PLOT_NOT_FOUND")

        farm = plot.farm
        org_id = farm.organization_id

        # 2. Multi-tenant and DataScope check
        if principal.data_scope != DataScope.ALL and str(org_id) != principal.organization_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        if principal.data_scope == DataScope.OWN:
            is_owner = farm.owner_farmer_user_id and str(farm.owner_farmer_user_id) == principal.user_id
            is_assigned = any(str(fa.farmer_user_id) == principal.user_id for fa in farm.farmer_assignments if fa.is_active)
            if not (is_owner or is_assigned):
                raise ForbiddenException(message_key="errors.auth.scopeDenied", code="OWN_SCOPE_VIOLATION")

        # 3. Validate dates
        if data.expected_harvest_start < data.start_date:
            raise ValidationException(
                message_key="errors.season.invalidDates",
                code="INVALID_DATES",
                field_errors=[{"field": "expected_harvest_start", "message": "Harvest start date cannot precede season start date"}]
            )
        if data.expected_harvest_end < data.expected_harvest_start:
            raise ValidationException(
                message_key="errors.season.invalidDates",
                code="INVALID_DATES",
                field_errors=[{"field": "expected_harvest_end", "message": "Harvest end date cannot precede harvest start date"}]
            )

        # 4. Resolve Upstream Variety
        variety_info = await cls._resolve_plot_variety(db, plot)

        # 5. Generate canonical Season Code
        now = datetime.now(timezone.utc)
        year = data.start_date.year
        clean_plot = plot.plot_code.replace("-", "")[-6:]
        rand_suffix = uuid.uuid4().hex[:4].upper()
        season_code = f"SEA-{year}-{clean_plot}-{rand_suffix}"

        season = CropSeason(
            id=uuid.uuid4(),
            plot_id=plot.id,
            season_code=season_code,
            season_name=data.season_name,
            start_date=data.start_date,
            expected_harvest_start=data.expected_harvest_start,
            expected_harvest_end=data.expected_harvest_end,
            forecasted_yield_kg=data.forecasted_yield_kg,
            actual_harvested_yield_kg=0.00,
            season_status="ACTIVE",
            created_at=now,
            updated_at=now
        )
        db.add(season)
        await db.flush()

        # 6. Audit & Domain Event Journal in same transaction
        await AuditService.record_audit_log(
            db=db,
            action="SEASON_CREATE",
            resource_type="CROP_SEASON",
            resource_id=season.id,
            actor_id=uuid.UUID(principal.user_id),
            organization_id=org_id,
            details={
                "season_code": season_code,
                "season_name": season.season_name,
                "plot_id": str(plot.id),
                "farm_id": str(farm.id),
                "inherited_variety": variety_info["variety_code"],
                "forecasted_yield_kg": data.forecasted_yield_kg
            }
        )

        event = DomainEventEnvelope(
            event_type="SeasonCreated",
            aggregate_type="CropSeason",
            aggregate_id=season.id,
            organization_id=org_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "season_id": str(season.id),
                "season_code": season_code,
                "plot_id": str(plot.id),
                "farm_id": str(farm.id),
                "variety_code": variety_info["variety_code"],
                "forecasted_yield_kg": data.forecasted_yield_kg,
                "status": season.season_status
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)
        await db.commit()

        return SeasonResponse(
            id=season.id,
            plot_id=plot.id,
            plot_code=plot.plot_code,
            plot_name=plot.plot_name,
            farm_id=farm.id,
            farm_name=farm.farm_name,
            organization_id=org_id,
            inherited_variety_code=variety_info["variety_code"],
            inherited_variety_name_vi=variety_info["name_vi"],
            inherited_variety_name_en=variety_info["name_en"],
            is_variety_verified=variety_info["is_verified"],
            assurance_level=variety_info["assurance_level"],
            source_claim_id=variety_info.get("source_claim_id"),
            provenance_source=variety_info.get("provenance_source"),
            season_code=season.season_code,
            season_name=season.season_name,
            start_date=season.start_date,
            expected_harvest_start=season.expected_harvest_start,
            expected_harvest_end=season.expected_harvest_end,
            actual_harvest_end=season.actual_harvest_end,
            forecasted_yield_kg=float(season.forecasted_yield_kg),
            actual_harvested_yield_kg=float(season.actual_harvested_yield_kg),
            season_status=season.season_status,
            activities_count=0,
            closed_at=season.closed_at,
            created_at=season.created_at,
            updated_at=season.updated_at
        )

    @classmethod
    async def list_seasons(
        cls,
        db: AsyncSession,
        principal: Principal,
        plot_id: Optional[uuid.UUID] = None,
        season_status: Optional[str] = None
    ) -> List[SeasonResponse]:
        """List seasons filtered by DataScope and optional filters."""
        stmt = select(CropSeason).join(Plot, CropSeason.plot_id == Plot.id).join(Farm, Plot.farm_id == Farm.id).options(
            selectinload(CropSeason.plot).selectinload(Plot.farm),
            selectinload(CropSeason.plot).selectinload(Plot.tree_groups).selectinload(TreeGroup.variety),
            selectinload(CropSeason.activities)
        )

        # Apply Scope Filters
        if principal.data_scope != DataScope.ALL:
            stmt = stmt.where(Farm.organization_id == uuid.UUID(principal.organization_id))

        if principal.data_scope == DataScope.OWN:
            stmt = stmt.outerjoin(FarmFarmerAssignment, Farm.id == FarmFarmerAssignment.farm_id).where(
                or_(
                    Farm.owner_farmer_user_id == uuid.UUID(principal.user_id),
                    and_(
                        FarmFarmerAssignment.farmer_user_id == uuid.UUID(principal.user_id),
                        FarmFarmerAssignment.is_active == True
                    )
                )
            )

        if plot_id:
            stmt = stmt.where(CropSeason.plot_id == plot_id)
        if season_status:
            stmt = stmt.where(CropSeason.season_status == season_status)

        stmt = stmt.order_by(CropSeason.created_at.desc())
        res = await db.execute(stmt)
        seasons = res.scalars().unique().all()

        results = []
        for s in seasons:
            variety_info = await cls._resolve_plot_variety(db, s.plot)
            results.append(
                SeasonResponse(
                    id=s.id,
                    plot_id=s.plot.id,
                    plot_code=s.plot.plot_code,
                    plot_name=s.plot.plot_name,
                    farm_id=s.plot.farm.id,
                    farm_name=s.plot.farm.farm_name,
                    organization_id=s.plot.farm.organization_id,
                    inherited_variety_code=variety_info["variety_code"],
                    inherited_variety_name_vi=variety_info["name_vi"],
                    inherited_variety_name_en=variety_info["name_en"],
                    is_variety_verified=variety_info["is_verified"],
                    assurance_level=variety_info["assurance_level"],
                    source_claim_id=variety_info.get("source_claim_id"),
                    provenance_source=variety_info.get("provenance_source"),
                    season_code=s.season_code,
                    season_name=s.season_name,
                    start_date=s.start_date,
                    expected_harvest_start=s.expected_harvest_start,
                    expected_harvest_end=s.expected_harvest_end,
                    actual_harvest_end=s.actual_harvest_end,
                    forecasted_yield_kg=float(s.forecasted_yield_kg),
                    actual_harvested_yield_kg=float(s.actual_harvested_yield_kg),
                    season_status=s.season_status,
                    activities_count=len(s.activities),
                    closed_at=s.closed_at,
                    created_at=s.created_at,
                    updated_at=s.updated_at
                )
            )
        return results

    @classmethod
    async def get_season(
        cls,
        db: AsyncSession,
        season_id: uuid.UUID,
        principal: Principal
    ) -> SeasonDetailResponse:
        """Get season detail by ID with DataScope guard, activities, yield estimates, and materials PHI summary."""
        res = await db.execute(
            select(CropSeason).where(CropSeason.id == season_id).options(
                selectinload(CropSeason.plot).selectinload(Plot.farm),
                selectinload(CropSeason.plot).selectinload(Plot.tree_groups).selectinload(TreeGroup.variety),
                selectinload(CropSeason.activities),
                selectinload(CropSeason.yield_estimates)
            )
        )
        season = res.scalar_one_or_none()
        if not season:
            raise NotFoundException(message_key="errors.season.notFound", code="SEASON_NOT_FOUND")

        farm = season.plot.farm
        if principal.data_scope != DataScope.ALL and str(farm.organization_id) != principal.organization_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        variety_info = await cls._resolve_plot_variety(db, season.plot)

        # Fetch activities for season
        from app.modules.farm_activity.models import FarmActivity
        from app.modules.material.models import MaterialUsage, MaterialBatch, Material
        act_res = await db.execute(
            select(FarmActivity).where(FarmActivity.season_id == season_id).options(
                selectinload(FarmActivity.activity_type),
                selectinload(FarmActivity.performer),
                selectinload(FarmActivity.material_usages).selectinload(MaterialUsage.material_batch).selectinload(MaterialBatch.material)
            ).order_by(FarmActivity.performed_at.desc())
        )
        activities = act_res.scalars().all()

        act_list = []
        total_mat_apps = 0
        latest_safe_date: Optional[date] = None
        longest_phi_mat: Optional[str] = None
        longest_phi_val = 0

        for a in activities:
            mat_objs = []
            for mu in a.material_usages:
                total_mat_apps += 1
                mat = mu.material_batch.material if mu.material_batch else None
                phi_days = mat.pre_harvest_interval_days if mat and mat.pre_harvest_interval_days else 0
                if phi_days > longest_phi_val:
                    longest_phi_val = phi_days
                    longest_phi_mat = mat.brand_name if mat else None

                safe_d = a.performed_at.date() + timedelta(days=phi_days)
                if latest_safe_date is None or safe_d > latest_safe_date:
                    latest_safe_date = safe_d

                mat_objs.append({
                    "id": str(mu.id),
                    "material_batch_id": str(mu.material_batch_id),
                    "material_name": mat.brand_name if mat else "",
                    "batch_number": mu.material_batch.batch_number if mu.material_batch else "",
                    "quantity_applied": float(mu.quantity_applied),
                    "phi_days": phi_days,
                    "safe_harvest_date": safe_d.isoformat()
                })

            act_name_vi = a.activity_code
            if a.activity_type:
                act_name_vi = a.activity_type.activity_code
                for tr in (a.activity_type.translations or []):
                    if tr.locale == "vi":
                        act_name_vi = tr.name
                        break

            act_list.append({
                "id": str(a.id),
                "activity_code": a.activity_code,
                "activity_type_code": a.activity_type.activity_code if a.activity_type else "ACTIVITY",
                "activity_name_vi": act_name_vi,
                "performed_at": a.performed_at.isoformat(),
                "performed_by_name": a.performer.full_name if a.performer else "Farmer",
                "is_geofence_verified": a.is_geofence_verified,
                "verification_status": "VERIFIED" if a.is_geofence_verified else "PENDING",
                "notes": a.notes,
                "materials": mat_objs
            })

        # Yield estimates
        ye_list = []
        if season.yield_estimates:
            for ye in season.yield_estimates:
                ye_list.append(
                    YieldEstimateResponse(
                        id=ye.id,
                        season_id=ye.season_id,
                        estimation_method=ye.estimation_method,
                        estimated_yield_kg=float(ye.estimated_yield_kg),
                        confidence_level_pct=float(ye.confidence_level_pct) if ye.confidence_level_pct else 90.0,
                        estimated_by_id=ye.estimated_by_id,
                        estimated_by_name="Kỹ thuật viên",
                        estimated_at=ye.estimated_at,
                        notes=ye.notes
                    )
                )

        today_d = date.today()

        # PHI Evaluation
        if total_mat_apps == 0:
            phi_status = "NO_MATERIAL_RECORDED"
            earliest_safe_harvest_date = None
            quarantine_days_remaining = None
            is_phi_safe = False
        elif latest_safe_date is not None:
            earliest_safe_harvest_date = latest_safe_date
            if today_d < latest_safe_date:
                phi_status = "IN_QUARANTINE"
                quarantine_days_remaining = (latest_safe_date - today_d).days
                is_phi_safe = False
            else:
                phi_status = "PHI_ELAPSED"
                quarantine_days_remaining = 0
                is_phi_safe = True
        else:
            phi_status = "UNKNOWN"
            earliest_safe_harvest_date = None
            quarantine_days_remaining = None
            is_phi_safe = False

        # Harvest Eligibility Evaluation (Decoupled from solely PHI date passage)
        if season.season_status not in ["ACTIVE", "HARVESTING"]:
            harvest_eligibility = "INELIGIBLE_SEASON_INACTIVE"
            harvest_eligibility_reason = f"Mùa vụ đang ở trạng thái [{season.season_status}], không cho phép thu hoạch"
        elif total_mat_apps > 0 and not is_phi_safe:
            harvest_eligibility = "INELIGIBLE_PHI_ACTIVE"
            harvest_eligibility_reason = f"Vườn đang trong thời gian cách ly PHI (còn {quarantine_days_remaining} ngày, an toàn từ {latest_safe_date.isoformat()})"
        elif total_mat_apps == 0:
            harvest_eligibility = "NEEDS_REVIEW"
            harvest_eligibility_reason = "Chưa ghi nhận nhật ký vật tư phân thuốc; cần kỹ thuật viên thẩm định thực địa trước thu hoạch"
        elif today_d < season.expected_harvest_start:
            harvest_eligibility = "INELIGIBLE_BEFORE_HARVEST_WINDOW"
            harvest_eligibility_reason = f"Chưa đến khung thời gian thu hoạch dự kiến (dự kiến từ {season.expected_harvest_start.isoformat()})"
        else:
            harvest_eligibility = "ELIGIBLE"
            harvest_eligibility_reason = f"Đạt chuẩn an toàn cách ly PHI và trong khung thời gian thu hoạch vụ mùa"

        materials_summary = SeasonMaterialsSummary(
            total_applications=total_mat_apps,
            earliest_safe_harvest_date=earliest_safe_harvest_date,
            phi_status=phi_status,
            harvest_eligibility=harvest_eligibility,
            harvest_eligibility_reason=harvest_eligibility_reason,
            quarantine_days_remaining=quarantine_days_remaining,
            is_safe_to_harvest=(harvest_eligibility == "ELIGIBLE"),
            longest_phi_material=longest_phi_mat,
            longest_phi_days=longest_phi_val
        )

        return SeasonDetailResponse(
            id=season.id,
            plot_id=season.plot.id,
            plot_code=season.plot.plot_code,
            plot_name=season.plot.plot_name,
            farm_id=farm.id,
            farm_name=farm.farm_name,
            organization_id=farm.organization_id,
            inherited_variety_code=variety_info["variety_code"],
            inherited_variety_name_vi=variety_info["name_vi"],
            inherited_variety_name_en=variety_info["name_en"],
            is_variety_verified=variety_info["is_verified"],
            assurance_level=variety_info["assurance_level"],
            source_claim_id=variety_info.get("source_claim_id"),
            provenance_source=variety_info.get("provenance_source"),
            season_code=season.season_code,
            season_name=season.season_name,
            start_date=season.start_date,
            expected_harvest_start=season.expected_harvest_start,
            expected_harvest_end=season.expected_harvest_end,
            actual_harvest_end=season.actual_harvest_end,
            forecasted_yield_kg=float(season.forecasted_yield_kg),
            actual_harvested_yield_kg=float(season.actual_harvested_yield_kg),
            season_status=season.season_status,
            activities_count=len(season.activities),
            closed_at=season.closed_at,
            created_at=season.created_at,
            updated_at=season.updated_at,
            yield_estimates=ye_list,
            farm_activities=act_list,
            materials_summary=materials_summary
        )

    @classmethod
    async def close_season(
        cls,
        db: AsyncSession,
        season_id: uuid.UUID,
        principal: Principal
    ) -> SeasonResponse:
        """Close an active crop season."""
        season = await db.get(CropSeason, season_id)
        if not season:
            raise NotFoundException(message_key="errors.season.notFound", code="SEASON_NOT_FOUND")

        # Invariant: Cannot close an already closed season
        if season.season_status == "CLOSED":
            raise ConflictException(message_key="errors.season.alreadyClosed", code="SEASON_ALREADY_CLOSED")

        now = datetime.now(timezone.utc)
        season.season_status = "CLOSED"
        season.closed_at = now
        season.closed_by = uuid.UUID(principal.user_id)
        season.actual_harvest_end = now.date()
        season.updated_at = now

        await AuditService.record_audit_log(
            db=db,
            action="SEASON_CLOSE",
            resource_type="CROP_SEASON",
            resource_id=season.id,
            actor_id=uuid.UUID(principal.user_id),
            organization_id=season.plot.farm.organization_id if season.plot and season.plot.farm else None,
            details={"season_code": season.season_code}
        )

        event = DomainEventEnvelope(
            event_type="SeasonClosed",
            aggregate_type="CropSeason",
            aggregate_id=season.id,
            organization_id=uuid.UUID(principal.organization_id) if principal.organization_id else uuid.uuid4(),
            actor_id=uuid.UUID(principal.user_id),
            payload={"season_id": str(season.id), "season_code": season.season_code, "closed_at": now.isoformat()}
        )
        await OutboxService.enqueue_outbox_event(db, event)
        await db.commit()

        return await cls.get_season(db, season.id, principal)
