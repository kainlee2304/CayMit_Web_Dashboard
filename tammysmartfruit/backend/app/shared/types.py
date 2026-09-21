"""
Portable SQLAlchemy Type Decorators
Provides seamless compatibility between PostgreSQL (UUID, JSONB, INET, Geometry)
and SQLite (CHAR(36), JSON, VARCHAR(45), TEXT).
"""

import json
import uuid
from typing import Any, Optional
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB, INET as PG_INET


class PortableUUID(types.TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex.
    """
    impl = types.CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(types.CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class PortableJSON(types.TypeDecorator):
    """
    Platform-independent JSON type.
    Uses PostgreSQL's JSONB type, otherwise uses standard SQLAlchemy JSON.
    """
    impl = types.JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(types.JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class PortableINET(types.TypeDecorator):
    """
    Platform-independent IP address type.
    Uses PostgreSQL's INET type, otherwise uses String(45).
    """
    impl = types.String(45)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_INET())
        return dialect.type_descriptor(types.String(45))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


class PortableGeometry(types.TypeDecorator):
    """
    Platform-independent Spatial Geometry type.
    On PostgreSQL uses GeoAlchemy2 Geometry, on SQLite stores as GeoJSON string / Text.
    """
    impl = types.Text
    cache_ok = True

    def __init__(self, geometry_type="POLYGON", srid=4326, **kwargs):
        super().__init__()
        self.geometry_type = geometry_type
        self.srid = srid

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from geoalchemy2 import Geometry
                return dialect.type_descriptor(Geometry(geometry_type=self.geometry_type, srid=self.srid))
            except ImportError:
                pass
        return dialect.type_descriptor(types.Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value
