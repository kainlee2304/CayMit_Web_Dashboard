"""
Farm Activities (Farm Diary) ORM Models (Module 9)
Records agronomic activities (irrigation, fertilization, spraying, pruning, bagging)
with GPS geofencing, material usages, and data trust verification.
"""

from typing import Optional, List
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Numeric, Text
from app.shared.types import PortableUUID as UUID, PortableGeometry as Geometry
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class FarmActivity(Base):
    """Farm Activity Aggregate Root (Module 9: Farm Diary)."""
    __tablename__ = "farm_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crop_seasons.id", ondelete="RESTRICT"), nullable=False, index=True)
    activity_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activity_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    activity_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True) # ACT-2026-000451
    performed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    gps_point = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    gps_accuracy_meters: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    is_geofence_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_hours: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    weather_condition: Mapped[Optional[str]] = mapped_column(String(40), nullable=True) # SUNNY, CLOUDY, RAIN, HIGH_HUMIDITY
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    season = relationship("CropSeason", back_populates="activities", lazy="joined")
    activity_type = relationship("ActivityType", lazy="joined")
    performer = relationship("User", foreign_keys=[performed_by_user_id], lazy="joined")
    material_usages: Mapped[List["MaterialUsage"]] = relationship("MaterialUsage", back_populates="activity", cascade="all, delete-orphan", lazy="selectin")
