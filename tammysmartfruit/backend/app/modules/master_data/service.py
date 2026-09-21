"""
Master Data Service
Provides fast localized querying across Crops, Varieties, Units, Activity Types, and Markets.
"""

from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.master_data.models import (
    Crop, CropTranslation, CropVariety, CropVarietyTranslation,
    QualityGrade, QualityGradeTranslation, Unit, UnitTranslation,
    ActivityType, ActivityTypeTranslation, MarketCode, MarketCodeTranslation,
    CertificateType, CertificateTypeTranslation
)
from app.modules.master_data.schemas import (
    CropResponse, CropVarietyResponse, QualityGradeResponse,
    UnitResponse, ActivityTypeResponse, MarketCodeResponse, CertificateTypeResponse
)
from app.core.errors import NotFoundException

class MasterDataService:

    @staticmethod
    def _resolve_trans(translations, locale: str, fallback_field: str = "name") -> tuple[str, Optional[str]]:
        """Resolve localized name and description with fallback to 'vi' then 'en'."""
        trans_map = {t.locale: t for t in translations}
        selected = trans_map.get(locale) or trans_map.get("vi") or trans_map.get("en")
        if selected:
            name = getattr(selected, "name", fallback_field)
            desc = getattr(selected, "description", None) or getattr(selected, "characteristics", None) or getattr(selected, "instructions", None) or getattr(selected, "quarantine_notes", None)
            return name, desc
        return fallback_field, None

    @classmethod
    async def get_crops(cls, db: AsyncSession, locale: str = "vi") -> List[CropResponse]:
        query = select(Crop).where(Crop.is_active == True).options(
            selectinload(Crop.translations),
            selectinload(Crop.varieties).selectinload(CropVariety.translations),
            selectinload(Crop.grades).selectinload(QualityGrade.translations)
        )
        res = await db.execute(query)
        crops = res.scalars().all()

        output = []
        for c in crops:
            name, desc = cls._resolve_trans(c.translations, locale, fallback_field=c.crop_code)
            all_translations = {t.locale: t.name for t in c.translations}

            varieties_out = []
            for v in c.varieties:
                v_name, v_char = cls._resolve_trans(v.translations, locale, fallback_field=v.variety_code)
                v_trans = {t.locale: t.name for t in v.translations}
                varieties_out.append(CropVarietyResponse(
                    id=v.id,
                    variety_code=v.variety_code,
                    name=v_name,
                    characteristics=v_char,
                    standard_growth_days=v.standard_growth_days,
                    optimal_brix_min=float(v.optimal_brix_min) if v.optimal_brix_min else None,
                    is_active=v.is_active,
                    translations=v_trans
                ))

            grades_out = []
            for g in c.grades:
                g_name, g_desc = cls._resolve_trans(g.translations, locale, fallback_field=g.grade_code)
                grades_out.append(QualityGradeResponse(
                    id=g.id,
                    grade_code=g.grade_code,
                    name=g_name,
                    description=g_desc,
                    min_brix=float(g.min_brix),
                    min_weight_kg=float(g.min_weight_kg),
                    max_weight_kg=float(g.max_weight_kg) if g.max_weight_kg else None,
                    allow_cosmetic_defects=g.allow_cosmetic_defects,
                    is_export_eligible=g.is_export_eligible,
                    is_active=g.is_active
                ))

            output.append(CropResponse(
                id=c.id,
                crop_code=c.crop_code,
                scientific_name=c.scientific_name,
                name=name,
                description=desc,
                is_active=c.is_active,
                varieties=varieties_out,
                grades=grades_out,
                translations=all_translations
            ))
        return output

    @classmethod
    async def get_crop_by_code(cls, db: AsyncSession, crop_code: str, locale: str = "vi") -> CropResponse:
        query = select(Crop).where(Crop.crop_code == crop_code).options(
            selectinload(Crop.translations),
            selectinload(Crop.varieties).selectinload(CropVariety.translations),
            selectinload(Crop.grades).selectinload(QualityGrade.translations)
        )
        res = await db.execute(query)
        c = res.scalar_one_or_none()
        if not c:
            raise NotFoundException(message_key="errors.master_data.cropNotFound", code="CROP_NOT_FOUND")

        name, desc = cls._resolve_trans(c.translations, locale, fallback_field=c.crop_code)
        all_translations = {t.locale: t.name for t in c.translations}

        varieties_out = []
        for v in c.varieties:
            v_name, v_char = cls._resolve_trans(v.translations, locale, fallback_field=v.variety_code)
            v_trans = {t.locale: t.name for t in v.translations}
            varieties_out.append(CropVarietyResponse(
                id=v.id,
                variety_code=v.variety_code,
                name=v_name,
                characteristics=v_char,
                standard_growth_days=v.standard_growth_days,
                optimal_brix_min=float(v.optimal_brix_min) if v.optimal_brix_min else None,
                is_active=v.is_active,
                translations=v_trans
            ))

        grades_out = []
        for g in c.grades:
            g_name, g_desc = cls._resolve_trans(g.translations, locale, fallback_field=g.grade_code)
            grades_out.append(QualityGradeResponse(
                id=g.id,
                grade_code=g.grade_code,
                name=g_name,
                description=g_desc,
                min_brix=float(g.min_brix),
                min_weight_kg=float(g.min_weight_kg),
                max_weight_kg=float(g.max_weight_kg) if g.max_weight_kg else None,
                allow_cosmetic_defects=g.allow_cosmetic_defects,
                is_export_eligible=g.is_export_eligible,
                is_active=g.is_active
            ))

        return CropResponse(
            id=c.id,
            crop_code=c.crop_code,
            scientific_name=c.scientific_name,
            name=name,
            description=desc,
            is_active=c.is_active,
            varieties=varieties_out,
            grades=grades_out,
            translations=all_translations
        )

    @classmethod
    async def get_varieties(cls, db: AsyncSession, crop_code: Optional[str] = None, locale: str = "vi") -> List[CropVarietyResponse]:
        query = select(CropVariety).where(CropVariety.is_active == True).options(
            selectinload(CropVariety.translations),
            selectinload(CropVariety.crop)
        )
        if crop_code:
            query = query.join(Crop).where(Crop.crop_code == crop_code)

        res = await db.execute(query)
        varieties = res.scalars().all()

        output = []
        for v in varieties:
            v_name, v_char = cls._resolve_trans(v.translations, locale, fallback_field=v.variety_code)
            v_trans = {t.locale: t.name for t in v.translations}
            output.append(CropVarietyResponse(
                id=v.id,
                variety_code=v.variety_code,
                name=v_name,
                characteristics=v_char,
                standard_growth_days=v.standard_growth_days,
                optimal_brix_min=float(v.optimal_brix_min) if v.optimal_brix_min else None,
                is_active=v.is_active,
                translations=v_trans
            ))
        return output

    @classmethod
    async def get_variety_by_code(cls, db: AsyncSession, variety_code: str, locale: str = "vi") -> CropVarietyResponse:
        query = select(CropVariety).where(CropVariety.variety_code == variety_code).options(
            selectinload(CropVariety.translations)
        )
        res = await db.execute(query)
        v = res.scalar_one_or_none()
        if not v:
            raise NotFoundException(message_key="errors.master_data.varietyNotFound", code="VARIETY_NOT_FOUND")

        v_name, v_char = cls._resolve_trans(v.translations, locale, fallback_field=v.variety_code)
        v_trans = {t.locale: t.name for t in v.translations}
        return CropVarietyResponse(
            id=v.id,
            variety_code=v.variety_code,
            name=v_name,
            characteristics=v_char,
            standard_growth_days=v.standard_growth_days,
            optimal_brix_min=float(v.optimal_brix_min) if v.optimal_brix_min else None,
            is_active=v.is_active,
            translations=v_trans
        )

    @classmethod
    async def get_units(cls, db: AsyncSession, locale: str = "vi") -> List[UnitResponse]:
        query = select(Unit).options(selectinload(Unit.translations))
        res = await db.execute(query)
        units = res.scalars().all()

        output = []
        for u in units:
            trans_map = {t.locale: t for t in u.translations}
            selected = trans_map.get(locale) or trans_map.get("vi") or trans_map.get("en")
            name = selected.name if selected else u.unit_code
            symbol = selected.symbol if selected else u.unit_code
            output.append(UnitResponse(
                id=u.id,
                unit_code=u.unit_code,
                unit_type=u.unit_type,
                name=name,
                symbol=symbol,
                is_si_base=u.is_si_base,
                conversion_to_base=float(u.conversion_to_base)
            ))
        return output

    @classmethod
    async def get_activity_types(cls, db: AsyncSession, locale: str = "vi") -> List[ActivityTypeResponse]:
        query = select(ActivityType).where(ActivityType.is_active == True).options(selectinload(ActivityType.translations))
        res = await db.execute(query)
        acts = res.scalars().all()

        output = []
        for a in acts:
            name, instr = cls._resolve_trans(a.translations, locale, fallback_field=a.activity_code)
            output.append(ActivityTypeResponse(
                id=a.id,
                activity_code=a.activity_code,
                name=name,
                instructions=instr,
                requires_material=a.requires_material,
                requires_gps_photo=a.requires_gps_photo,
                is_active=a.is_active
            ))
        return output

    @classmethod
    async def get_market_codes(cls, db: AsyncSession, locale: str = "vi") -> List[MarketCodeResponse]:
        query = select(MarketCode).where(MarketCode.is_active == True).options(selectinload(MarketCode.translations))
        res = await db.execute(query)
        markets = res.scalars().all()

        output = []
        for m in markets:
            name, notes = cls._resolve_trans(m.translations, locale, fallback_field=m.market_code)
            output.append(MarketCodeResponse(
                id=m.id,
                market_code=m.market_code,
                iso_country_code=m.iso_country_code,
                name=name,
                quarantine_notes=notes,
                requires_puc=m.requires_puc,
                requires_phc=m.requires_phc,
                is_active=m.is_active
            ))
        return output
