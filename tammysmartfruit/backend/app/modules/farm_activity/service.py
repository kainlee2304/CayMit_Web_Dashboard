"""
Farm Activity (Farm Diary) Domain Service (Module 9)
Enforces:
1. Activity Type validation from Canonical Master Data.
2. Material Usage validation, Batch stock deduction, and PHI safe harvest calculation.
3. Geofence point-in-polygon verification against Plot boundaries.
4. Data Trust: Evidence creation (SHA-256) and Data Claim linking.
5. Four-Eyes Principle Enforcement (Creator cannot verify own activity).
6. Transactional Outbox, Domain Event Journal, and Audit Logging.
"""

from datetime import datetime, timezone, date, timedelta
import hashlib
import json
from typing import List, Optional, Dict, Any
import uuid
from shapely.geometry import shape, Point
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import Principal, DataScope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException, ValidationException
from app.modules.identity.models import User
from app.modules.farm.models import Farm, Plot, FarmFarmerAssignment
from app.modules.master_data.models import ActivityType, Unit
from app.modules.season.models import CropSeason
from app.modules.material.models import Material, MaterialBatch, MaterialUsage
from app.modules.claims.models import DataClaim, ClaimStatusHistory, EvidenceRecord, ClaimEvidenceLink
from app.modules.farm_activity.models import FarmActivity
from app.modules.farm_activity.schemas import (
    FarmActivityCreate, FarmActivityVerifyAction, FarmActivityResponse
)
from app.modules.material.schemas import MaterialUsageResponse
from app.modules.audit.service import AuditService
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.service import OutboxService

class FarmActivityService:

    @classmethod
    async def create_activity(
        cls,
        db: AsyncSession,
        data: FarmActivityCreate,
        principal: Principal
    ) -> FarmActivityResponse:
        """Record a farm diary activity with optional material usage and evidence."""
        # 1. Fetch Season and Plot
        s_res = await db.execute(
            select(CropSeason).where(CropSeason.id == data.season_id).options(
                selectinload(CropSeason.plot).selectinload(Plot.farm).selectinload(Farm.farmer_assignments)
            )
        )
        season = s_res.scalar_one_or_none()
        if not season:
            raise NotFoundException(message_key="errors.season.notFound", code="SEASON_NOT_FOUND")

        plot = season.plot
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

        # 3. Validate Activity Type from Master Data
        act_type = await db.get(ActivityType, data.activity_type_id)
        if not act_type:
            raise NotFoundException(message_key="errors.masterData.activityTypeNotFound", code="ACTIVITY_TYPE_NOT_FOUND")

        # 4. Geofence Verification
        is_geofence_verified = False
        if data.gps_point and isinstance(data.gps_point, dict) and "coordinates" in data.gps_point:
            try:
                coords = data.gps_point["coordinates"] # [lng, lat]
                pt = Point(coords[0], coords[1])
                # Check point in plot polygon
                if plot.boundary_polygon:
                    poly_geom = plot.boundary_polygon
                    if isinstance(poly_geom, str):
                        poly_geom = json.loads(poly_geom)
                    plot_poly = shape(poly_geom)
                    if plot_poly.contains(pt) or plot_poly.distance(pt) < 0.0005: # ~50m tolerance
                        is_geofence_verified = True
            except Exception:
                is_geofence_verified = False

        now = datetime.now(timezone.utc)
        activity_id = uuid.uuid4()
        rand_code = uuid.uuid4().hex[:6].upper()
        activity_code = f"ACT-{now.year}-{rand_code}"

        # 5. Create FarmActivity Aggregate
        activity = FarmActivity(
            id=activity_id,
            season_id=season.id,
            activity_type_id=act_type.id,
            activity_code=activity_code,
            performed_by_user_id=uuid.UUID(principal.user_id),
            performed_at=data.performed_at,
            gps_point=data.gps_point,
            gps_accuracy_meters=data.gps_accuracy_meters,
            is_geofence_verified=is_geofence_verified,
            duration_hours=data.duration_hours,
            weather_condition=data.weather_condition,
            notes=data.notes,
            created_at=now,
            updated_at=now
        )
        db.add(activity)
        await db.flush()

        # 6. Process Material Usages & PHI
        material_usages_list = []
        if data.materials:
            for mat_input in data.materials:
                if mat_input.quantity_applied <= 0:
                    raise ValidationException(
                        message_key="errors.material.invalidQuantity",
                        code="INVALID_QUANTITY",
                        field_errors=[{"field": "quantity_applied", "message": "Applied quantity must be greater than 0"}]
                    )

                batch_res = await db.execute(
                    select(MaterialBatch).where(MaterialBatch.id == mat_input.material_batch_id).options(
                        selectinload(MaterialBatch.material),
                        selectinload(MaterialBatch.unit)
                    )
                )
                batch = batch_res.scalar_one_or_none()
                if not batch:
                    raise NotFoundException(message_key="errors.material.batchNotFound", code="MATERIAL_BATCH_NOT_FOUND")

                # Stock verification
                if float(batch.remaining_quantity) < float(mat_input.quantity_applied):
                    raise ValidationException(
                        message_key="errors.material.insufficientStock",
                        code="INSUFFICIENT_STOCK",
                        field_errors=[{"field": "quantity_applied", "message": f"Insufficient stock: requested {mat_input.quantity_applied}, remaining {batch.remaining_quantity}"}]
                    )

                # Deduct stock
                batch.remaining_quantity = float(batch.remaining_quantity) - float(mat_input.quantity_applied)

                # Calculate PHI earliest safe harvest date
                phi_days = batch.material.pre_harvest_interval_days
                activity_date = data.performed_at.date() if isinstance(data.performed_at, datetime) else data.performed_at
                earliest_safe_date = activity_date + timedelta(days=phi_days)

                usage = MaterialUsage(
                    id=uuid.uuid4(),
                    activity_id=activity.id,
                    material_batch_id=batch.id,
                    quantity_applied=mat_input.quantity_applied,
                    unit_id=mat_input.unit_id,
                    phi_days_applied=phi_days,
                    earliest_safe_harvest_date=earliest_safe_date,
                    application_method=mat_input.application_method,
                    created_at=now
                )
                db.add(usage)
                await db.flush()

                material_usages_list.append(
                    MaterialUsageResponse(
                        id=usage.id,
                        activity_id=activity.id,
                        material_batch_id=batch.id,
                        material_code=batch.material.material_code,
                        brand_name=batch.material.brand_name,
                        batch_number=batch.batch_number,
                        quantity_applied=float(usage.quantity_applied),
                        unit_id=usage.unit_id,
                        unit_code=batch.unit.unit_code,
                        phi_days_applied=phi_days,
                        earliest_safe_harvest_date=earliest_safe_date,
                        application_method=usage.application_method
                    )
                )

        # 7. Evidence & DataClaim Creation
        evidence_id = None
        evidence_hash = None
        if data.evidence_photo_base64:
            evidence_hash = hashlib.sha256(data.evidence_photo_base64.encode("utf-8")).hexdigest()
            evidence_record = EvidenceRecord(
                id=uuid.uuid4(),
                organization_id=org_id,
                evidence_type="GEOTAGGED_PHOTO",
                evidence_hash=evidence_hash,
                captured_at=data.performed_at,
                gps_point=data.gps_point,
                metadata_json={"activity_code": activity_code, "accuracy": data.gps_accuracy_meters},
                created_by=uuid.UUID(principal.user_id),
                created_at=now
            )
            db.add(evidence_record)
            await db.flush()
            evidence_id = evidence_record.id

        # Create Claim
        initial_assurance = "LEVEL_1_SYSTEM_VALIDATED" if is_geofence_verified else "LEVEL_0_DECLARED"
        claim = DataClaim(
            id=uuid.uuid4(),
            organization_id=org_id,
            claim_type="FARM_ACTIVITY",
            subject_type="PLOT",
            subject_id=plot.id,
            value_code=act_type.activity_code,
            value_json={"activity_id": str(activity.id), "activity_code": activity_code, "duration_hours": data.duration_hours},
            declared_by=uuid.UUID(principal.user_id),
            declared_at=now,
            source_type="FARMER_DECLARATION",
            assurance_level=initial_assurance,
            verification_status="PENDING",
            risk_score=5.0 if is_geofence_verified else 15.0,
            is_current=True,
            created_at=now,
            updated_at=now
        )
        db.add(claim)
        await db.flush()

        db.add(ClaimStatusHistory(
            id=uuid.uuid4(),
            claim_id=claim.id,
            previous_status="NONE",
            new_status="PENDING",
            previous_assurance_level="NONE",
            new_assurance_level=initial_assurance,
            transition_reason="Farmer farm diary activity recorded",
            transitioned_by=uuid.UUID(principal.user_id),
            occurred_at=now
        ))

        if evidence_id:
            db.add(ClaimEvidenceLink(
                id=uuid.uuid4(),
                claim_id=claim.id,
                evidence_id=evidence_id,
                relevance_weight=1.0,
                linked_at=now,
                linked_by=uuid.UUID(principal.user_id)
            ))

        # 8. Outbox & Domain Event Journal & Audit
        await AuditService.record_audit_log(
            db=db,
            action="ACTIVITY_CREATE",
            resource_type="FARM_ACTIVITY",
            resource_id=activity.id,
            actor_id=uuid.UUID(principal.user_id),
            organization_id=org_id,
            details={
                "activity_code": activity_code,
                "season_id": str(season.id),
                "activity_type": act_type.activity_code,
                "is_geofence_verified": is_geofence_verified,
                "materials_count": len(material_usages_list)
            }
        )

        event = DomainEventEnvelope(
            event_type="FarmActivityRecorded",
            aggregate_type="FarmActivity",
            aggregate_id=activity.id,
            organization_id=org_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "activity_id": str(activity.id),
                "activity_code": activity_code,
                "season_id": str(season.id),
                "plot_id": str(plot.id),
                "activity_type": act_type.activity_code,
                "is_geofence_verified": is_geofence_verified,
                "materials_count": len(material_usages_list),
                "claim_id": str(claim.id)
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)
        await db.commit()

        # Fetch performer display name
        u = await db.get(User, uuid.UUID(principal.user_id))
        performer_name = u.full_name or u.username if u else principal.username

        act_type_translations = {t.locale: t.name for t in act_type.translations} if hasattr(act_type, "translations") and act_type.translations else {}
        name_vi = act_type_translations.get("vi", act_type.activity_code)
        name_en = act_type_translations.get("en", act_type.activity_code)

        return FarmActivityResponse(
            id=activity.id,
            season_id=season.id,
            season_code=season.season_code,
            season_name=season.season_name,
            plot_id=plot.id,
            plot_code=plot.plot_code,
            plot_name=plot.plot_name,
            farm_id=farm.id,
            farm_name=farm.farm_name,
            organization_id=org_id,
            activity_type_id=act_type.id,
            activity_type_code=act_type.activity_code,
            activity_type_name_vi=name_vi,
            activity_type_name_en=name_en,
            activity_code=activity.activity_code,
            performed_by_user_id=activity.performed_by_user_id,
            performed_by_name=performer_name,
            performed_at=activity.performed_at,
            gps_point=activity.gps_point,
            gps_accuracy_meters=float(activity.gps_accuracy_meters) if activity.gps_accuracy_meters else None,
            is_geofence_verified=activity.is_geofence_verified,
            duration_hours=float(activity.duration_hours) if activity.duration_hours else None,
            weather_condition=activity.weather_condition,
            notes=activity.notes,
            materials=material_usages_list,
            claim_id=claim.id,
            assurance_level=claim.assurance_level,
            verification_status=claim.verification_status,
            evidence_id=evidence_id,
            evidence_hash=evidence_hash,
            created_at=activity.created_at,
            updated_at=activity.updated_at
        )

    @classmethod
    async def list_activities(
        cls,
        db: AsyncSession,
        principal: Principal,
        season_id: Optional[uuid.UUID] = None,
        plot_id: Optional[uuid.UUID] = None,
        activity_type_id: Optional[uuid.UUID] = None,
        verification_status: Optional[str] = None
    ) -> List[FarmActivityResponse]:
        """List farm activities filtered by DataScope and query params."""
        stmt = select(FarmActivity).join(CropSeason, FarmActivity.season_id == CropSeason.id).join(Plot, CropSeason.plot_id == Plot.id).join(Farm, Plot.farm_id == Farm.id).options(
            selectinload(FarmActivity.season).selectinload(CropSeason.plot).selectinload(Plot.farm),
            selectinload(FarmActivity.activity_type).selectinload(ActivityType.translations),
            selectinload(FarmActivity.performer),
            selectinload(FarmActivity.material_usages).selectinload(MaterialUsage.material_batch).selectinload(MaterialBatch.material),
            selectinload(FarmActivity.material_usages).selectinload(MaterialUsage.unit)
        )

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

        if season_id:
            stmt = stmt.where(FarmActivity.season_id == season_id)
        if plot_id:
            stmt = stmt.where(CropSeason.plot_id == plot_id)
        if activity_type_id:
            stmt = stmt.where(FarmActivity.activity_type_id == activity_type_id)

        stmt = stmt.order_by(FarmActivity.performed_at.desc())
        res = await db.execute(stmt)
        activities = res.scalars().unique().all()

        results = []
        for a in activities:
            # Check claim
            claim_res = await db.execute(
                select(DataClaim).where(
                    and_(
                        DataClaim.claim_type == "FARM_ACTIVITY",
                        DataClaim.subject_id == a.season.plot_id,
                        DataClaim.value_code == a.activity_type.activity_code,
                        DataClaim.is_current == True
                    )
                ).options(selectinload(DataClaim.verifier))
            )
            claim = claim_res.scalars().first()

            material_res_list = [
                MaterialUsageResponse(
                    id=u.id,
                    activity_id=a.id,
                    material_batch_id=u.material_batch_id,
                    material_code=u.material_batch.material.material_code,
                    brand_name=u.material_batch.material.brand_name,
                    batch_number=u.material_batch.batch_number,
                    quantity_applied=float(u.quantity_applied),
                    unit_id=u.unit_id,
                    unit_code=u.unit.unit_code,
                    phi_days_applied=u.phi_days_applied,
                    earliest_safe_harvest_date=u.earliest_safe_harvest_date,
                    application_method=u.application_method
                )
                for u in a.material_usages
            ]

            act_type_translations = {t.locale: t.name for t in a.activity_type.translations} if a.activity_type and a.activity_type.translations else {}
            name_vi = act_type_translations.get("vi", a.activity_type.activity_code)
            name_en = act_type_translations.get("en", a.activity_type.activity_code)

            if verification_status and claim and claim.verification_status != verification_status:
                continue

            results.append(
                FarmActivityResponse(
                    id=a.id,
                    season_id=a.season.id,
                    season_code=a.season.season_code,
                    season_name=a.season.season_name,
                    plot_id=a.season.plot.id,
                    plot_code=a.season.plot.plot_code,
                    plot_name=a.season.plot.plot_name,
                    farm_id=a.season.plot.farm.id,
                    farm_name=a.season.plot.farm.farm_name,
                    organization_id=a.season.plot.farm.organization_id,
                    activity_type_id=a.activity_type.id,
                    activity_type_code=a.activity_type.activity_code,
                    activity_type_name_vi=name_vi,
                    activity_type_name_en=name_en,
                    activity_code=a.activity_code,
                    performed_by_user_id=a.performed_by_user_id,
                    performed_by_name=a.performer.full_name or a.performer.username if a.performer else "Farmer",
                    performed_at=a.performed_at,
                    gps_point=a.gps_point,
                    gps_accuracy_meters=float(a.gps_accuracy_meters) if a.gps_accuracy_meters else None,
                    is_geofence_verified=a.is_geofence_verified,
                    duration_hours=float(a.duration_hours) if a.duration_hours else None,
                    weather_condition=a.weather_condition,
                    notes=a.notes,
                    materials=material_res_list,
                    claim_id=claim.id if claim else None,
                    assurance_level=claim.assurance_level if claim else "LEVEL_0_DECLARED",
                    verification_status=claim.verification_status if claim else "PENDING",
                    verified_by_id=claim.verified_by if claim else None,
                    verified_by_name=claim.verifier.full_name if claim and claim.verifier else None,
                    verified_at=claim.verified_at if claim else None,
                    created_at=a.created_at,
                    updated_at=a.updated_at
                )
            )
        return results

    @classmethod
    async def get_activity(
        cls,
        db: AsyncSession,
        activity_id: uuid.UUID,
        principal: Principal
    ) -> FarmActivityResponse:
        """Get activity detail by ID with DataScope check."""
        res = await db.execute(
            select(FarmActivity).where(FarmActivity.id == activity_id).options(
                selectinload(FarmActivity.season).selectinload(CropSeason.plot).selectinload(Plot.farm),
                selectinload(FarmActivity.activity_type).selectinload(ActivityType.translations),
                selectinload(FarmActivity.performer),
                selectinload(FarmActivity.material_usages).selectinload(MaterialUsage.material_batch).selectinload(MaterialBatch.material),
                selectinload(FarmActivity.material_usages).selectinload(MaterialUsage.unit)
            )
        )
        activity = res.scalar_one_or_none()
        if not activity:
            raise NotFoundException(message_key="errors.activity.notFound", code="ACTIVITY_NOT_FOUND")

        farm = activity.season.plot.farm
        if principal.data_scope != DataScope.ALL and str(farm.organization_id) != principal.organization_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # Fetch claim
        claim_res = await db.execute(
            select(DataClaim).where(
                and_(
                    DataClaim.claim_type == "FARM_ACTIVITY",
                    DataClaim.subject_id == activity.season.plot_id,
                    DataClaim.value_code == activity.activity_type.activity_code,
                    DataClaim.is_current == True
                )
            ).options(
                selectinload(DataClaim.verifier),
                selectinload(DataClaim.evidence_links).selectinload(ClaimEvidenceLink.evidence)
            )
        )
        claim = claim_res.scalars().first()

        material_res_list = [
            MaterialUsageResponse(
                id=u.id,
                activity_id=activity.id,
                material_batch_id=u.material_batch_id,
                material_code=u.material_batch.material.material_code,
                brand_name=u.material_batch.material.brand_name,
                batch_number=u.material_batch.batch_number,
                quantity_applied=float(u.quantity_applied),
                unit_id=u.unit_id,
                unit_code=u.unit.unit_code,
                phi_days_applied=u.phi_days_applied,
                earliest_safe_harvest_date=u.earliest_safe_harvest_date,
                application_method=u.application_method
            )
            for u in activity.material_usages
        ]

        evidence_id = None
        evidence_hash = None
        if claim and claim.evidence_links:
            evidence_id = claim.evidence_links[0].evidence_id
            if claim.evidence_links[0].evidence:
                evidence_hash = claim.evidence_links[0].evidence.evidence_hash

        verified_by_name = None
        if claim and claim.verified_by:
            if claim.verifier:
                verified_by_name = claim.verifier.full_name or claim.verifier.username
            else:
                v_user = await db.get(User, claim.verified_by)
                if v_user:
                    verified_by_name = v_user.full_name or v_user.username

        act_type_translations = {t.locale: t.name for t in activity.activity_type.translations} if activity.activity_type and activity.activity_type.translations else {}
        name_vi = act_type_translations.get("vi", activity.activity_type.activity_code)
        name_en = act_type_translations.get("en", activity.activity_type.activity_code)

        return FarmActivityResponse(
            id=activity.id,
            season_id=activity.season.id,
            season_code=activity.season.season_code,
            season_name=activity.season.season_name,
            plot_id=activity.season.plot.id,
            plot_code=activity.season.plot.plot_code,
            plot_name=activity.season.plot.plot_name,
            farm_id=farm.id,
            farm_name=farm.farm_name,
            organization_id=farm.organization_id,
            activity_type_id=activity.activity_type.id,
            activity_type_code=activity.activity_type.activity_code,
            activity_type_name_vi=name_vi,
            activity_type_name_en=name_en,
            activity_code=activity.activity_code,
            performed_by_user_id=activity.performed_by_user_id,
            performed_by_name=activity.performer.full_name or activity.performer.username if activity.performer else "Farmer",
            performed_at=activity.performed_at,
            gps_point=activity.gps_point,
            gps_accuracy_meters=float(activity.gps_accuracy_meters) if activity.gps_accuracy_meters else None,
            is_geofence_verified=activity.is_geofence_verified,
            duration_hours=float(activity.duration_hours) if activity.duration_hours else None,
            weather_condition=activity.weather_condition,
            notes=activity.notes,
            materials=material_res_list,
            claim_id=claim.id if claim else None,
            assurance_level=claim.assurance_level if claim else "LEVEL_0_DECLARED",
            verification_status=claim.verification_status if claim else "PENDING",
            verified_by_id=claim.verified_by if claim else None,
            verified_by_name=verified_by_name,
            verified_at=claim.verified_at if claim else None,
            evidence_id=evidence_id,
            evidence_hash=evidence_hash,
            created_at=activity.created_at,
            updated_at=activity.updated_at
        )

    @classmethod
    async def verify_activity(
        cls,
        db: AsyncSession,
        activity_id: uuid.UUID,
        data: FarmActivityVerifyAction,
        principal: Principal
    ) -> FarmActivityResponse:
        """
        Technician or QA verifies a Farm Diary activity.
        CRITICAL: Four-Eyes Principle -> Declarant/Creator CANNOT verify their own activity!
        """
        res = await db.execute(
            select(FarmActivity).where(FarmActivity.id == activity_id).options(
                selectinload(FarmActivity.season).selectinload(CropSeason.plot).selectinload(Plot.farm)
            )
        )
        activity = res.scalar_one_or_none()
        if not activity:
            raise NotFoundException(message_key="errors.activity.notFound", code="ACTIVITY_NOT_FOUND")

        farm = activity.season.plot.farm
        if principal.data_scope != DataScope.ALL and str(farm.organization_id) != principal.organization_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # FOUR-EYES PRINCIPLE: Declarant cannot self-verify!
        if str(activity.performed_by_user_id) == principal.user_id:
            raise ForbiddenException(
                message_key="errors.claims.fourEyesSelfVerificationBlocked",
                code="FOUR_EYES_SELF_VERIFICATION_BLOCKED"
            )

        # Fetch claim
        claim_res = await db.execute(
            select(DataClaim).where(
                and_(
                    DataClaim.claim_type == "FARM_ACTIVITY",
                    DataClaim.subject_id == activity.season.plot_id,
                    DataClaim.value_code == activity.activity_type.activity_code,
                    DataClaim.is_current == True
                )
            )
        )
        claim = claim_res.scalars().first()
        if not claim:
            raise NotFoundException(message_key="errors.claims.claimNotFound", code="CLAIM_NOT_FOUND")

        now = datetime.now(timezone.utc)
        prev_status = claim.verification_status
        prev_assurance = claim.assurance_level

        if data.decision == "APPROVED":
            new_status = "VERIFIED"
            new_assurance = "LEVEL_2_ORGANIZATION_VERIFIED"
            claim.verification_status = new_status
            claim.assurance_level = new_assurance
            claim.verified_by = uuid.UUID(principal.user_id)
            claim.verified_at = now
            claim.verification_method = data.verification_method
            claim.risk_score = 0.0
        else:
            new_status = "REJECTED"
            new_assurance = prev_assurance
            claim.verification_status = new_status
            claim.verified_by = uuid.UUID(principal.user_id)
            claim.verified_at = now
            claim.verification_method = data.verification_method

        claim.updated_at = now

        db.add(ClaimStatusHistory(
            id=uuid.uuid4(),
            claim_id=claim.id,
            previous_status=prev_status,
            new_status=new_status,
            previous_assurance_level=prev_assurance,
            new_assurance_level=new_assurance,
            transition_reason=data.notes or f"Technician four-eyes verification decision: {data.decision}",
            transitioned_by=uuid.UUID(principal.user_id),
            occurred_at=now
        ))

        await AuditService.record_audit_log(
            db=db,
            action="ACTIVITY_VERIFY",
            resource_type="FARM_ACTIVITY",
            resource_id=activity.id,
            actor_id=uuid.UUID(principal.user_id),
            organization_id=farm.organization_id,
            details={
                "activity_code": activity.activity_code,
                "decision": data.decision,
                "verification_method": data.verification_method,
                "claim_id": str(claim.id)
            }
        )

        event = DomainEventEnvelope(
            event_type="FarmActivityVerified",
            aggregate_type="FarmActivity",
            aggregate_id=activity.id,
            organization_id=farm.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "activity_id": str(activity.id),
                "activity_code": activity.activity_code,
                "decision": data.decision,
                "claim_id": str(claim.id),
                "assurance_level": new_assurance
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)
        await db.commit()

        return await cls.get_activity(db, activity.id, principal)
