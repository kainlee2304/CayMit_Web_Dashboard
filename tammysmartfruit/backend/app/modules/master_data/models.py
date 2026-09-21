"""
Master Data Domain ORM Models (Module 3)
Crops, Varieties, Grades, Units, Activity Types, Market Codes with i18n Localization.
"""

from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from app.shared.types import PortableUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class Crop(Base):
    """Crops Master Aggregate Root."""
    __tablename__ = "crops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    scientific_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    translations: Mapped[List["CropTranslation"]] = relationship("CropTranslation", back_populates="crop", cascade="all, delete-orphan", lazy="selectin")
    varieties: Mapped[List["CropVariety"]] = relationship("CropVariety", back_populates="crop", lazy="selectin")
    grades: Mapped[List["QualityGrade"]] = relationship("QualityGrade", back_populates="crop", lazy="selectin")

class CropTranslation(Base):
    """Crop Localized Translations."""
    __tablename__ = "crop_translations"

    crop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crops.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True) # vi, en
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="translations")

class CropVariety(Base):
    """Crop Varieties Master."""
    __tablename__ = "crop_varieties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crops.id", ondelete="RESTRICT"), nullable=False, index=True)
    variety_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    standard_growth_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    optimal_brix_min: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), default=14.0, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="varieties")
    translations: Mapped[List["CropVarietyTranslation"]] = relationship("CropVarietyTranslation", back_populates="variety", cascade="all, delete-orphan", lazy="selectin")

class CropVarietyTranslation(Base):
    """Crop Variety Localized Translations."""
    __tablename__ = "crop_variety_translations"

    variety_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crop_varieties.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    characteristics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    variety: Mapped["CropVariety"] = relationship("CropVariety", back_populates="translations")

class QualityGrade(Base):
    """Quality Grades Master."""
    __tablename__ = "quality_grades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crops.id", ondelete="RESTRICT"), nullable=False, index=True)
    grade_code: Mapped[str] = mapped_column(String(40), nullable=False)
    min_brix: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    min_weight_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    allow_cosmetic_defects: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_export_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("crop_id", "grade_code", name="uq_crop_grade"),)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="grades")
    translations: Mapped[List["QualityGradeTranslation"]] = relationship("QualityGradeTranslation", back_populates="grade", cascade="all, delete-orphan", lazy="selectin")

class QualityGradeTranslation(Base):
    __tablename__ = "quality_grade_translations"

    grade_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quality_grades.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    grade: Mapped["QualityGrade"] = relationship("QualityGrade", back_populates="translations")

class Unit(Base):
    """Measurement Units Master."""
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    unit_type: Mapped[str] = mapped_column(String(30), nullable=False) # MASS, COUNT, AREA, QUALITY, TEMPERATURE, VOLUME
    is_si_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conversion_to_base: Mapped[float] = mapped_column(Numeric(14, 6), default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    translations: Mapped[List["UnitTranslation"]] = relationship("UnitTranslation", back_populates="unit", cascade="all, delete-orphan", lazy="selectin")

class UnitTranslation(Base):
    __tablename__ = "unit_translations"

    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    unit: Mapped["Unit"] = relationship("Unit", back_populates="translations")

class ActivityType(Base):
    """Farm & Supply Chain Activity Types Master."""
    __tablename__ = "activity_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    requires_material: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_gps_photo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    translations: Mapped[List["ActivityTypeTranslation"]] = relationship("ActivityTypeTranslation", back_populates="activity_type", cascade="all, delete-orphan", lazy="selectin")

class ActivityTypeTranslation(Base):
    __tablename__ = "activity_type_translations"

    activity_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activity_types.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    activity_type: Mapped["ActivityType"] = relationship("ActivityType", back_populates="translations")

class MarketCode(Base):
    """Export Market Destination Codes Master."""
    __tablename__ = "market_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    iso_country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    requires_puc: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_phc: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    translations: Mapped[List["MarketCodeTranslation"]] = relationship("MarketCodeTranslation", back_populates="market", cascade="all, delete-orphan", lazy="selectin")

class MarketCodeTranslation(Base):
    __tablename__ = "market_code_translations"

    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_codes.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    quarantine_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    market: Mapped["MarketCode"] = relationship("MarketCode", back_populates="translations")

class CertificateType(Base):
    """Certificate Types Master."""
    __tablename__ = "certificate_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cert_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    accreditation_body: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_export_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    translations: Mapped[List["CertificateTypeTranslation"]] = relationship("CertificateTypeTranslation", back_populates="cert_type", cascade="all, delete-orphan", lazy="selectin")

class CertificateTypeTranslation(Base):
    __tablename__ = "certificate_type_translations"

    cert_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("certificate_types.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cert_type: Mapped["CertificateType"] = relationship("CertificateType", back_populates="translations")

class MaterialType(Base):
    """Agricultural Input Material Types Master."""
    __tablename__ = "material_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    is_quarantine_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_organic_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
