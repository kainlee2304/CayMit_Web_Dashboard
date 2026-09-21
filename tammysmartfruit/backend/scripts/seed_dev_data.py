"""
Development & Testing Database Seeding Script
Seeds Canonical Roles, Permissions, Default Tam My Organizations, Test Users,
Master Data (Crops, Varieties, Grades, Units, Activities, Markets),
and Sample Agricultural Entities (Growing Area, Farm, Plots, TreeGroups, Claims).
"""

import asyncio
from datetime import datetime, date, timezone
import json
import os
import sys
import uuid

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from passlib.hash import pbkdf2_sha256
from sqlalchemy import select, text
from app.core.database import get_db_context
from app.core.security import hash_password_argon2
from app.core.rbac import CanonicalRole, DataScope
from app.modules.identity.models import User, UserCredential, Role, Permission, RolePermission, UserRole
from app.modules.organization.models import Organization, UserOrganizationMembership, MembershipRole, DataScopeAssignment
from app.modules.master_data.models import (
    Crop, CropTranslation, CropVariety, CropVarietyTranslation,
    QualityGrade, QualityGradeTranslation, Unit, UnitTranslation,
    ActivityType, ActivityTypeTranslation, MarketCode, MarketCodeTranslation,
    MaterialType
)
from app.modules.growing_area.models import GrowingArea
from app.modules.farm.models import Farm, Plot, TreeGroup, FarmFarmerAssignment
from app.modules.claims.models import DataClaim, ClaimStatusHistory
from app.modules.material.models import Material, MaterialBatch, MaterialUsage
from app.modules.season.models import CropSeason, YieldEstimate
from app.modules.farm_activity.models import FarmActivity

CANONICAL_ROLES_DATA = [
    ("admin_hq", "Quản trị viên Hệ thống Tam Mỹ", "System HQ Administrator", "ALL"),
    ("technician", "Kỹ thuật viên Nông nghiệp", "Agricultural Field Technician", "COOPERATIVE"),
    ("farmer", "Nông hộ / Xã viên", "Farmer / Smallholder", "OWN"),
    ("packhouse_lead", "Trưởng xưởng Sơ chế & Đóng gói", "Packhouse Production Lead", "ORGANIZATION"),
    ("qa_qc", "Chuyên viên Kiểm soát Chất lượng QA/QC", "Quality Control Inspector", "ORGANIZATION"),
    ("warehouse_keeper", "Thủ kho Lạnh", "Cold Storage Warehouse Keeper", "ORGANIZATION"),
    ("logistics_driver", "Tài xế Vận tải Lạnh", "Refrigerated Fleet Driver", "ASSIGNED"),
    ("export_officer", "Chuyên viên Xuất nhập khẩu", "Export & Customs Officer", "ORGANIZATION"),
    ("auditor_inspector", "Thanh tra Độc lập & Đánh giá", "Independent Certification Auditor", "ALL"),
    ("buyer_partner", "Đối tác Thu mua B2B", "B2B Commercial Buyer", "ASSIGNED"),
    ("system_worker", "Tiến trình Xử lý Nền", "System Background Worker", "ALL"),
]

PERMISSIONS_DATA = [
    ("org:create", "organization", "create", "Tạo tổ chức mới"),
    ("org:read", "organization", "read", "Xem thông tin tổ chức"),
    ("org:update", "organization", "update", "Cập nhật thông tin tổ chức"),
    ("user:create", "user", "create", "Tạo tài khoản người dùng"),
    ("user:read", "user", "read", "Xem thông tin người dùng"),
    ("farm:create", "farm", "create", "Đăng ký vùng trồng / nông trại / thửa đất"),
    ("farm:read", "farm", "read", "Xem dữ liệu nông trại"),
    ("farm:verify", "farm", "verify", "Kiểm định kỹ thuật / xác minh nông trại"),
    ("harvest:create", "harvest", "create", "Ghi nhận nhật ký thu hoạch"),
    ("harvest:read", "harvest", "read", "Xem dữ liệu thu hoạch"),
    ("qc:approve", "qc", "approve", "Phê duyệt kiểm định chất lượng"),
    ("audit:read", "audit", "read", "Xem nhật ký kiểm toán hệ thống"),
]

async def seed_database():
    import app.core.database as db_module
    from app.shared.base_model import Base
    if not await db_module.check_db_health():
        await db_module.switch_to_sqlite()
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with db_module.get_db_context() as db:
        print("[SEED 1] Seeding Roles and Permissions...")
        roles_map = {}
        for role_code, name_vi, name_en, default_scope in CANONICAL_ROLES_DATA:
            res = await db.execute(select(Role).where(Role.role_code == role_code))
            role = res.scalar_one_or_none()
            if not role:
                role = Role(
                    role_code=role_code,
                    name_vi=name_vi,
                    name_en=name_en,
                    description=f"Standard Canonical Role: {role_code}",
                    is_system_role=True
                )
                db.add(role)
                await db.flush()
            roles_map[role_code] = role

        perms_map = {}
        for perm_code, res_name, act_name, desc in PERMISSIONS_DATA:
            res = await db.execute(select(Permission).where(Permission.permission_code == perm_code))
            perm = res.scalar_one_or_none()
            if not perm:
                perm = Permission(
                    permission_code=perm_code,
                    resource=res_name,
                    action=act_name,
                    description=desc
                )
                db.add(perm)
                await db.flush()
            perms_map[perm_code] = perm

        # Attach all permissions to admin_hq and appropriate permissions to technician/farmer
        admin_role = roles_map["admin_hq"]
        for perm in perms_map.values():
            link_res = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if not link_res.scalar_one_or_none():
                db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

        # Technician permissions
        tech_role = roles_map["technician"]
        for p_code in ["farm:read", "farm:verify", "harvest:read", "qc:approve"]:
            p = perms_map.get(p_code)
            if p:
                l_res = await db.execute(select(RolePermission).where(RolePermission.role_id == tech_role.id, RolePermission.permission_id == p.id))
                if not l_res.scalar_one_or_none():
                    db.add(RolePermission(role_id=tech_role.id, permission_id=p.id))

        # Farmer permissions
        farmer_role = roles_map["farmer"]
        for p_code in ["farm:read", "farm:create", "harvest:create", "harvest:read"]:
            p = perms_map.get(p_code)
            if p:
                l_res = await db.execute(select(RolePermission).where(RolePermission.role_id == farmer_role.id, RolePermission.permission_id == p.id))
                if not l_res.scalar_one_or_none():
                    db.add(RolePermission(role_id=farmer_role.id, permission_id=p.id))

        print("[SEED 2] Seeding Master Data (Crops, Varieties, Units, Activities)...")
        # 1. Crop: JACKFRUIT
        c_res = await db.execute(select(Crop).where(Crop.crop_code == "JACKFRUIT"))
        crop_jackfruit = c_res.scalar_one_or_none()
        if not crop_jackfruit:
            crop_jackfruit = Crop(
                crop_code="JACKFRUIT",
                scientific_name="Artocarpus heterophyllus",
                is_active=True
            )
            db.add(crop_jackfruit)
            await db.flush()
            db.add(CropTranslation(crop_id=crop_jackfruit.id, locale="vi", name="Cây Mít", description="Cây mít ăn quả nhiệt đới"))
            db.add(CropTranslation(crop_id=crop_jackfruit.id, locale="en", name="Jackfruit", description="Tropical jackfruit tree"))

            # Varieties
            v1 = CropVariety(crop_id=crop_jackfruit.id, variety_code="JACKFRUIT_THAI", standard_growth_days=120, optimal_brix_min=15.0, is_active=True)
            db.add(v1)
            await db.flush()
            db.add(CropVarietyTranslation(variety_id=v1.id, locale="vi", name="Mít Thái Changai", characteristics="Cơm vàng, dày, giòn ngọt, ráo nước, năng suất cao"))
            db.add(CropVarietyTranslation(variety_id=v1.id, locale="en", name="Thai Changai Jackfruit", characteristics="Thick yellow flesh, sweet, crisp, high commercial yield"))

            v2 = CropVariety(crop_id=crop_jackfruit.id, variety_code="JACKFRUIT_RED_INDONESIAN", standard_growth_days=130, optimal_brix_min=16.0, is_active=True)
            db.add(v2)
            await db.flush()
            db.add(CropVarietyTranslation(variety_id=v2.id, locale="vi", name="Mít Ruột Đỏ Indo", characteristics="Cơm đỏ cam, vị ngọt đậm, mùi thơm đặc trưng dầu chuối"))
            db.add(CropVarietyTranslation(variety_id=v2.id, locale="en", name="Indonesian Red Jackfruit", characteristics="Red-orange flesh, aromatic, deep sweetness"))

            v3 = CropVariety(crop_id=crop_jackfruit.id, variety_code="JACKFRUIT_SEEDLESS", standard_growth_days=125, optimal_brix_min=14.5, is_active=True)
            db.add(v3)
            await db.flush()
            db.add(CropVarietyTranslation(variety_id=v3.id, locale="vi", name="Mít Không Hạt Ba Láng", characteristics="Không hạt, ít xơ, cơm mềm ngọt thanh"))
            db.add(CropVarietyTranslation(variety_id=v3.id, locale="en", name="Seedless Jackfruit", characteristics="Seedless, low fiber, tender sweet flesh"))

            # Quality Grades
            g1 = QualityGrade(crop_id=crop_jackfruit.id, grade_code="GRADE_A_EXPORT", min_brix=15.0, min_weight_kg=9.0, max_weight_kg=15.0, allow_cosmetic_defects=False, is_export_eligible=True)
            db.add(g1)
            await db.flush()
            db.add(QualityGradeTranslation(grade_id=g1.id, locale="vi", name="Hạng A (Xuất khẩu)", description="Trái tròn đều, không sâu bệnh, brix >= 15, trọng lượng 9-15kg"))
            db.add(QualityGradeTranslation(grade_id=g1.id, locale="en", name="Grade A (Export)", description="Symmetrical shape, zero defects, brix >= 15, 9-15kg weight"))

            g2 = QualityGrade(crop_id=crop_jackfruit.id, grade_code="GRADE_B_DOMESTIC", min_brix=13.0, min_weight_kg=6.0, max_weight_kg=18.0, allow_cosmetic_defects=True, is_export_eligible=False)
            db.add(g2)
            await db.flush()
            db.add(QualityGradeTranslation(grade_id=g2.id, locale="vi", name="Hạng B (Nội địa)", description="Trái chất lượng tốt tiêu thụ siêu thị nội địa"))
            db.add(QualityGradeTranslation(grade_id=g2.id, locale="en", name="Grade B (Domestic)", description="Good quality fruit for domestic supermarket supply"))

        # 2. Units
        units_data = [
            ("KG", "MASS", True, 1.0, "Kilogram", "kg", "Kilogram", "kg"),
            ("TON", "MASS", False, 1000.0, "Tấn", "tấn", "Metric Ton", "ton"),
            ("HECTARE", "AREA", True, 1.0, "Héc-ta", "ha", "Hectare", "ha"),
            ("BRIX", "QUALITY", True, 1.0, "Độ Brix", "°Bx", "Brix Degree", "°Bx"),
            ("CARTON", "COUNT", False, 1.0, "Thùng carton", "thùng", "Carton Box", "ctn"),
        ]
        for u_code, u_type, is_base, conv, n_vi, s_vi, n_en, s_en in units_data:
            u_check = await db.execute(select(Unit).where(Unit.unit_code == u_code))
            if not u_check.scalar_one_or_none():
                unit = Unit(unit_code=u_code, unit_type=u_type, is_si_base=is_base, conversion_to_base=conv)
                db.add(unit)
                await db.flush()
                db.add(UnitTranslation(unit_id=unit.id, locale="vi", name=n_vi, symbol=s_vi))
                db.add(UnitTranslation(unit_id=unit.id, locale="en", name=n_en, symbol=s_en))

        print("[SEED 3] Seeding Primary Organizations...")
        # 1. Tam My HQ Cooperative
        res_org1 = await db.execute(select(Organization).where(Organization.org_code == "HTX_TAM_MY"))
        org_tam_my = res_org1.scalar_one_or_none()
        if not org_tam_my:
            org_tam_my = Organization(
                org_code="HTX_TAM_MY",
                org_name_vi="Hợp Tác Xã Nông Nghiệp Tam Mỹ",
                org_name_en="Tam My Agricultural Cooperative",
                org_type="COOPERATIVE",
                tax_id="4001234567",
                contact_email="contact@tammysmartfruit.vn",
                contact_phone="0901234567",
                headquarters_address="Xã Tam Mỹ, Núi Thành, Quảng Nam",
                is_active=True,
                is_verified=True
            )
            db.add(org_tam_my)
            await db.flush()

        res_org2 = await db.execute(select(Organization).where(Organization.org_code == "HTX_TIEN_PHUOC"))
        org_tien_phuoc = res_org2.scalar_one_or_none()
        if not org_tien_phuoc:
            org_tien_phuoc = Organization(
                org_code="HTX_TIEN_PHUOC",
                org_name_vi="Hợp Tác Xã Trái Cây Tiên Phước",
                org_name_en="Tien Phuoc Fruit Cooperative",
                org_type="COOPERATIVE",
                tax_id="4009876543",
                contact_email="contact@tienphuoc.vn",
                contact_phone="0909876543",
                headquarters_address="Tiên Phước, Quảng Nam",
                is_active=True,
                is_verified=True
            )
            db.add(org_tien_phuoc)
            await db.flush()

        print("[SEED 4] Seeding Test Users & Credentials...")
        # 1. Admin HQ User
        res_user1 = await db.execute(select(User).where(User.username == "admin_tammy"))
        admin_user = res_user1.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                username="admin_tammy",
                email="admin@tammysmartfruit.vn",
                phone_number="0900000001",
                full_name="Quản Trị Viên Tam Mỹ HQ",
                is_active=True
            )
            db.add(admin_user)
            await db.flush()
            db.add(UserCredential(user_id=admin_user.id, password_hash=hash_password_argon2("Admin@123456"), password_algo="ARGON2ID"))
            db.add(UserRole(user_id=admin_user.id, role_id=roles_map["admin_hq"].id))
            mem = UserOrganizationMembership(user_id=admin_user.id, organization_id=org_tam_my.id, is_primary_organization=True, membership_status="ACTIVE")
            db.add(mem)
            await db.flush()
            db.add(MembershipRole(membership_id=mem.id, role_id=roles_map["admin_hq"].id))
            db.add(DataScopeAssignment(membership_id=mem.id, scope_type="ALL"))

        # 2. Farmer User
        res_user2 = await db.execute(select(User).where(User.username == "farmer_ba_tam"))
        farmer_user = res_user2.scalar_one_or_none()
        if not farmer_user:
            farmer_user = User(
                username="farmer_ba_tam",
                email="farmer.batam@gmail.com",
                phone_number="0900000002",
                full_name="Nguyễn Văn Ba (Nông hộ)",
                is_active=True
            )
            db.add(farmer_user)
            await db.flush()
            db.add(UserCredential(user_id=farmer_user.id, password_hash=hash_password_argon2("Farmer@123456"), password_algo="ARGON2ID"))
            db.add(UserRole(user_id=farmer_user.id, role_id=roles_map["farmer"].id))
            mem = UserOrganizationMembership(user_id=farmer_user.id, organization_id=org_tam_my.id, is_primary_organization=True, membership_status="ACTIVE")
            db.add(mem)
            await db.flush()
            db.add(MembershipRole(membership_id=mem.id, role_id=roles_map["farmer"].id))
            db.add(DataScopeAssignment(membership_id=mem.id, scope_type="OWN"))

        # 3. Technician User
        res_user3 = await db.execute(select(User).where(User.username == "legacy_technician"))
        legacy_user = res_user3.scalar_one_or_none()
        if not legacy_user:
            legacy_user = User(
                username="legacy_technician",
                email="legacy.tech@tammysmartfruit.vn",
                phone_number="0900000003",
                full_name="Trần Kỹ Thuật (Kỹ thuật viên)",
                is_active=True
            )
            db.add(legacy_user)
            await db.flush()
            pbkdf2_hash = pbkdf2_sha256.hash("Legacy@123456")
            db.add(UserCredential(user_id=legacy_user.id, password_hash=pbkdf2_hash, password_algo="PBKDF2_LEGACY", rehash_required=True))
            db.add(UserRole(user_id=legacy_user.id, role_id=roles_map["technician"].id))
            mem = UserOrganizationMembership(user_id=legacy_user.id, organization_id=org_tam_my.id, is_primary_organization=True, membership_status="ACTIVE")
            db.add(mem)
            await db.flush()
            db.add(MembershipRole(membership_id=mem.id, role_id=roles_map["technician"].id))
            db.add(DataScopeAssignment(membership_id=mem.id, scope_type="COOPERATIVE"))

        # 4. Tien Phuoc User
        res_user4 = await db.execute(select(User).where(User.username == "user_tienphuoc"))
        tp_user = res_user4.scalar_one_or_none()
        if not tp_user:
            tp_user = User(
                username="user_tienphuoc",
                email="user@tienphuoc.vn",
                phone_number="0900000004",
                full_name="Lê Văn Tiên (HTX Tiên Phước)",
                is_active=True
            )
            db.add(tp_user)
            await db.flush()
            db.add(UserCredential(user_id=tp_user.id, password_hash=hash_password_argon2("TienPhuoc@123"), password_algo="ARGON2ID"))
            db.add(UserRole(user_id=tp_user.id, role_id=roles_map["farmer"].id))
            mem = UserOrganizationMembership(user_id=tp_user.id, organization_id=org_tien_phuoc.id, is_primary_organization=True, membership_status="ACTIVE")
            db.add(mem)
            await db.flush()
            db.add(MembershipRole(membership_id=mem.id, role_id=roles_map["farmer"].id))
            db.add(DataScopeAssignment(membership_id=mem.id, scope_type="OWN"))

        # 5. Packhouse Lead User
        res_user5 = await db.execute(select(User).where(User.username == "packhouse_tammy"))
        ph_user = res_user5.scalar_one_or_none()
        if not ph_user:
            ph_user = User(
                username="packhouse_tammy",
                email="packhouse@tammysmartfruit.vn",
                phone_number="0900000005",
                full_name="Phan Xưởng Trưởng (Sơ chế & Đóng gói)",
                is_active=True
            )
            db.add(ph_user)
            await db.flush()
            db.add(UserCredential(user_id=ph_user.id, password_hash=hash_password_argon2("Packhouse@123456"), password_algo="ARGON2ID"))
            db.add(UserRole(user_id=ph_user.id, role_id=roles_map["packhouse_lead"].id))
            mem = UserOrganizationMembership(user_id=ph_user.id, organization_id=org_tam_my.id, is_primary_organization=True, membership_status="ACTIVE")
            db.add(mem)
            await db.flush()
            db.add(MembershipRole(membership_id=mem.id, role_id=roles_map["packhouse_lead"].id))
            db.add(DataScopeAssignment(membership_id=mem.id, scope_type="ORGANIZATION"))

        print("[SEED 5] Seeding Growing Area, Farm, Plots & Spatial Polygons...")
        # Growing Area: PUC-VN-QNA-00891
        ga_res = await db.execute(select(GrowingArea).where(GrowingArea.area_code == "PUC-VN-QNA-00891"))
        growing_area = ga_res.scalar_one_or_none()
        if not growing_area:
            ga_poly = {
                "type": "Polygon",
                "coordinates": [[
                    [108.6200, 15.4200],
                    [108.6350, 15.4200],
                    [108.6350, 15.4350],
                    [108.6200, 15.4350],
                    [108.6200, 15.4200]
                ]]
            }
            ga_id = uuid.uuid4()
            growing_area = GrowingArea(
                id=ga_id,
                organization_id=org_tam_my.id,
                area_code="PUC-VN-QNA-00891",
                area_name="Vùng Trồng Mít Tam Mỹ Tây",
                puc_registration_code="PUC-VN-QNA-00891",
                puc_issued_at=date(2025, 1, 1),
                puc_expires_at=date(2028, 12, 31),
                puc_status="ACTIVE",
                province_code="49",
                district_code="502",
                commune_code="20725",
                total_area_hectares=25.50,
                boundary_polygon=ga_poly,
                created_by=admin_user.id
            )
            db.add(growing_area)
            await db.flush()

            # Farm: FARM-TAMMY-001
            farm = Farm(
                id=uuid.uuid4(),
                organization_id=org_tam_my.id,
                growing_area_id=ga_id,
                farm_code="FARM-TAMMY-001",
                farm_name="Nông Trại Mít Ba Tám - Tam Mỹ",
                owner_farmer_user_id=farmer_user.id,
                address_line="Thôn 3, Xã Tam Mỹ Tây, Huyện Núi Thành, Quảng Nam",
                total_plots_count=2,
                farm_area_hectares=4.50,
                is_active=True
            )
            db.add(farm)
            await db.flush()

            # Plot A: PLOT-TAMMY-001-A
            plot_a_poly = {
                "type": "Polygon",
                "coordinates": [[
                    [108.6210, 15.4210],
                    [108.6260, 15.4210],
                    [108.6260, 15.4260],
                    [108.6210, 15.4260],
                    [108.6210, 15.4210]
                ]]
            }
            plot_a_id = uuid.uuid4()
            plot = Plot(
                id=plot_a_id,
                farm_id=farm.id,
                plot_code="PLOT-TAMMY-001-A",
                plot_name="Thửa Mít Đồi A1",
                area_hectares=2.50,
                boundary_polygon=plot_a_poly,
                centroid_point={"type": "Point", "coordinates": [108.6235, 15.4235]},
                soil_type="BASALTIC",
                topography="SLIGHT_SLOPE",
                irrigation_system="DRIP_IRRIGATION",
                is_active=True
            )
            db.add(plot)
            await db.flush()

            # TreeGroup in Plot A
            v_thai = await db.execute(select(CropVariety).where(CropVariety.variety_code == "JACKFRUIT_THAI"))
            thai_variety = v_thai.scalar_one()

            tg = TreeGroup(
                plot_id=plot_a_id,
                group_code="TG-001-JACKFRUIT-THAI",
                crop_variety_id=thai_variety.id,
                planting_date=date(2022, 4, 15),
                tree_count=350,
                row_spacing_meters=6.0,
                tree_spacing_meters=5.0,
                estimated_annual_yield_kg=8500.0,
                health_status="HEALTHY",
                is_active=True
            )
            db.add(tg)

            # Sample Initial Claim: CROP_VARIETY = JACKFRUIT_THAI (LEVEL_0_DECLARED)
            claim = DataClaim(
                organization_id=org_tam_my.id,
                claim_type="CROP_VARIETY",
                subject_type="PLOT",
                subject_id=plot_a_id,
                value_code="JACKFRUIT_THAI",
                declared_by=farmer_user.id,
                source_type="FARMER_DECLARATION",
                assurance_level="LEVEL_0_DECLARED",
                verification_status="PENDING",
                risk_score=10.0,
                is_current=True
            )
            db.add(claim)
            await db.flush()

            db.add(ClaimStatusHistory(
                claim_id=claim.id,
                previous_status="NONE",
                new_status="PENDING",
                previous_assurance_level="NONE",
                new_assurance_level="LEVEL_0_DECLARED",
                transition_reason="Initial farmer declaration on planting",
                transitioned_by=farmer_user.id
            ))

        print("[SEED 6] Seeding Phase 6 Activity Types, Materials, Batches, Seasons & Farm Diary...")
        # 1. Activity Types
        act_types_data = [
            ("PLANTING", "Xuống giống / Trồng cây", "Planting / Seedling", False, True),
            ("WATERING", "Tưới nước nhỏ giọt", "Drip Irrigation", False, False),
            ("FERTILIZING", "Bón phân hữu cơ vi sinh", "Bio-Fertilization", True, True),
            ("PRUNING", "Tỉa cành tạo tán", "Canopy Pruning", False, True),
            ("BAGGING", "Bao trái ngừa sâu bệnh", "Fruit Bagging", False, True),
            ("PESTICIDE_SPRAY", "Phun thuốc trừ sâu sinh học", "Bio-Pesticide Spraying", True, True),
            ("HARVESTING", "Thu hoạch trái chín", "Fruit Harvesting", False, True),
        ]
        act_map = {}
        for code, vi_n, en_n, req_mat, req_gps in act_types_data:
            at_res = await db.execute(select(ActivityType).where(ActivityType.activity_code == code))
            at_obj = at_res.scalar_one_or_none()
            if not at_obj:
                at_obj = ActivityType(activity_code=code, requires_material=req_mat, requires_gps_photo=req_gps, is_active=True)
                db.add(at_obj)
                await db.flush()
                db.add(ActivityTypeTranslation(activity_type_id=at_obj.id, locale="vi", name=vi_n, instructions="Thực hiện theo quy chuẩn VietGAP Tam Mỹ"))
                db.add(ActivityTypeTranslation(activity_type_id=at_obj.id, locale="en", name=en_n, instructions="Perform under Tam My VietGAP standards"))
            act_map[code] = at_obj

        # 2. Material Types
        mat_types_data = [
            ("BIO_FERTILIZER", False, True),
            ("CHEMICAL_FERTILIZER", False, False),
            ("BIO_PESTICIDE", False, True),
            ("GROWTH_REGULATOR", False, False),
        ]
        mat_type_map = {}
        for mt_code, is_quar, is_org in mat_types_data:
            mt_res = await db.execute(select(MaterialType).where(MaterialType.type_code == mt_code))
            mt_obj = mt_res.scalar_one_or_none()
            if not mt_obj:
                mt_obj = MaterialType(type_code=mt_code, is_quarantine_restricted=is_quar, is_organic_allowed=is_org, is_active=True)
                db.add(mt_obj)
                await db.flush()
            mat_type_map[mt_code] = mt_obj

        # 3. Units map
        kg_unit = (await db.execute(select(Unit).where(Unit.unit_code == "KG"))).scalar_one()
        
        # 4. Materials
        materials_data = [
            ("MAT-NPK-BIO-01", "BIO_FERTILIZER", "Phân Hữu Cơ Vi Sinh Tam Mỹ Gold", "Công ty CP Nông Nghiệp Tam Mỹ", "Hữu cơ 65%, Vi sinh Trichoderma, Axit Humic", "65%", 0, "500kg/ha", True),
            ("MAT-NEEM-OIL-02", "BIO_PESTICIDE", "Dầu Neem Trừ Sâu Sinh Học Azadirachtin", "BioTech Vietnam", "Azadirachtin A/B", "0.3%", 3, "2.5 lít/ha", True),
            ("MAT-TRICHO-03", "BIO_PESTICIDE", "Nấm Đối Kháng Trichoderma Hazianum", "Viện BVTV Quốc Gia", "Trichoderma spp. 10^9 CFU/g", "10^9 CFU", 0, "1.5 kg/ha", True),
            ("MAT-K-ORGANIC-04", "BIO_FERTILIZER", "Phân Bón Lá Kali Hữu Cơ Ngọt Trái", "AgriGlobal Labs", "K2O hữu cơ từ tro vỏ dừa", "30%", 5, "3 lít/ha", True),
        ]
        mat_map = {}
        for m_code, mt_code, b_name, manuf, act_ing, act_conc, phi, dosage, is_org in materials_data:
            m_res = await db.execute(select(Material).where(Material.material_code == m_code))
            m_obj = m_res.scalar_one_or_none()
            if not m_obj:
                m_obj = Material(
                    organization_id=org_tam_my.id,
                    material_type_id=mat_type_map[mt_code].id,
                    material_code=m_code,
                    brand_name=b_name,
                    manufacturer=manuf,
                    active_ingredient=act_ing,
                    active_ingredient_concentration=act_conc,
                    pre_harvest_interval_days=phi,
                    standard_dosage_per_ha=dosage,
                    is_organic_certified=is_org,
                    is_active=True
                )
                db.add(m_obj)
                await db.flush()

                # Seed initial Batch
                batch = MaterialBatch(
                    material_id=m_obj.id,
                    batch_number=f"LOT-2026-{m_code[-4:]}-01",
                    manufacturing_date=date(2026, 1, 15),
                    expiration_date=date(2027, 12, 31),
                    initial_quantity=1000.0,
                    remaining_quantity=950.0,
                    unit_id=kg_unit.id,
                    storage_location="Kho Vật Tư Tam Mỹ - Ngăn A1"
                )
                db.add(batch)
            mat_map[m_code] = m_obj

        # 5. Crop Seasons: Active Season for Plot A
        plot_res = await db.execute(select(Plot).where(Plot.plot_code == "PLOT-TAMMY-001-A"))
        plot_a = plot_res.scalar_one()

        sea_res = await db.execute(select(CropSeason).where(CropSeason.season_code == "SEA-2026-PLOT01-M01"))
        season_a = sea_res.scalar_one_or_none()
        if not season_a:
            season_a = CropSeason(
                id=uuid.uuid4(),
                plot_id=plot_a.id,
                season_code="SEA-2026-PLOT01-M01",
                season_name="Vụ Mít Thái Changai Mùa Thuận 2026",
                start_date=date(2026, 5, 1),
                expected_harvest_start=date(2026, 9, 15),
                expected_harvest_end=date(2026, 10, 31),
                forecasted_yield_kg=8500.0,
                actual_harvested_yield_kg=0.0,
                season_status="ACTIVE"
            )
            db.add(season_a)
            await db.flush()

            # Seed Yield Estimate
            ye = YieldEstimate(
                season_id=season_a.id,
                estimation_method="TREE_COUNT_SAMPLING",
                estimated_yield_kg=8500.0,
                confidence_level_pct=92.5,
                estimated_by=legacy_user.id,
                notes="Khảo sát 350 cây mít Thái 4 năm tuổi, trung bình 24-28kg/cây"
            )
            db.add(ye)

            # Seed 2 Sample Farm Activities
            act1 = FarmActivity(
                season_id=season_a.id,
                activity_type_id=act_map["FERTILIZING"].id,
                activity_code="ACT-2026-000101",
                performed_by_user_id=farmer_user.id,
                performed_at=datetime(2026, 6, 10, 8, 30, tzinfo=timezone.utc),
                gps_point={"type": "Point", "coordinates": [108.6235, 15.4235]},
                gps_accuracy_meters=4.2,
                is_geofence_verified=True,
                duration_hours=3.5,
                weather_condition="SUNNY",
                notes="Bón lót phân hữu cơ vi sinh Tam Mỹ Gold đợt 1 sau tỉa trái"
            )
            db.add(act1)
            await db.flush()

            # Material Usage for act1
            b_res = await db.execute(select(MaterialBatch).where(MaterialBatch.material_id == mat_map["MAT-NPK-BIO-01"].id))
            b_npk = b_res.scalar_one()
            u1 = MaterialUsage(
                activity_id=act1.id,
                material_batch_id=b_npk.id,
                quantity_applied=50.0,
                unit_id=kg_unit.id,
                phi_days_applied=0,
                earliest_safe_harvest_date=date(2026, 6, 10),
                application_method="ROOT_FERTILIZE"
            )
            db.add(u1)

            # Verified Claim for act1
            c_act1 = DataClaim(
                organization_id=org_tam_my.id,
                claim_type="FARM_ACTIVITY",
                subject_type="PLOT",
                subject_id=plot_a.id,
                value_code="FERTILIZING",
                value_json={"activity_id": str(act1.id), "activity_code": act1.activity_code},
                declared_by=farmer_user.id,
                source_type="FARMER_DECLARATION",
                assurance_level="LEVEL_2_ORGANIZATION_VERIFIED",
                verification_status="VERIFIED",
                verified_by=legacy_user.id,
                verified_at=datetime(2026, 6, 11, 9, 0, tzinfo=timezone.utc),
                verification_method="ON_SITE_PHYSICAL_INSPECTION",
                risk_score=0.0,
                is_current=True
            )
            db.add(c_act1)

            # Activity 2: Neem oil spraying
            act2 = FarmActivity(
                season_id=season_a.id,
                activity_type_id=act_map["PESTICIDE_SPRAY"].id,
                activity_code="ACT-2026-000102",
                performed_by_user_id=farmer_user.id,
                performed_at=datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc),
                gps_point={"type": "Point", "coordinates": [108.6235, 15.4235]},
                gps_accuracy_meters=3.8,
                is_geofence_verified=True,
                duration_hours=2.0,
                weather_condition="CLOUDY",
                notes="Phun phòng trừ rệp sáp và sâu đục trái bằng dầu neem sinh học"
            )
            db.add(act2)
            await db.flush()

            b_neem_res = await db.execute(select(MaterialBatch).where(MaterialBatch.material_id == mat_map["MAT-NEEM-OIL-02"].id))
            b_neem = b_neem_res.scalar_one()
            u2 = MaterialUsage(
                activity_id=act2.id,
                material_batch_id=b_neem.id,
                quantity_applied=5.0,
                unit_id=kg_unit.id,
                phi_days_applied=3,
                earliest_safe_harvest_date=date(2026, 8, 23),
                application_method="FOLIAR_SPRAY"
            )
            db.add(u2)

            c_act2 = DataClaim(
                organization_id=org_tam_my.id,
                claim_type="FARM_ACTIVITY",
                subject_type="PLOT",
                subject_id=plot_a.id,
                value_code="PESTICIDE_SPRAY",
                value_json={"activity_id": str(act2.id), "activity_code": act2.activity_code},
                declared_by=farmer_user.id,
                source_type="FARMER_DECLARATION",
                assurance_level="LEVEL_1_SYSTEM_VALIDATED",
                verification_status="PENDING",
                risk_score=5.0,
                is_current=True
            )
            db.add(c_act2)

        await db.commit()
        print("[SUCCESS] All Phase 6 Master Data, Materials, Seasons, and Farm Activities seeded successfully!")

seed_all = seed_database

if __name__ == "__main__":
    asyncio.run(seed_database())

