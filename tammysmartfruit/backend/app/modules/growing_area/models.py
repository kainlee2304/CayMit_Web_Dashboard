"""
Growing Area Domain ORM Models (Module 5)
Plant Unit Code (PUC) and PostGIS Spatial Polygon Boundaries (SRID 4326).
"""

from typing import Optional, List, Any, Dict
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Numeric, Text
from app.shared.types import PortableUUID as UUID, PortableGeometry as Geometry
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class GrowingArea(Base):
    """Growing Area Aggregate Root (Module 5)."""
    __tablename__ = "growing_areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    area_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    area_name: Mapped[str] = mapped_column(String(120), nullable=False)
    puc_registration_code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    puc_issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    puc_expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    puc_status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False) # PENDING_APPROVAL, ACTIVE, SUSPENDED, EXPIRED, REVOKED
    province_code: Mapped[str] = mapped_column(String(20), nullable=False)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False)
    commune_code: Mapped[str] = mapped_column(String(20), nullable=False)
    total_area_hectares: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    
    # PostGIS Spatial Geometries
    boundary_polygon = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    buffer_zone_polygon = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)
    centroid_point = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    farms = relationship("Farm", back_populates="growing_area", lazy="selectin")
