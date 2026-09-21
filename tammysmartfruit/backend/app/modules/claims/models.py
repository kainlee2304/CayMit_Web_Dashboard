"""
Data Claims, Verification Pipeline, and Evidence ORM Models (Modules 24, 25, 26)
Enforces immutable transition history and assurance levels.
"""

from typing import Optional, List, Any, Dict
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, UniqueConstraint
from app.shared.types import PortableUUID as UUID, PortableJSON as JSONB, PortableGeometry as Geometry
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base

class DataClaim(Base):
    """Data Claims Aggregate Root (Module 25)."""
    __tablename__ = "data_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    claim_type: Mapped[str] = mapped_column(String(80), nullable=False) # CROP_VARIETY, AREA_PUC, PLOT_LOCATION, QUALITY_GRADE
    subject_type: Mapped[str] = mapped_column(String(60), nullable=False) # PLOT, TREE_GROUP, FARM, GROWING_AREA
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    value_code: Mapped[str] = mapped_column(String(80), nullable=False) # JACKFRUIT_THAI, PUC-VN-TG-00125
    value_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    declared_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), default="FARMER_DECLARATION", nullable=False) # FARMER_DECLARATION, TECHNICIAN_INSPECTION
    assurance_level: Mapped[str] = mapped_column(String(40), default="LEVEL_0_DECLARED", nullable=False) # LEVEL_0_DECLARED, LEVEL_1_SYSTEM_VALIDATED, LEVEL_2_ORGANIZATION_VERIFIED
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False) # PENDING, VERIFIED, REJECTED, DISPUTED, REVOKED, SUPERSEDED
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.00, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_by_claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("data_claims.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", lazy="joined")
    declarant = relationship("User", foreign_keys=[declared_by], lazy="joined")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="joined")
    status_history: Mapped[List["ClaimStatusHistory"]] = relationship("ClaimStatusHistory", back_populates="claim", cascade="all, delete-orphan", lazy="selectin")
    evidence_links: Mapped[List["ClaimEvidenceLink"]] = relationship("ClaimEvidenceLink", back_populates="claim", cascade="all, delete-orphan", lazy="selectin")

class ClaimStatusHistory(Base):
    """Immutable Append-Only Claim Status Transitions."""
    __tablename__ = "claim_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_claims.id", ondelete="RESTRICT"), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(40), nullable=False)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_assurance_level: Mapped[str] = mapped_column(String(40), nullable=False)
    new_assurance_level: Mapped[str] = mapped_column(String(40), nullable=False)
    transition_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transitioned_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    claim: Mapped["DataClaim"] = relationship("DataClaim", back_populates="status_history")
    actor = relationship("User", foreign_keys=[transitioned_by], lazy="joined")

class EvidenceRecord(Base):
    """Evidence Records Aggregate Root (Module 26)."""
    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False) # GEOTAGGED_PHOTO, IOT_SENSOR_SNAPSHOT, PHYSICAL_MEASUREMENT
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True) # SHA-256
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gps_point = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    creator = relationship("User", foreign_keys=[created_by], lazy="joined")

class ClaimEvidenceLink(Base):
    """Junction Table Linking Evidence to Data Claim."""
    __tablename__ = "claim_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_claims.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=False, index=True)
    relevance_weight: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    linked_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (UniqueConstraint("claim_id", "evidence_id", name="uq_claim_evidence"),)

    claim: Mapped["DataClaim"] = relationship("DataClaim", back_populates="evidence_links")
    evidence: Mapped["EvidenceRecord"] = relationship("EvidenceRecord", lazy="joined")
