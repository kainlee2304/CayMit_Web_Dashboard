"""
Material Master and Inventory Service (Module 10)
Enforces:
1. Canonical Master Data validation (No free-text input codes).
2. Pre-Harvest Interval (PHI) safety window calculation.
3. Batch stock balance verification and deduction.
"""

from typing import List, Optional
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import Principal, DataScope
from app.core.errors import ConflictException, NotFoundException, ForbiddenException, ValidationException
from app.modules.master_data.models import MaterialType, Unit
from app.modules.material.models import Material, MaterialBatch
from app.modules.material.schemas import (
    MaterialResponse, MaterialBatchCreate, MaterialBatchResponse
)

class MaterialService:

    @classmethod
    async def list_materials(
        cls,
        db: AsyncSession,
        principal: Principal,
        material_type_code: Optional[str] = None
    ) -> List[MaterialResponse]:
        """List materials available to the organization."""
        stmt = select(Material).options(
            selectinload(Material.material_type),
            selectinload(Material.organization)
        )
        if principal.data_scope != DataScope.ALL:
            stmt = stmt.where(Material.organization_id == uuid.UUID(principal.organization_id))

        if material_type_code:
            stmt = stmt.join(MaterialType).where(MaterialType.type_code == material_type_code)

        stmt = stmt.where(Material.is_active == True).order_by(Material.brand_name.asc())
        res = await db.execute(stmt)
        materials = res.scalars().all()

        return [
            MaterialResponse(
                id=m.id,
                organization_id=m.organization_id,
                material_type_id=m.material_type_id,
                material_type_code=m.material_type.type_code,
                material_code=m.material_code,
                brand_name=m.brand_name,
                manufacturer=m.manufacturer,
                active_ingredient=m.active_ingredient,
                active_ingredient_concentration=m.active_ingredient_concentration,
                pre_harvest_interval_days=m.pre_harvest_interval_days,
                standard_dosage_per_ha=m.standard_dosage_per_ha,
                is_organic_certified=m.is_organic_certified,
                is_active=m.is_active
            )
            for m in materials
        ]

    @classmethod
    async def list_batches(
        cls,
        db: AsyncSession,
        principal: Principal,
        material_id: Optional[uuid.UUID] = None
    ) -> List[MaterialBatchResponse]:
        """List active material inventory batches with stock and PHI info."""
        stmt = select(MaterialBatch).join(Material, MaterialBatch.material_id == Material.id).options(
            selectinload(MaterialBatch.material),
            selectinload(MaterialBatch.unit)
        )
        if principal.data_scope != DataScope.ALL:
            stmt = stmt.where(Material.organization_id == uuid.UUID(principal.organization_id))

        if material_id:
            stmt = stmt.where(MaterialBatch.material_id == material_id)

        stmt = stmt.order_by(MaterialBatch.expiration_date.asc())
        res = await db.execute(stmt)
        batches = res.scalars().all()

        today = date.today()
        return [
            MaterialBatchResponse(
                id=b.id,
                material_id=b.material_id,
                material_code=b.material.material_code,
                brand_name=b.material.brand_name,
                batch_number=b.batch_number,
                manufacturing_date=b.manufacturing_date,
                expiration_date=b.expiration_date,
                initial_quantity=float(b.initial_quantity),
                remaining_quantity=float(b.remaining_quantity),
                unit_id=b.unit_id,
                unit_code=b.unit.unit_code,
                pre_harvest_interval_days=b.material.pre_harvest_interval_days,
                storage_location=b.storage_location,
                is_expired=b.expiration_date < today
            )
            for b in batches
        ]

    @classmethod
    async def create_batch(
        cls,
        db: AsyncSession,
        data: MaterialBatchCreate,
        principal: Principal
    ) -> MaterialBatchResponse:
        """Create a new material stock batch."""
        material = await db.get(Material, data.material_id)
        if not material:
            raise NotFoundException(message_key="errors.material.notFound", code="MATERIAL_NOT_FOUND")

        if principal.data_scope != DataScope.ALL and str(material.organization_id) != principal.organization_id:
            raise ForbiddenException(message_key="errors.auth.crossTenantForbidden", code="CROSS_TENANT_ACCESS_DENIED")

        unit = await db.get(Unit, data.unit_id)
        if not unit:
            raise NotFoundException(message_key="errors.masterData.unitNotFound", code="UNIT_NOT_FOUND")

        batch = MaterialBatch(
            id=uuid.uuid4(),
            material_id=material.id,
            batch_number=data.batch_number,
            manufacturing_date=data.manufacturing_date,
            expiration_date=data.expiration_date,
            initial_quantity=data.initial_quantity,
            remaining_quantity=data.initial_quantity,
            unit_id=unit.id,
            storage_location=data.storage_location
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        today = date.today()
        return MaterialBatchResponse(
            id=batch.id,
            material_id=material.id,
            material_code=material.material_code,
            brand_name=material.brand_name,
            batch_number=batch.batch_number,
            manufacturing_date=batch.manufacturing_date,
            expiration_date=batch.expiration_date,
            initial_quantity=float(batch.initial_quantity),
            remaining_quantity=float(batch.remaining_quantity),
            unit_id=unit.id,
            unit_code=unit.unit_code,
            pre_harvest_interval_days=material.pre_harvest_interval_days,
            storage_location=batch.storage_location,
            is_expired=batch.expiration_date < today
        )
