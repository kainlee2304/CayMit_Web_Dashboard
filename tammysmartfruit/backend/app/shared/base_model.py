"""
Shared Domain & Infrastructure Base Classes
"""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.shared.types import PortableUUID, PortableJSON, PortableINET, PortableGeometry
import uuid

class Base(DeclarativeBase):
    """Declarative base class matching physical domain tables."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to dictionary."""
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
