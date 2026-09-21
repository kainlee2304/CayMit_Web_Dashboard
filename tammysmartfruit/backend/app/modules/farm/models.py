"""
Farm, Plot, TreeGroup, and Farmer Assignment ORM Models (Modules 6 & 7)
PostGIS spatial polygons and hierarchical agricultural assets.
"""

from typing import Optional, List
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from app.shared.types import PortableUUID as UUID, PortableGeometry as Geometry
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class Farm(Base):
    """Farm Aggregate Root (Module 6)."""
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    growing_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("growing_areas.id", ondelete="RESTRICT"), nullable=False, index=True)
    farm_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    farm_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_farmer_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    total_plots_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    farm_area_hectares: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", lazy="joined")
    growing_area = relationship("GrowingArea", back_populates="farms", lazy="joined")
    owner = relationship("User", foreign_keys=[owner_farmer_user_id], lazy="joined")
    plots: Mapped[List["Plot"]] = relationship("Plot", back_populates="farm", cascade="all, delete-orphan", lazy="selectin")
    farmer_assignments: Mapped[List["FarmFarmerAssignment"]] = relationship("FarmFarmerAssignment", back_populates="farm", cascade="all, delete-orphan", lazy="selectin")

class Plot(Base):
    """Plot Aggregate Root with PostGIS Spatial Polygon (Module 7)."""
    __tablename__ = "plots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="RESTRICT"), nullable=False, index=True)
    plot_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    plot_name: Mapped[str] = mapped_column(String(100), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    
    # PostGIS Spatial Geometries
    boundary_polygon = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    centroid_point = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)

    soil_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # BASALTIC, ALLUVIAL, SANDY_LOAM
    topography: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # FLAT, SLIGHT_SLOPE, HILLY
    irrigation_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # DRIP_IRRIGATION, SPRINKLER, MANUAL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    farm: Mapped["Farm"] = relationship("Farm", back_populates="plots", lazy="joined")
    tree_groups: Mapped[List["TreeGroup"]] = relationship("TreeGroup", back_populates="plot", cascade="all, delete-orphan", lazy="selectin")

class TreeGroup(Base):
    """Tree Group / Sub-plot Block within a Plot."""
    __tablename__ = "tree_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plots.id", ondelete="RESTRICT"), nullable=False, index=True)
    group_code: Mapped[str] = mapped_column(String(50), nullable=False)
    crop_variety_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crop_varieties.id", ondelete="RESTRICT"), nullable=False, index=True)
    planting_date: Mapped[date] = mapped_column(Date, nullable=False)
    tree_count: Mapped[int] = mapped_column(Integer, nullable=False)
    row_spacing_meters: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), default=6.00, nullable=True)
    tree_spacing_meters: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), default=5.00, nullable=True)
    estimated_annual_yield_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    health_status: Mapped[str] = mapped_column(String(30), default="HEALTHY", nullable=False) # HEALTHY, MONITORING, DISEASE_INFESTED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("plot_id", "group_code", name="uq_plot_group_code"),)

    plot: Mapped["Plot"] = relationship("Plot", back_populates="tree_groups")
    variety = relationship("CropVariety", lazy="joined")

class FarmFarmerAssignment(Base):
    """Farmer Assignment to Farm."""
    __tablename__ = "farm_farmer_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(40), default="PRIMARY_CULTIVATOR", nullable=False) # PRIMARY_CULTIVATOR, SEASONAL_WORKER
    contract_ref: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("farm_id", "farmer_user_id", name="uq_farm_farmer"),)

    farm: Mapped["Farm"] = relationship("Farm", back_populates="farmer_assignments")
    farmer = relationship("User", lazy="joined")
