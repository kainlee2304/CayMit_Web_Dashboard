# PHASE 1 CLOSURE & DOCUMENT CONSISTENCY REPORT
## TAM MỸ SMART FRUIT ECOSYSTEM

> **Báo cáo Thẩm định & Khóa Miền Nghiệp vụ Phase 1 (Phase 1 Closure Report)**  
> **Ngày thực hiện:** 28/08/2026  
> **Trạng thái:** ✅ **PHASE 1: APPROVED FOR PHASE 2**  
> **Nguyên tắc:** DỪNG TOÀN BỘ HOẠT ĐỘNG CODING — Chờ xem xét và phê duyệt trước khi chuyển sang Phase 2.

---

## 1. BẢNG ĐÁNH GIÁ TIÊU CHÍ KẾT THÚC PHASE 1 (EXIT CRITERIA EVALUATION)

| STT | Tiêu chí Nghiệp vụ / Kiến trúc (Exit Criterion) | Kết quả | Chi tiết Đánh giá & Bằng chứng |
| :---: | :--- | :---: | :--- |
| 1 | **Domain Boundaries Nhất Quán** | **PASS** | Phân định rõ 13 Bounded Contexts không chồng chéo (Identity, Farm GIS, Agronomy, IoT, AI, Harvest, Processing, Packing, Cold Chain, Logistics, Export, Data Trust, Immutable Audit). |
| 2 | **Canonical Role Codes Nhất Quán** | **PASS** | Chuẩn hóa 11 mã vai trò duy nhất (`admin_hq`, `technician`, `farmer`, `packhouse_lead`, `qa_qc`, `warehouse_keeper`, `logistics_driver`, `export_officer`, `auditor_inspector`, `buyer_partner`, `system_worker`). Không dùng text hiển thị làm ID. |
| 3 | **State Machines Nhất Quán** | **PASS** | Khóa máy trạng thái cho Season, Harvest, Processing, Packing, Shipment, Export, Certificate, User. Cấm người dùng đổi status tùy tiện bằng dropdown. |
| 4 | **Mass Balance Invariant Đã Chuẩn Hóa** | **PASS** | Áp dụng công thức bảo toàn 2 chiều có dung sai cấu hình $\left\| \text{Input} - (\text{Output} + \text{Loss} + \text{Reject}) \right\| \le \text{Input} \times \text{Tolerance}$. |
| 5 | **Data Trust Invariants Rõ Ràng** | **PASS** | Phân định 4 cấp độ tin cậy (`Level 0-3`), thiết kế Claim Model, Bằng chứng đa nguồn và kiểm tra chéo Geofence GPS. |
| 6 | **Traceability DAG Rõ Ràng** | **PASS** | Cấu trúc dữ liệu Đồ thị có hướng không chu trình (DAG), hỗ trợ cả Backward Trace (truy ngược) và Forward Trace (truy xuôi). |
| 7 | **Split / Merge Lineage Rõ Ràng** | **PASS** | Mô hình quan hệ Nhiều-Nhiều (`ProcessingInput` / `ProcessingOutput`) bảo toàn tỷ lệ đóng góp khối lượng khi gộp nhiều lô thu hoạch hoặc tách phẩm cấp Grade A/B/C. |
| 8 | **RBAC + Data Scope Rõ Ràng** | **PASS** | Phân quyền Backend theo cặp `Action` + `Data Scope` (`OWN`, `ASSIGNED`, `COOPERATIVE`, `ORGANIZATION`, `ALL`). |
| 9 | **i18n VI / EN Rõ Ràng** | **PASS** | Kiến trúc đa ngôn ngữ độc lập, phân tách qua tệp JSON namespace; tuyệt đối không hard-code văn bản UI; database không lưu text dịch làm khóa ngoại. |
| 10 | **Correction & Audit Trail Rõ Ràng** | **PASS** | Nguyên tắc "Never Overwrite History": Bản ghi cũ chuyển sang `SUPERSEDED`, tạo bản ghi `CORRECTION` mới kèm lý do và lưu trọn vẹn vào `audit_logs` Append-Only. |
| 11 | **Blockchain Không Nhận Raw Declared Data** | **PASS** | Pipeline 7 bước nghiêm ngặt: Dữ liệu thô `Level 0` bị chặn; chỉ neo dữ liệu đã qua thẩm định `Level 2+` và phê duyệt 4 mắt. |
| 12 | **Legacy Documents Được Đánh Dấu Rõ** | **PASS** | Đã gắn cờ cảnh báo `LEGACY / PRE-PHASE-2 / NOT AUTHORITATIVE` trên toàn bộ 4 tài liệu kỹ thuật prototype cũ (`DATABASE.md`, `API_SPEC.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`). |
| 13 | **Open Decisions Có Assumptions / ADR** | **PASS** | Ghi nhận rõ 4 quyết định giả định: Chiết khấu ngoài scope V1, QR tương thích GS1, IoT scale là config concern, phân định rõ Hash-chain nội bộ vs. Mạng Blockchain. |

---

## 2. CÁC MÂU THUẪN ĐÃ PHÁT HIỆN GIỮA TÀI LIỆU CŨ VÀ ĐẶC TẢ CHÍNH THỨC

Trong quá trình đối soát giữa [`MASTER_SPEC.md`](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/MASTER_SPEC.md), [`PHASE_1_DOMAIN_ANALYSIS.md`](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/PHASE_1_DOMAIN_ANALYSIS.md) và các tài liệu kỹ thuật prototype cũ, các mâu thuẫn trọng yếu sau đã được phát hiện:

| Hạng mục Phân tích | Thiết kế Prototype Cũ (Legacy) | Đặc tả Hệ thống Chuẩn (Authoritative Target) | Mức độ Nghiêm trọng |
| :--- | :--- | :--- | :---: |
| **Mô hình Lô Hàng** | Chỉ có 1 bảng đơn `trace_batches` với trường `current_stage` phẳng | Phân tách rõ `HarvestBatch`, `ProcessingBatch`, `PackingBatch`, `Pallet` thành các Aggregate Roots riêng biệt trong mô hình DAG | **CRITICAL** |
| **Quản lý Giống & Xuất xứ** | Cho phép nhập tự do dạng văn bản (Free-text `variety`, `origin`) | Master Data phân cấp (`crop_varieties`, `translations`), kế thừa bất biến từ thượng nguồn, cấm gõ lại | **CRITICAL** |
| **Định danh Thực thể** | Dùng `INTEGER AUTOINCREMENT` | Dùng `UUIDv7` nội bộ kết hợp mã định danh nghiệp vụ sinh từ Server (VD: `HAR-2026-000001`) | **HIGH** |
| **Phân quyền Người dùng** | Dùng 1 trường `role` phẳng (`admin`, `producer`, `processor`, `logistics`) | Hệ thống RBAC đa tổ chức (`Multi-Tenancy`) kết hợp phạm vi dữ liệu (`Data Scope`) | **HIGH** |
| **Cân bằng Khối lượng** | Hoàn toàn chưa có cơ chế kiểm soát khối lượng đầu vào/đầu ra | Bắt buộc áp dụng Invariant Cân bằng Khối lượng (Mass Balance) hai chiều tại mọi khâu chuyển đổi | **CRITICAL** |
| **Toàn vẹn Dữ liệu Trust** | Người dùng tạo sự kiện là tự động băm và lưu trực tiếp vào chuỗi khối | Kiến trúc Data Trust 4 cấp độ (`Level 0-3`), Claim/Evidence, Risk Engine và phê duyệt 4 mắt | **CRITICAL** |
| **Kết quả Phân tích AI** | Kết quả suy luận AI tự động lưu thành sự kiện chân lý | AI chỉ là Bằng chứng / Tín hiệu rủi ro (`Evidence / Risk Signal`), bắt buộc qua Kỹ thuật viên/QA xác nhận | **HIGH** |
| **Cơ sở dữ liệu Production** | Dùng SQLite file cục bộ (`caymit.db`) | PostgreSQL + PostGIS (Dữ liệu quan hệ & Địa không gian) + TimescaleDB (IoT Chuỗi thời gian) | **HIGH** |
| **Lưu trữ Tệp tin Đa phương tiện** | Lưu trực tiếp vào thư mục ổ đĩa cục bộ | Tầng Object Storage tương thích S3 / MinIO (Database chỉ lưu metadata & hash) | **MEDIUM** |
| **Thuật ngữ Blockchain** | Đồng nhất chuỗi băm SHA-256 nội bộ trong SQLite là "Blockchain" | Phân biệt rành mạch giữa *Tamper-evident Hash-Chain nội bộ* và *Mạng Blockchain phân tán thực tế* | **MEDIUM** |

---

## 3. CÁC ĐIỀU CHỈNH ĐÃ THỰC HIỆN ĐỂ ĐỒNG BỘ DỮ LIỆU (RESOLUTIONS APPLIED)

1. **Chuẩn hóa Bộ Mã Vai trò (Canonical Role Codes):**
   - Đã đồng bộ 100% trong toàn bộ tài liệu Phase 1, xóa bỏ các mã không đồng nhất (`carrier_driver` ➔ `logistics_driver`, `exporter_staff` ➔ `export_officer`, `auditor_lab` ➔ `auditor_inspector`).
   - Bổ sung `buyer_partner` (Đối tác thu mua B2B) và `system_worker` (Tiến trình nền).

2. **Chuẩn hóa Invariant Cân bằng Khối lượng (Mass Balance):**
   - Đã cập nhật công thức hai chiều:
     $$\left| \text{Total Valid Input} - (\text{Total Output} + \text{Total Documented Loss} + \text{Total Reject}) \right| \le \text{Total Valid Input} \times \text{Configured\_Tolerance}$$
   - Đưa `Configured_Tolerance` thành tham số cấu hình có phiên bản (Mặc định 1.5% cho mít tươi), không hard-code trong logic ứng dụng.

3. **Gắn nhãn Cảnh báo Toàn bộ Tài liệu Kỹ thuật Cũ:**
   - Các file [**`DATABASE.md`**](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/DATABASE.md), [**`API_SPEC.md`**](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/API_SPEC.md), [**`ARCHITECTURE.md`**](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/ARCHITECTURE.md), [**`IMPLEMENTATION_PLAN.md`**](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/IMPLEMENTATION_PLAN.md) đã được đặt banner rõ ràng:
     `STATUS: LEGACY / PRE-PHASE-2 / NOT AUTHORITATIVE`.
   - Giữ nguyên các tệp này để làm tài liệu đối chiếu di chuyển mã nguồn trong các Phase tiếp theo.

---

## 4. BẢNG DANH MỤC TÀI LIỆU CHUẨN TẮC (DOCUMENT HIERARCHY & STATUS)

```
tammysmartfruit/
├── AGENTS.md                          [AUTHORITATIVE INSTRUCTIONS]
└── docs/
    ├── MASTER_SPEC.md                 [AUTHORITATIVE MASTER SPECIFICATION]
    ├── PHASE_1_DOMAIN_ANALYSIS.md     [APPROVED BUSINESS BASELINE - PHASE 1]
    ├── PHASE_1_CLOSURE_REPORT.md      [THIS CLOSURE REPORT]
    ├── BUSINESS_RULES.md              [SYNCHRONIZED BUSINESS RULES]
    ├── UI_UX.md                       [SYNCHRONIZED DESIGN SYSTEM GUIDELINES]
    │
    ├── ARCHITECTURE.md                [LEGACY / PRE-PHASE-2] (Sẽ thay thế trong Phase 2)
    ├── DATABASE.md                    [LEGACY / PRE-PHASE-2] (Sẽ thay thế trong Phase 3)
    ├── API_SPEC.md                    [LEGACY / PRE-PHASE-2] (Sẽ thay thế trong Phase 4)
    └── IMPLEMENTATION_PLAN.md         [LEGACY / PRE-PHASE-2] (Sẽ thay thế trong Phase 7)
```

---

## 5. THUẬT NGỮ CHUẨN TẮC (CANONICAL TERMINOLOGY REFERENCE)

### 5.1. Vai trò Hệ thống (Canonical Roles):
- `admin_hq`: Quản trị viên cấp cao Tổng công ty Tam Mỹ.
- `technician`: Cán bộ Kỹ thuật Nông nghiệp vùng trồng / Hợp tác xã.
- `farmer`: Nông hộ / Xã viên canh tác trực tiếp.
- `packhouse_lead`: Trưởng xưởng Sơ chế & Cơ sở Đóng gói.
- `qa_qc`: Chuyên viên Kiểm soát Chất lượng & An toàn thực phẩm.
- `warehouse_keeper`: Thủ kho Bảo quản & Kho lạnh WMS.
- `logistics_driver`: Tài xế Vận tải & Điều phối Đội xe lạnh.
- `export_officer`: Chuyên viên Hồ sơ Xuất khẩu & Thủ tục Hải quan.
- `auditor_inspector`: Thanh tra Độc lập / Tổ chức Cấp Chứng chỉ.
- `buyer_partner`: Đối tác Thu mua Quốc tế & Chuỗi Phân phối B2B.
- `system_worker`: Tiến trình Hệ thống Nền (Background Worker / Job Engine).

### 5.2. Cấp bậc Khẳng định Dữ liệu (Data Assurance Levels):
- `LEVEL_0_DECLARED`: Người dùng tự khai báo ban đầu.
- `LEVEL_1_SYSTEM_VALIDATED`: Hệ thống tự động kiểm tra quy tắc, Geofence GPS và Mass Balance.
- `LEVEL_2_ORGANIZATION_VERIFIED`: Kỹ thuật viên / QA Tam Mỹ thẩm định thực địa và ký số.
- `LEVEL_3_INDEPENDENT_CERTIFIED`: Phòng xét nghiệm độc lập hoặc Tổ chức cấp chứng chỉ xác nhận.

### 5.3. Công đoạn Chuỗi giá trị (Value Chain Stages):
`STAGE_CULTIVATION` ➔ `STAGE_HARVEST` ➔ `STAGE_RECEIVING` ➔ `STAGE_PROCESSING` ➔ `STAGE_PACKING` ➔ `STAGE_COLD_STORAGE` ➔ `STAGE_LOGISTICS` ➔ `STAGE_EXPORT` ➔ `STAGE_MARKET`

---

## 6. CÁC QUYẾT ĐỊNH NGHIỆP VỤ & GIẢ ĐỊNH ĐÃ THỐNG NHẤT (ADR & ASSUMPTIONS)

1. **ADR-01 (Phạm vi Thanh toán Thương mại):**
   - Nghiệp vụ tính toán chiết khấu thương mại, công nợ và thanh toán được xác định là **NẰM NGOÀI PHẠM VI CỐT LÕI (OUT OF CORE SCOPE) của phiên bản V1**. Phiên bản V1 tập trung tuyệt đối vào tính toàn vẹn vận hành chuỗi cung ứng, chất lượng kiểm dịch và truy xuất nguồn gốc.
2. **ADR-02 (Chuẩn Tem Mã QR):**
   - Thiết kế URL được chuẩn hóa và trừu tượng hóa, sẵn sàng ánh xạ tương thích chuẩn quốc tế **GS1 Digital Link**. Phiên bản V1 sử dụng Secure Internal Trace URL (`/t/{trace_code}`) với mã băm bảo mật ngẫu nhiên để phục vụ in tem thực tế trên quả và thùng carton.
3. **ADR-03 (Quy mô Triển khai IoT):**
   - Số lượng trạm quan trắc IoT và Camera không bị giới hạn cứng trong Domain Model mà là thông số cấu hình triển khai (*Configuration & Deployment concern*).
4. **ADR-04 (Kiến trúc Blockchain Adapter):**
   - Phân định rạch ròi giữa *Sổ cái băm nội bộ (Internal Hash-Chain)* và *Mạng lưới Blockchain phân tán bên ngoài*. Thiết kế Phase 2 sẽ bao gồm Interface `BlockchainAdapter` để có thể cắm ghép linh hoạt giữa Ethereum L2, Quorum hoặc Hyperledger Fabric.

---

## 7. ĐÁNH GIÁ CÁC ĐIỂM NGHẼN CÒN LẠI (REMAINING BLOCKERS)

- **Critical Blockers:** **KHÔNG CÓ (NONE)**.
- **Tình trạng Miền Nghiệp vụ:** Toàn bộ miền bài toán, quy tắc dữ liệu, máy trạng thái, giải pháp chống gian lận và cân bằng khối lượng đã được định nghĩa chặt chẽ và không còn mâu thuẫn logic.
- **Sẵn sàng chuyển giao:** Hệ sinh thái đã đủ điều kiện kỹ thuật để tiến hành thiết kế kiến trúc hệ thống chi tiết trong Phase 2.

---

## 8. KẾT LUẬN & TRẠNG THÁI CUỐI CÙNG (FINAL VERDICT)

```
======================================================================
                  PHASE 1: APPROVED FOR PHASE 2
======================================================================
  - Nguồn sự thật nghiệp vụ chính thức:
    * tammysmartfruit/AGENTS.md
    * tammysmartfruit/docs/MASTER_SPEC.md
    * tammysmartfruit/docs/PHASE_1_DOMAIN_ANALYSIS.md
    * tammysmartfruit/docs/BUSINESS_RULES.md
    * tammysmartfruit/docs/UI_UX.md

  - Hành động tiếp theo:
    * DỪNG LẠI và chờ Chủ dự án review, xác nhận bản báo cáo này.
    * Sau khi nhận lệnh phê duyệt sẽ bắt đầu Phase 2 (System Architecture).
    * TUYỆT ĐỐI CHƯA VIẾT SOURCE CODE TRONG GIAI ĐOẠN NÀY.
======================================================================
```
