"""
Global Search Pydantic Schemas
"""

from typing import List, Optional, Any, Dict
import uuid
from pydantic import BaseModel, ConfigDict

class SearchResultItem(BaseModel):
    id: uuid.UUID
    category: str # "FARMER", "GROWING_AREA", "FARM", "PLOT"
    title: str
    subtitle: Optional[str] = None
    code: str
    organization_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class GlobalSearchResponse(BaseModel):
    query: str
    total_count: int
    results: List[SearchResultItem]
