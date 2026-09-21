"""
Spatial PostGIS Schemas and Geofence Contracts
"""

from typing import List, Optional, Any, Dict, Union
from enum import Enum
from pydantic import BaseModel, Field

class GeofenceStatus(str, Enum):
    INSIDE = "INSIDE"
    NEAR_BOUNDARY = "NEAR_BOUNDARY"
    OUTSIDE = "OUTSIDE"
    LOW_ACCURACY = "LOW_ACCURACY"

class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")

class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]] = Field(..., description="Array of linear rings [[ [lng, lat], ... ]]")

class GeofenceEvaluationInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_meters: float = Field(default=5.0, ge=0.0)
    captured_at: Optional[str] = None
    device_metadata: Optional[Dict[str, Any]] = None

class GeofenceEvaluationResult(BaseModel):
    status: GeofenceStatus
    distance_meters: float
    accuracy_meters: float
    is_trusted: bool
    risk_points: float
    message: str
