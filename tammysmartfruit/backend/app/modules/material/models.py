"""
Materials, Batches, and Material Usages ORM Models (Module 10)
Manages agricultural inputs, stock batches, and Pre-Harvest Interval (PHI) compliance.
"""

from typing import Optional, List
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from app.shared.types import PortableUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class Material(Base):
    """Material Master Aggregate Root (Module 10)."""
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    material_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("material_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    material_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True) # MAT-NPK-BIO-01
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(120), nullable=False)
    active_ingredient: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    active_ingredient_concentration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pre_harvest_interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # PHI in days
    standard_dosage_per_ha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_organic_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", lazy="joined")
    material_type = relationship("MaterialType", lazy="joined")
    batches: Mapped[List["MaterialBatch"]] = relationship("MaterialBatch", back_populates="material", cascade="all, delete-orphan", lazy="selectin")

class MaterialBatch(Base):
    """Material Inventory Batch (Module 10)."""
    __tablename__ = "material_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    batch_number: Mapped[str] = mapped_column(String(60), nullable=False)
    manufacturing_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False)
    storage_location: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("material_id", "batch_number", name="uq_material_batch"),)

    material: Mapped["Material"] = relationship("Material", back_populates="batches", lazy="joined")
    unit = relationship("Unit", lazy="joined")

class MaterialUsage(Base):
    """Material Usage in a Farm Activity (Module 10)."""
    __tablename__ = "material_usages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("farm_activities.id", ondelete="CASCADE"), nullable=False, index=True)
    material_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("material_batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity_applied: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False)
    phi_days_applied: Mapped[int] = mapped_column(Integer, nullable=False)
    earliest_safe_harvest_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    application_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # FOLIAR_SPRAY, SOIL_DRENCH, ROOT_FERTILIZE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    activity = relationship("FarmActivity", back_populates="material_usages")
    material_batch: Mapped["MaterialBatch"] = relationship("MaterialBatch", lazy="joined")
    unit = relationship("Unit", lazy="joined")
