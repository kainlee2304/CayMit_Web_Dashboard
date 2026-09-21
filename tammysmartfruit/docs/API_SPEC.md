# API SPECIFICATION - TAMMYSMARTFRUIT (PRODUCTION REST API v1)

> **STATUS:** PRODUCTION ACTIVE (Phase 4 Foundation + Phase 5 Agricultural Core)  
> **Base URL:** `http://localhost:8000/api/v1`  
> **Security:** JWT RS256 Bearer Token (`Authorization: Bearer <token>`) with RBAC & DataScope Multi-Tenant Filtering.

---

## 1. Master Data Endpoints (`/api/v1/master-data`)

- `GET /api/v1/master-data/crops`: Danh sách cây trồng (hỗ trợ `lang=vi|en`).
- `GET /api/v1/master-data/crops/{crop_code}`: Chi tiết cây trồng và danh mục giống trực thuộc.
- `GET /api/v1/master-data/varieties`: Danh sách giống mít chính thống (`JACKFRUIT_THAI`, `JACKFRUIT_RED_INDONESIAN`, `JACKFRUIT_MALAYSIAN`, `JACKFRUIT_SEEDLESS`, `JACKFRUIT_TURMERIC`).
- `GET /api/v1/master-data/units`: Danh mục đơn vị tính chuẩn nông nghiệp (KG, TON, TREE, HECTARE, LITER, PACK, BOX).
- `GET /api/v1/master-data/grades`: Tiêu chuẩn phẩm cấp trái mít (GRADE_SPECIAL, GRADE_A, GRADE_B, GRADE_C, INDUSTRIAL).
- `GET /api/v1/master-data/activity-types`: Danh mục hoạt động nhật ký canh tác chuẩn.
- `GET /api/v1/master-data/markets`: Mã thị trường xuất khẩu và nội địa (VN, CN, US, EU, JP, KR, GLOBAL).

---

## 2. Farmer Management Endpoints (`/api/v1/farmers`)

- `GET /api/v1/farmers`: Danh sách nông hộ thuộc phạm vi DataScope (`OWN`, `ORGANIZATION`, `ALL`).
- `GET /api/v1/farmers/{farmer_id}`: Chi tiết hồ sơ nông hộ, liên kết nông trại và mã số định danh.
- `POST /api/v1/farmers`: Tạo tài khoản và hồ sơ nông hộ mới (Tự động băm mật khẩu Argon2id, gán vai trò `FARMER` và DataScope `OWN`).

---

## 3. Growing Area (PUC) Endpoints (`/api/v1/growing-areas`)

- `GET /api/v1/growing-areas`: Danh sách vùng trồng xuất khẩu PUC được cấp phép.
- `GET /api/v1/growing-areas/{area_id}`: Chi tiết vùng trồng bao gồm đa giác không gian PostGIS SRID 4326.
- `POST /api/v1/growing-areas`: Đăng ký vùng trồng mới kèm đa giác GeoJSON `Polygon`/`MultiPolygon` (Tự động tính diện tích Geodesic `ST_Area` qua PostGIS).
- `PATCH /api/v1/growing-areas/{area_id}/status`: Chuyển đổi vòng đời trạng thái (`ACTIVE`, `SUSPENDED`, `REVOKED`).

---

## 4. Farm & Cadastral Plot Endpoints (`/api/v1/farms`, `/api/v1/plots`)

- `GET /api/v1/farms`: Danh sách nông trại thành viên hợp tác xã.
- `GET /api/v1/farms/{farm_id}`: Chi tiết nông trại và danh mục thửa đất trực thuộc.
- `POST /api/v1/farms`: Đăng ký nông trại thành viên liên kết chủ hộ và vùng trồng PUC.
- `GET /api/v1/plots`: Danh sách thửa đất (Hỗ trợ lọc theo `farm_id`).
- `GET /api/v1/plots/{plot_id}`: Chi tiết thửa đất, đặc tính thổ nhưỡng, hệ thống tưới, lô cây và tuyên bố giống hiện tại.
- `POST /api/v1/plots`: Đăng ký thửa đất mới kèm đa giác PostGIS `boundary_polygon` (Validate `ST_IsValid`, tự tính diện tích ha `geodesic_area_hectares`).
- `POST /api/v1/plots/spatial/viewport`: Truy vấn không gian các thửa đất nằm trong khung nhìn bản đồ Bounding Box (`ST_Intersects`).

---

## 5. Data Claims & Trust Verification Pipeline (`/api/v1/claims`)

- `GET /api/v1/claims`: Tra cứu danh sách tuyên bố dữ liệu theo `subject_id`, `claim_type`, `is_current`.
- `GET /api/v1/claims/{claim_id}`: Chi tiết tuyên bố dữ liệu kèm bằng chứng Geotagged GPS và lịch sử chuyển đổi trạng thái bất biến.
- `POST /api/v1/claims`:
  - **Mục đích:** Nông hộ khai báo giống cây trồng.
  - **Bảo mật & Tính toàn vẹn:**
    - Kiểm tra tính hợp lệ của mã giống trong Master Data (Không dùng Free-Text).
    - Khởi tạo bảo chứng ở mức `LEVEL_0_DECLARED` (Trạng thái `PENDING`).
    - Ghi nhận bằng chứng Geotagged GPS + Mã băm SHA-256 vào `evidence_records`.
    - Chặn ghi đè trực tiếp nếu thửa đất đã có xác thực cấp độ 2 (`409 CANNOT_OVERWRITE_VERIFIED_CLAIM`).
- `POST /api/v1/claims/{claim_id}/verify`:
  - **Mục đích:** Kỹ thuật viên thẩm định thực địa và cấp chứng nhận.
  - **Bảo mật & Tính toàn vẹn:**
    - Thực thi nguyên tắc 4 mắt (Four-Eyes): Nông hộ không được tự duyệt lời khai của mình (`403 CANNOT_SELF_VERIFY`).
    - Nâng cấp bảo chứng lên `LEVEL_2_ORGANIZATION_VERIFIED` (Trạng thái `VERIFIED`).
    - Ghi nhận nhật ký trạng thái `claim_status_history` bất biến.

---

## 6. Global Multi-Entity Search (`/api/v1/search`)

- `GET /api/v1/search?q={query}`:
  - Tìm kiếm đồng thời trên 4 thực thể nông nghiệp: Nông hộ (Farmers), Vùng trồng (Growing Areas), Nông trại (Farms), Thửa đất (Plots).
  - Tự động áp dụng bộ lọc đa người thuê DataScope bảo vệ an toàn dữ liệu.
