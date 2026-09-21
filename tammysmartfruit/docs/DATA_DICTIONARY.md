# DATA DICTIONARY SPECIFICATION — TAM MỸ SMART FRUIT ECOSYSTEM
## COMPLETE TABLES, ATTRIBUTES, CONSTRAINTS & DATA TYPES

> **Từ Điển Dữ Liệu Chi Tiết (Data Dictionary)**  
> **Phiên bản:** 3.0.0-PROD  
> **Nền tảng:** PostgreSQL 16 + PostGIS + TimescaleDB  

---

## 1. NHÓM MIỀN I: NỀN TẢNG, DANH TÍNH & DỮ LIỆU CHỦ

### 1.1. `users` (IdentityModule - Aggregate Root)
| Tên Cột (Column Name) | Kiểu Dữ Liệu | Ràng Buộc (Constraints) | Mô Tả Nghiệp Vụ & Ràng Buộc |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh toàn cục người dùng (UUIDv7). |
| `username` | `VARCHAR(60)` | `UNIQUE, NOT NULL` | Tên tài khoản đăng nhập duy nhất. |
| `email` | `VARCHAR(120)` | `UNIQUE, NULLABLE` | Email liên hệ và nhận thông báo. |
| `phone_number` | `VARCHAR(20)` | `UNIQUE, NULLABLE` | Số điện thoại di động xác thực OTP. |
| `full_name` | `VARCHAR(120)` | `NOT NULL` | Họ và tên đầy đủ của người dùng. |
| `avatar_storage_key`| `VARCHAR(255)` | `NULLABLE` | Khóa đối tượng ảnh đại diện trên S3/MinIO. |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE, NOT NULL` | Trạng thái tài khoản hoạt động. |
| `is_verified` | `BOOLEAN` | `DEFAULT FALSE, NOT NULL`| Đã xác thực CCCD/SĐT chính chủ. |
| `is_suspended` | `BOOLEAN` | `DEFAULT FALSE, NOT NULL`| Trạng thái tạm khóa tài khoản do vi phạm. |
| `suspension_reason` | `TEXT` | `NULLABLE` | Lý do tạm khóa tài khoản. |
| `preferred_locale` | `VARCHAR(10)` | `DEFAULT 'vi', NOT NULL` | Ngôn ngữ ưu tiên (`vi`, `en`). |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Thời điểm tạo tài khoản (UTC). |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Thời điểm cập nhật cuối cùng (UTC). |

### 1.2. `user_credentials` (IdentityModule)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh bản ghi chứng thực. |
| `user_id` | `UUID` | `UNIQUE, NOT NULL, FK users(id) ON DELETE CASCADE` | Tham chiếu người dùng sở hữu. |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Chuỗi băm mật khẩu (Argon2id hoặc PBKDF2). |
| `password_algo` | `VARCHAR(30)` | `DEFAULT 'ARGON2ID', NOT NULL` | Thuật toán băm (`ARGON2ID`, `PBKDF2_LEGACY`). |
| `argon2_memory_kb` | `INT` | `DEFAULT 65536` | Bộ nhớ RAM sử dụng băm Argon2id (64MB). |
| `argon2_iterations`| `INT` | `DEFAULT 3` | Số vòng lặp băm Argon2id. |
| `argon2_parallelism`| `INT`| `DEFAULT 4` | Số luồng tính toán song song. |
| `rehash_required` | `BOOLEAN` | `DEFAULT FALSE, NOT NULL` | Đánh dấu cần băm lại khi đăng nhập. |
| `failed_login_attempts`| `INT` | `DEFAULT 0, NOT NULL` | Số lần đăng nhập sai liên tiếp. |
| `locked_until` | `TIMESTAMPTZ` | `NULLABLE` | Thời điểm mở khóa tài khoản tự động. |

### 1.3. `organizations` (OrganizationModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh tổ chức (UUIDv7). |
| `org_code` | `VARCHAR(40)` | `UNIQUE, NOT NULL` | Mã viết tắt chuẩn (`TAMMY_HQ`, `HTX_TAM_MY`). |
| `org_name_vi` | `VARCHAR(150)` | `NOT NULL` | Tên tiếng Việt của tổ chức/hợp tác xã. |
| `org_name_en` | `VARCHAR(150)` | `NOT NULL` | Tên tiếng Anh của tổ chức. |
| `org_type` | `VARCHAR(40)` | `NOT NULL` | Loại hình tổ chức (`ECOSYSTEM_HQ`, `COOPERATIVE`, v.v.). |
| `tax_id` | `VARCHAR(30)` | `UNIQUE, NULLABLE` | Mã số thuế doanh nghiệp / HTX. |
| `parent_org_id` | `UUID` | `NULLABLE, FK organizations(id)` | Tổ chức cấp trên (nếu là chi nhánh/HTX thành viên). |

### 1.4. `crop_varieties` & `crop_variety_translations` (MasterDataModule)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh giống cây trồng. |
| `crop_id` | `UUID` | `NOT NULL, FK crops(id)` | Tham chiếu loài cây chủ (`JACKFRUIT`). |
| `variety_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã chuẩn (`JACKFRUIT_THAI`, `JACKFRUIT_RED_INDONESIAN`). |
| `standard_growth_days` | `INT` | `NULLABLE` | Số ngày sinh trưởng tiêu chuẩn từ khi bao trái. |
| `optimal_brix_min` | `NUMERIC(4,1)` | `DEFAULT 14.0` | Độ ngọt Brix tối thiểu đạt chuẩn thu hoạch. |

---

## 2. NHÓM MIỀN II: VÙNG TRỒNG, NÔNG HỘ & CANH TÁC

### 2.1. `growing_areas` (GrowingAreaModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh vùng trồng. |
| `organization_id` | `UUID` | `NOT NULL, FK organizations(id)` | Hợp tác xã / Doanh nghiệp quản lý vùng. |
| `area_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã định danh nội bộ vùng trồng. |
| `puc_registration_code`| `VARCHAR(60)` | `UNIQUE, NOT NULL` | Mã số vùng trồng chính thức do Cục BVTV cấp. |
| `boundary_polygon`| `GEOMETRY(Polygon, 4326)` | `NOT NULL` | Đa giác ranh giới địa lý không gian PostGIS. |
| `centroid_point` | `GEOMETRY(Point, 4326)` | `NULLABLE` | Tọa độ tâm vùng trồng phục vụ hiển thị bản đồ. |

### 2.2. `plots` (PlotModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh thửa đất. |
| `farm_id` | `UUID` | `NOT NULL, FK farms(id)` | Nông trại sở hữu thửa đất. |
| `plot_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã số thửa vườn (`PLOT-TAMMY-001-A`). |
| `area_hectares` | `NUMERIC(6,2)` | `NOT NULL` | Diện tích canh tác thực tế (hecta). |
| `boundary_polygon`| `GEOMETRY(Polygon, 4326)` | `NOT NULL` | Ranh giới đa giác không gian của thửa đất. |

### 2.3. `farm_activities` (ActivityModule - Farm Diary)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh hoạt động nhật ký. |
| `season_id` | `UUID` | `NOT NULL, FK crop_seasons(id)` | Mùa vụ canh tác liên kết. |
| `activity_type_id`| `UUID` | `NOT NULL, FK activity_types(id)` | Loại hoạt động (Tưới, Bón phân, Xịt thuốc). |
| `activity_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã số phiếu nhật ký (`ACT-2026-000451`). |
| `performed_by_user_id`| `UUID` | `NOT NULL, FK users(id)` | Nông dân / Công nhân thực hiện. |
| `performed_at` | `TIMESTAMPTZ` | `NOT NULL` | Thời điểm thực hiện ngoài thực địa (UTC). |
| `gps_point` | `GEOMETRY(Point, 4326)` | `NULLABLE` | Tọa độ GPS ghi nhận từ điện thoại. |
| `is_geofence_verified`| `BOOLEAN` | `DEFAULT FALSE, NOT NULL` | Đã kiểm tra điểm GPS nằm trong thửa đất (`ST_Contains`). |

---

## 3. NHÓM MIỀN III: CHUỖI CUNG ỨNG & THƯƠNG MẠI

### 3.1. `harvest_batches` (HarvestModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh lô thu hoạch. |
| `season_id` | `UUID` | `NOT NULL, FK crop_seasons(id)` | Mùa vụ thu hoạch (Thừa kế 100% giống, vùng trồng). |
| `harvest_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã lô thu hoạch tự động sinh (`HAR-2026-000125`). |
| `total_fruit_count`| `INT` | `NOT NULL, CHECK (> 0)` | Tổng số lượng quả thu hoạch. |
| `total_net_weight_kg`| `NUMERIC(10,2)`| `NOT NULL, CHECK (> 0)` | Tổng khối lượng tịnh cân thực tế (kg). |
| `harvest_status` | `VARCHAR(30)` | `DEFAULT 'DRAFT', NOT NULL` | Trạng thái (`DRAFT`, `SUBMITTED`, `ACCEPTED`, `REJECTED`). |
| `phi_compliance_status`| `VARCHAR(30)`| `DEFAULT 'VERIFIED_SAFE'` | Trạng thái an toàn cách ly thuốc BVTV (PHI). |
| `is_locked` | `BOOLEAN` | `DEFAULT FALSE, NOT NULL` | Đã khóa dữ liệu sau khi được duyệt 4 mắt. |

### 3.2. `processing_batches` (ProcessingModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh lô sơ chế. |
| `processing_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã lô sơ chế (`PRO-2026-000412`). |
| `mass_balance_policy_id`| `UUID` | `NOT NULL, FK mass_balance_policies`| Chính sách dung sai cân bằng khối lượng áp dụng. |
| `total_input_weight_kg` | `NUMERIC(10,2)`| `NOT NULL, CHECK (> 0)` | Tổng khối lượng nguyên liệu đầu vào (kg). |
| `total_output_weight_kg`| `NUMERIC(10,2)`| `DEFAULT 0.00, NOT NULL` | Tổng khối lượng thành phẩm xuất xưởng (kg). |
| `total_documented_loss_kg`| `NUMERIC(10,2)`| `DEFAULT 0.00, NOT NULL` | Tổng hao hụt có lý do (vỏ, cùi, bốc hơi) (kg). |
| `total_reject_weight_kg` | `NUMERIC(10,2)`| `DEFAULT 0.00, NOT NULL` | Tổng phế phẩm loại bỏ (kg). |
| `mass_balance_status` | `VARCHAR(30)` | `DEFAULT 'IN_PROGRESS'` | Trạng thái cân bằng (`BALANCED_PASSED`, `IMBALANCE_VIOLATION`). |

### 3.3. `pallets` & `cartons` (PackingModule)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh Pallet đóng gói. |
| `pallet_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Mã Pallet nội bộ (`PAL-2026-000104`). |
| `sscc_18_code` | `VARCHAR(20)` | `UNIQUE, NOT NULL` | Mã chuẩn vận tải quốc tế GS1 SSCC-18 (18 chữ số). |
| `total_cartons_count`| `INT` | `DEFAULT 0, NOT NULL` | Số lượng thùng carton xếp trên Pallet. |
| `total_net_weight_kg`| `NUMERIC(10,2)`| `NOT NULL` | Khối lượng tịnh toàn bộ Pallet (kg). |
| `pallet_qc_status` | `VARCHAR(30)` | `DEFAULT 'PENDING_QC'` | Trạng thái kiểm định (`QC_PASSED`, `REJECTED`). |
| `pallet_inventory_status`| `VARCHAR(30)`| `DEFAULT 'IN_PACKHOUSE'`| Trạng thái kho (`AVAILABLE`, `RESERVED`, `DISPATCHED`). |

---

## 4. NHÓM MIỀN IV: ĐỘ TIN CẬY DỮ LIỆU, SỔ CÁI & TRUY XUẤT NGUỒN GỐC

### 4.1. `data_claims` (ClaimModule - Aggregate Root)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Mã định danh khẳng định dữ liệu. |
| `claim_type` | `VARCHAR(80)` | `NOT NULL` | Loại khẳng định (`CROP_VARIETY`, `AREA_PUC`, `PHI_SAFE`, `QUALITY_GRADE`). |
| `subject_type` | `VARCHAR(60)` | `NOT NULL` | Đối tượng khẳng định (`PLOT`, `HARVEST_BATCH`, `PALLET`). |
| `subject_id` | `UUID` | `NOT NULL` | Khóa chính của đối tượng nghiệp vụ được khẳng định. |
| `value_code` | `VARCHAR(80)` | `NOT NULL` | Giá trị mã khẳng định (`JACKFRUIT_THAI`, `GRADE_A`). |
| `assurance_level` | `VARCHAR(40)` | `DEFAULT 'LEVEL_0_DECLARED'` | Cấp độ tin cậy (`LEVEL_0` đến `LEVEL_3`). |
| `verification_status`| `VARCHAR(40)` | `DEFAULT 'PENDING'` | Trạng thái thẩm định (`PENDING`, `VERIFIED`, `SUPERSEDED`). |
| `verified_by` | `UUID` | `NULLABLE, FK users(id)` | Chuyên viên / Thanh tra viên ký xác thực. |
| `is_current` | `BOOLEAN` | `DEFAULT TRUE, NOT NULL` | Khẳng định đang có hiệu lực hay đã bị thay thế. |
| `superseded_by_claim_id`| `UUID` | `NULLABLE, FK data_claims(id)`| Liên kết bản ghi đính chính thay thế (Never Overwrite). |

### 4.2. `domain_event_history` (Durable Event Journal - Immutable Source of Truth)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PK, DEFAULT generate_uuid_v7()` | Khóa tự tăng thời gian UUIDv7. |
| `event_id` | `UUID` | `UNIQUE, NOT NULL` | Mã định danh duy nhất của sự kiện (Idempotency Key). |
| `event_type` | `VARCHAR(120)` | `NOT NULL` | Tên sự kiện (`HarvestBatchAcceptedEvent`, `ProcessingCompletedEvent`). |
| `event_version` | `VARCHAR(20)` | `NOT NULL` | Phiên bản schema sự kiện (`1.0.0`). |
| `aggregate_type` | `VARCHAR(80)` | `NOT NULL` | Tên Aggregate Root phát sinh sự kiện (`HarvestBatch`). |
| `aggregate_id` | `UUID` | `NOT NULL` | Khóa chính của Aggregate Root. |
| `payload` | `JSONB` | `NOT NULL` | Toàn bộ dữ liệu chi tiết sự kiện dạng JSON chuẩn hóa. |
| `payload_hash` | `CHAR(64)` | `NOT NULL` | Mã băm SHA-256 của payload Canonical JSON. |
| `occurred_at` | `TIMESTAMPTZ` | `NOT NULL` | Thời điểm sự kiện thực sự xảy ra (UTC). |

### 4.3. `trace_nodes` & `trace_edges` (TraceabilityModule - DAG Read Projection)
| Bảng | Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả Nghiệp Vụ |
| :--- | :--- | :--- | :--- | :--- |
| `trace_nodes` | `id` | `UUID` | `PK` | Mã nút đồ thị truy xuất. |
| | `node_type` | `VARCHAR(60)` | `NOT NULL` | Loại nút (`PLOT`, `HARVEST_BATCH`, `PALLET`, `SHIPMENT`). |
| | `node_code` | `VARCHAR(80)` | `UNIQUE, NOT NULL` | Mã nghiệp vụ hiển thị (`HAR-2026-000125`). |
| | `data_hash` | `CHAR(64)` | `NOT NULL` | Mã băm toàn vẹn trạng thái nút. |
| `trace_edges` | `id` | `UUID` | `PK` | Mã cạnh đồ thị định hướng. |
| | `source_node_id` | `UUID` | `NOT NULL, FK trace_nodes` | Nút thượng nguồn (Cha). |
| | `target_node_id` | `UUID` | `NOT NULL, FK trace_nodes` | Nút hạ nguồn (Con). |
| | `relationship_type`| `VARCHAR(60)` | `NOT NULL` | Quan hệ (`HARVESTED_FROM`, `PROCESSED_INTO`, `PACKED_INTO`). |
| | `contribution_ratio`| `NUMERIC(6,4)` | `NOT NULL, CHECK (0.0001 -> 1.0000)`| Tỷ lệ khối lượng đóng góp chính xác vào nút con. |
