"""
Crop Seasons and Yield Estimation ORM Models (Module 8)
Manages crop season lifecycle and yield forecasts.
"""

from typing import Optional, List
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from app.shared.types import PortableUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class CropSeason(Base):
    """Crop Season Aggregate Root (Module 8)."""
    __tablename__ = "crop_seasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plots.id", ondelete="RESTRICT"), nullable=False, index=True)
    season_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True) # SEA-2026-PLOT01-M01
    season_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_start: Mapped[date] = mapped_column(Date, nullable=False)
    expected_harvest_end: Mapped[date] = mapped_column(Date, nullable=False)
    actual_harvest_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    forecasted_yield_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    actual_harvested_yield_kg: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    season_status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True) # DRAFT, PLANNED, ACTIVE, HARVESTING, COMPLETED, CLOSED
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    plot = relationship("Plot", lazy="joined")
    closer = relationship("User", foreign_keys=[closed_by], lazy="joined")
    yield_estimates: Mapped[List["YieldEstimate"]] = relationship("YieldEstimate", back_populates="season", cascade="all, delete-orphan", lazy="selectin")
    activities: Mapped[List["FarmActivity"]] = relationship("FarmActivity", back_populates="season", cascade="all, delete-orphan", lazy="selectin")

class YieldEstimate(Base):
    """Yield Estimate History (Module 8)."""
    __tablename__ = "yield_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crop_seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    estimation_method: Mapped[str] = mapped_column(String(50), nullable=False) # TREE_COUNT_SAMPLING, AI_CANOPY_DENSITY, HISTORICAL_AVERAGE, MANUAL_INSPECTION
    estimated_yield_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_level_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), default=90.00, nullable=True)
    estimated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    estimated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    season: Mapped["CropSeason"] = relationship("CropSeason", back_populates="yield_estimates")
    estimator = relationship("User", foreign_keys=[estimated_by], lazy="joined")
