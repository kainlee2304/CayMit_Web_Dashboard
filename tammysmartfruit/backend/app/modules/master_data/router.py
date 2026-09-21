"""
Master Data API Endpoints (Module 3)
Provides canonical code lookups, units, activity types, and varieties.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.master_data.service import MasterDataService
from app.modules.master_data.schemas import (
    CropResponse, CropVarietyResponse, UnitResponse,
    ActivityTypeResponse, MarketCodeResponse
)

router = APIRouter(prefix="/master-data", tags=["Master Data"])

@router.get("/crops", response_model=List[CropResponse])
async def list_crops(
    locale: str = Query("vi", description="Language locale ('vi' or 'en')"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """List all active crops with their varieties and quality grades."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_crops(db, locale=effective_locale)

@router.get("/crops/{crop_code}", response_model=CropResponse)
async def get_crop(
    crop_code: str,
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """Get single crop details with varieties."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_crop_by_code(db, crop_code=crop_code, locale=effective_locale)

@router.get("/varieties", response_model=List[CropVarietyResponse])
async def list_varieties(
    crop_code: Optional[str] = Query(None, description="Filter by crop_code e.g. JACKFRUIT"),
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """List canonical crop varieties."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_varieties(db, crop_code=crop_code, locale=effective_locale)

@router.get("/varieties/{variety_code}", response_model=CropVarietyResponse)
async def get_variety(
    variety_code: str,
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """Get specific variety detail."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_variety_by_code(db, variety_code=variety_code, locale=effective_locale)

@router.get("/units", response_model=List[UnitResponse])
async def list_units(
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """List standardized measurement units."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_units(db, locale=effective_locale)

@router.get("/activity-types", response_model=List[ActivityTypeResponse])
async def list_activity_types(
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """List standard agricultural activity types."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_activity_types(db, locale=effective_locale)

@router.get("/market-codes", response_model=List[MarketCodeResponse])
async def list_market_codes(
    locale: str = Query("vi"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: AsyncSession = Depends(get_db)
):
    """List destination export markets."""
    effective_locale = "en" if accept_language and "en" in accept_language else locale
    return await MasterDataService.get_market_codes(db, locale=effective_locale)
