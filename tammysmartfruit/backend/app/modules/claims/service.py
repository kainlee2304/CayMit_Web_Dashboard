"""
Data Claims and Verification Domain Service (Modules 24, 25, 26)
Enforces:
1. Canonical Master Code Validation (No Free-Text Variety/PUC).
2. Variety Declaration != Verified Variety (Initial LEVEL_0_DECLARED).
3. Four-Eyes Principle Enforcement (Creator cannot verify own claim).
4. Verified Claim Immutability (Direct overwrite blocked).
"""

import hashlib
import json
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.rbac import Principal, DataScope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException, ValidationException
from app.modules.identity.models import User
from app.modules.claims.models import DataClaim, ClaimStatusHistory, EvidenceRecord, ClaimEvidenceLink
from app.modules.claims.schemas import (
    ClaimDeclarationCreate, ClaimVerificationAction, DataClaimResponse,
    ClaimStatusHistoryResponse, EvidenceResponse
)
from app.modules.master_data.models import CropVariety
from app.modules.audit.service import AuditService
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.service import OutboxService

class ClaimService:

    @classmethod
    async def declare_claim(
        cls,
        db: AsyncSession,
        data: ClaimDeclarationCreate,
        principal: Principal
    ) -> DataClaimResponse:
        """
        Farmer or Producer declares an agricultural claim (e.g. CROP_VARIETY).
        Initial state: LEVEL_0_DECLARED, PENDING verification.
        """
        # 1. Multi-tenant scope check
        if principal.data_scope != DataScope.ALL and principal.organization_id != str(data.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # 2. Invariant: Master Code Validation (No free-text allowed)
        if data.claim_type == "CROP_VARIETY":
            v_res = await db.execute(select(CropVariety).where(CropVariety.variety_code == data.value_code))
            if not v_res.scalar_one_or_none():
                raise ValidationException(
                    message_key="errors.claims.invalidMasterVarietyCode",
                    code="INVALID_VARIETY_CODE",
                    field_errors=[{"field": "value_code", "message": f"Variety code '{data.value_code}' does not exist in master data"}]
                )

        # 3. Check for existing active VERIFIED claim on this subject
        existing_res = await db.execute(
            select(DataClaim).where(
                and_(
                    DataClaim.subject_type == data.subject_type,
                    DataClaim.subject_id == data.subject_id,
                    DataClaim.claim_type == data.claim_type,
                    DataClaim.is_current == True
                )
            )
        )
        existing_claims = existing_res.scalars().all()

        # Invariant: If there is any active VERIFIED claim, Farmer cannot overwrite it directly
        for ec in existing_claims:
            if ec.verification_status == "VERIFIED":
                raise ConflictException(
                    message_key="errors.claims.cannotOverwriteVerifiedClaim",
                    code="CANNOT_OVERWRITE_VERIFIED_CLAIM"
                )

        new_claim_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # 4. Insert new Claim (LEVEL_0_DECLARED)
        claim = DataClaim(
            id=new_claim_id,
            organization_id=data.organization_id,
            claim_type=data.claim_type,
            subject_type=data.subject_type,
            subject_id=data.subject_id,
            value_code=data.value_code,
            value_json=data.value_json,
            declared_by=uuid.UUID(principal.user_id),
            declared_at=now,
            source_type="FARMER_DECLARATION",
            assurance_level="LEVEL_0_DECLARED",
            verification_status="PENDING",
            risk_score=10.00, # Initial declaration risk
            is_current=True
        )
        db.add(claim)
        await db.flush()

        # Supersede older pending claims (now that new_claim_id is persisted)
        for ec in existing_claims:
            if ec.verification_status == "PENDING":
                ec.is_current = False
                ec.superseded_by_claim_id = new_claim_id
        await db.flush()

        # 5. Insert initial status history
        history = ClaimStatusHistory(
            id=uuid.uuid4(),
            claim_id=new_claim_id,
            previous_status="NONE",
            new_status="PENDING",
            previous_assurance_level="NONE",
            new_assurance_level="LEVEL_0_DECLARED",
            transition_reason="Initial farmer declaration submitted",
            transitioned_by=uuid.UUID(principal.user_id),
            occurred_at=now
        )
        db.add(history)

        # 6. Optional Evidence Creation (GPS / Photos)
        if data.gps_latitude is not None and data.gps_longitude is not None:
            raw_evidence = f"{new_claim_id}:{data.gps_latitude}:{data.gps_longitude}:{now.isoformat()}"
            ev_hash = hashlib.sha256(raw_evidence.encode("utf-8")).hexdigest()

            ev_id = uuid.uuid4()
            ev_record = EvidenceRecord(
                id=ev_id,
                organization_id=data.organization_id,
                evidence_type="GEOTAGGED_PHOTO",
                evidence_hash=ev_hash,
                captured_at=now,
                gps_point=f"POINT({data.gps_longitude} {data.gps_latitude})",
                metadata_json={"notes": data.evidence_notes or "Farmer mobile capture"},
                created_by=uuid.UUID(principal.user_id)
            )
            db.add(ev_record)

            # Link evidence to claim
            link = ClaimEvidenceLink(
                id=uuid.uuid4(),
                claim_id=new_claim_id,
                evidence_id=ev_id,
                relevance_weight=1.00,
                linked_at=now,
                linked_by=uuid.UUID(principal.user_id)
            )
            db.add(link)

        await db.flush()

        # 7. Audit Logging
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="DECLARE_CLAIM",
            resource_type="DataClaim",
            resource_id=new_claim_id,
            organization_id=data.organization_id,
            details={"claim_type": data.claim_type, "value_code": data.value_code, "level": "LEVEL_0_DECLARED"}
        )

        # 8. Domain Event Enqueueing
        event = DomainEventEnvelope(
            event_type="VarietyClaimDeclaredEvent",
            aggregate_type="DataClaim",
            aggregate_id=new_claim_id,
            organization_id=data.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "claim_type": data.claim_type,
                "subject_type": data.subject_type,
                "subject_id": str(data.subject_id),
                "value_code": data.value_code,
                "assurance_level": "LEVEL_0_DECLARED"
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return await cls.get_claim_by_id(db, new_claim_id, principal)

    @classmethod
    async def verify_claim(
        cls,
        db: AsyncSession,
        claim_id: uuid.UUID,
        action: ClaimVerificationAction,
        principal: Principal
    ) -> DataClaimResponse:
        """
        Technician or QA/QC performs official verification on a declared claim.
        Enforces Four-Eyes Principle: Declarant cannot self-verify!
        """
        claim_query = select(DataClaim).where(DataClaim.id == claim_id).options(
            selectinload(DataClaim.status_history),
            selectinload(DataClaim.evidence_links).selectinload(ClaimEvidenceLink.evidence)
        )
        res = await db.execute(claim_query)
        claim = res.scalar_one_or_none()
        if not claim:
            raise NotFoundException(message_key="errors.claims.notFound", code="CLAIM_NOT_FOUND")

        # 1. Multi-tenant Scope Check
        if principal.data_scope != DataScope.ALL and principal.organization_id != str(claim.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # 2. Four-Eyes Principle Check: Self-Verification Forbidden
        if str(claim.declared_by) == principal.user_id:
            raise ForbiddenException(
                message_key="errors.claims.cannotSelfVerify",
                code="CANNOT_SELF_VERIFY"
            )

        now = datetime.now(timezone.utc)
        prev_status = claim.verification_status
        prev_assurance = claim.assurance_level

        if action.decision == "VERIFY":
            new_status = "VERIFIED"
            new_assurance = "LEVEL_2_ORGANIZATION_VERIFIED"
            new_risk = 0.00
        elif action.decision == "REJECT":
            new_status = "REJECTED"
            new_assurance = prev_assurance
            new_risk = 90.00
        else:
            raise ValidationException(
                message_key="errors.claims.invalidDecision",
                code="INVALID_DECISION",
                field_errors=[{"field": "decision", "message": "Decision must be 'VERIFY' or 'REJECT'"}]
            )

        # Update Claim
        claim.verification_status = new_status
        claim.assurance_level = new_assurance
        claim.verified_by = uuid.UUID(principal.user_id)
        claim.verified_at = now
        claim.verification_method = action.verification_method
        claim.risk_score = new_risk

        # Insert Immutable Status History
        history = ClaimStatusHistory(
            id=uuid.uuid4(),
            claim_id=claim.id,
            previous_status=prev_status,
            new_status=new_status,
            previous_assurance_level=prev_assurance,
            new_assurance_level=new_assurance,
            transition_reason=action.notes or f"Verified by {principal.username}",
            transitioned_by=uuid.UUID(principal.user_id),
            occurred_at=now
        )
        db.add(history)
        await db.flush()

        # Audit Logging
        await AuditService.record_audit_log(
            db=db,
            actor_id=uuid.UUID(principal.user_id),
            action="VERIFY_CLAIM",
            resource_type="DataClaim",
            resource_id=claim.id,
            organization_id=claim.organization_id,
            details={"status": new_status, "assurance": new_assurance, "method": action.verification_method}
        )

        # Domain Event Enqueueing
        event = DomainEventEnvelope(
            event_type="VarietyVerifiedEvent",
            aggregate_type="DataClaim",
            aggregate_id=claim.id,
            organization_id=claim.organization_id,
            actor_id=uuid.UUID(principal.user_id),
            payload={
                "claim_id": str(claim.id),
                "subject_type": claim.subject_type,
                "subject_id": str(claim.subject_id),
                "value_code": claim.value_code,
                "verification_status": new_status,
                "assurance_level": new_assurance,
                "verified_by": principal.user_id
            }
        )
        await OutboxService.enqueue_outbox_event(db, event)

        return await cls.get_claim_by_id(db, claim.id, principal)

    @classmethod
    async def list_claims(
        cls,
        db: AsyncSession,
        principal: Principal,
        subject_type: Optional[str] = None,
        subject_id: Optional[uuid.UUID] = None,
        verification_status: Optional[str] = None
    ) -> List[DataClaimResponse]:
        """List claims with DataScope filtering."""
        query = select(DataClaim).options(
            selectinload(DataClaim.declarant),
            selectinload(DataClaim.verifier),
            selectinload(DataClaim.status_history).selectinload(ClaimStatusHistory.actor),
            selectinload(DataClaim.evidence_links).selectinload(ClaimEvidenceLink.evidence)
        )

        if principal.data_scope != DataScope.ALL and principal.organization_id:
            query = query.where(DataClaim.organization_id == uuid.UUID(principal.organization_id))

        if subject_type:
            query = query.where(DataClaim.subject_type == subject_type)
        if subject_id:
            query = query.where(DataClaim.subject_id == subject_id)
        if verification_status:
            query = query.where(DataClaim.verification_status == verification_status)

        query = query.order_by(DataClaim.created_at.desc())
        res = await db.execute(query)
        claims = res.scalars().all()

        return [cls._to_response(c) for c in claims]

    @classmethod
    async def get_claim_by_id(
        cls,
        db: AsyncSession,
        claim_id: uuid.UUID,
        principal: Principal
    ) -> DataClaimResponse:
        """Fetch claim by ID with full history and evidence records."""
        query = select(DataClaim).where(DataClaim.id == claim_id).options(
            selectinload(DataClaim.declarant),
            selectinload(DataClaim.verifier)
        )
        res = await db.execute(query)
        claim = res.scalar_one_or_none()
        if not claim:
            raise NotFoundException(message_key="errors.claims.notFound", code="CLAIM_NOT_FOUND")

        if principal.data_scope != DataScope.ALL and principal.organization_id != str(claim.organization_id):
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        # Explicitly query immutable status history
        hist_query = (
            select(ClaimStatusHistory)
            .where(ClaimStatusHistory.claim_id == claim.id)
            .order_by(ClaimStatusHistory.occurred_at.asc())
        )
        hist_res = await db.execute(hist_query)
        histories = hist_res.scalars().all()

        # Explicitly query attached evidence
        ev_query = (
            select(ClaimEvidenceLink)
            .where(ClaimEvidenceLink.claim_id == claim.id)
        )
        ev_res = await db.execute(ev_query)
        evidence_links = ev_res.scalars().all()

        declarant_name = None
        if claim.declared_by:
            u_dec = await db.get(User, claim.declared_by)
            if u_dec:
                declarant_name = u_dec.full_name

        verifier_name = None
        if claim.verified_by:
            u_ver = await db.get(User, claim.verified_by)
            if u_ver:
                verifier_name = u_ver.full_name

        return cls._to_response(
            claim,
            histories=histories,
            evidence_links=evidence_links,
            declarant_name=declarant_name,
            verifier_name=verifier_name
        )

    @staticmethod
    def _to_response(
        c: DataClaim,
        histories: Optional[List[ClaimStatusHistory]] = None,
        evidence_links: Optional[List[ClaimEvidenceLink]] = None,
        declarant_name: Optional[str] = None,
        verifier_name: Optional[str] = None
    ) -> DataClaimResponse:
        hist_list = histories if histories is not None else (c.status_history or [])
        ev_list = evidence_links if evidence_links is not None else (c.evidence_links or [])

        history_out = [
            ClaimStatusHistoryResponse(
                id=h.id,
                previous_status=h.previous_status,
                new_status=h.new_status,
                previous_assurance_level=h.previous_assurance_level,
                new_assurance_level=h.new_assurance_level,
                transition_reason=h.transition_reason,
                transitioned_by=h.transitioned_by,
                transitioned_by_name=h.actor.full_name if h.actor else None,
                occurred_at=h.occurred_at
            )
            for h in hist_list
        ]
        evidence_out = [
            EvidenceResponse(
                id=link.evidence.id,
                evidence_type=link.evidence.evidence_type,
                evidence_hash=link.evidence.evidence_hash,
                captured_at=link.evidence.captured_at,
                metadata_json=link.evidence.metadata_json,
                created_at=link.evidence.created_at
            )
            for link in ev_list if link.evidence
        ]
        return DataClaimResponse(
            id=c.id,
            organization_id=c.organization_id,
            claim_type=c.claim_type,
            subject_type=c.subject_type,
            subject_id=c.subject_id,
            value_code=c.value_code,
            value_json=c.value_json,
            declared_by=c.declared_by,
            declared_by_name=declarant_name or (c.declarant.full_name if c.declarant else None),
            declared_at=c.declared_at,
            source_type=c.source_type,
            assurance_level=c.assurance_level,
            verification_status=c.verification_status,
            verified_by=c.verified_by,
            verified_by_name=verifier_name or (c.verifier.full_name if c.verifier else None),
            verified_at=c.verified_at,
            verification_method=c.verification_method,
            risk_score=float(c.risk_score),
            is_current=c.is_current,
            created_at=c.created_at,
            updated_at=c.updated_at,
            status_history=history_out,
            evidence_records=evidence_out
        )
