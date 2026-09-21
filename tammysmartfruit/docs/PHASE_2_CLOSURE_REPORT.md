# PHASE 2 CLOSURE & ARCHITECTURE AUDIT REPORT
## TAM MỸ SMART FRUIT ECOSYSTEM

> **Báo cáo Nghiệm thu & Khóa Toàn diện Thiết kế Kiến trúc Kỹ thuật Phase 2 (Final Phase 2 Lock Report)**  
> **Ngày thực hiện:** 28/08/2026  
> **Trạng thái:** ✅ **PHASE 2: FINAL APPROVED FOR PHASE 3**  
> **Nguyên tắc:** DỪNG TOÀN BỘ HOẠT ĐỘNG CODING — Chờ xem xét và phê duyệt trước khi chuyển sang Phase 3 (Database Architecture & DDL).

---

## 1. BẢNG ĐÁNH GIÁ CÁC TIÊU CHÍ KHÓA KIẾN TRÚC CUỐI CÙNG (FINAL ARCHITECTURAL CONFIRMATIONS)

| STT | Quyết định Kiến trúc Then chốt | Kết quả | Chi tiết Xác thực trong Hệ thống Tài liệu Chính thức |
| :---: | :--- | :---: | :--- |
| 1 | **Xác Nhận Chính Sách Rủi Ro Có Thể Cấu Hình (Risk Policy Configurable Confirmed)** | **PASS** | Loại bỏ hoàn toàn việc hard-code `risk <= 25`. Việc neo chuỗi khối yêu cầu `RiskPolicy.evaluate() == ALLOW_ANCHOR` dựa trên chính sách rủi ro có phiên bản, nhận biết ngày hiệu lực (`effective-date aware`) và có thể kiểm toán. |
| 2 | **Xác Nhận Sổ Sự Kiện Bền Vững (Durable Domain Event Journal Confirmed)** | **PASS** | Phân định rạch ròi: Bảng `domain_event_history` (Append-Only, không bao giờ bị xóa) là nguồn sự thật bền vững duy nhất để tái tạo Đồ thị DAG (`trace_nodes`, `trace_edges`); Bảng `outbox_events` chỉ phục vụ hàng đợi gửi tin cậy và có thể dọn dẹp theo Retention Policy. |
| 3 | **Xác Nhận Kiến Trúc Bảo Mật Argon2id + RS256 (Security Decision Confirmed)** | **PASS** | Mật khẩu mới bắt buộc dùng `Argon2id`; mật khẩu cũ chuyển đổi xác thực bằng `PBKDF2` và tự động băm lại (`Rehash`) thành Argon2id ngay khi đăng nhập thành công; Token truy cập dùng `JWT RS256` bất đối xứng (Private key lưu qua Secret Manager / Env, không lưu DB; Public key chia sẻ cho trusted services); Refresh Token ngẫu nhiên (CSPRNG) chỉ lưu mã băm SHA-256 trong Redis kèm cơ chế xoay vòng và thu hồi Token Family khi phát hiện tái sử dụng. |
| 4 | **Canonical Module Count Chính Xác** | **PASS** | Định danh chính xác **đúng 35 modules** độc lập (Foundation: 4, Upstream: 9, Supply Chain: 10, Trust/Cross-Cutting: 12) trong `MODULE_ARCHITECTURE.md`. |
| 5 | **Không Có Circular Dependency** | **PASS** | `IdentityModule` (User/Credential) và `OrganizationModule` (Membership/Org) được tách độc lập, kết nối qua Auth Middleware Composition. |
| 6 | **Data Trust ➔ Approval ➔ Blockchain Đúng Thứ Tự** | **PASS** | Sự kiện `BlockchainAnchorEligibleEvent` chỉ phát sinh khi đủ 5 điều kiện tiên quyết (Assurance Policy, Risk Policy, Evidence Policy, Verification, 4-Eyes Approval). `BlockchainModule` chỉ consume duy nhất event này. |
| 7 | **Export Gọi Certificate Validation Đúng Boundary** | **PASS** | `ExportModule` gọi hợp đồng chính thức `ICertificateService.validateCertificateValid()` để đối soát chứng chỉ kiểm dịch quốc tế. |
| 8 | **Một Background Job Stack Canonical Duy Nhất** | **PASS** | Chốt một stack Python-compatible chuẩn: **Celery 5.3+ kết hợp Redis 7 Message Broker**, phân bổ 5 hàng đợi Celery chuyên biệt. |
| 9 | **Outbox Crash & Retry Semantics Rõ Ràng** | **PASS** | Bổ sung `locked_at`, `locked_by`, `lease_timeout (5 phút)` cho bảng `outbox_events` để phục hồi tự động khi Worker crash giữa chừng. |
| 10 | **Offline PWA Storage Canonical** | **PASS** | Chuẩn hóa **IndexedDB (Dexie.js)** cho 4 tác vụ hiện trường thiết yếu (Farm Diary, Inspection, Harvest Draft, Photo Queue); không offline toàn bộ ERP. |
| 11 | **UUIDv7 Phục Vụ Index Locality (Không Phải Security Control)** | **PASS** | UUIDv7 phục vụ Index-Locality và sắp xếp thời gian B-Tree; Public Trace dùng chuỗi ngẫu nhiên bảo mật riêng (`trace_code`). |
| 12 | **FK Delete Policy Theo Từng Quan Hệ** | **PASS** | Phân định cụ thể `RESTRICT` (Bảo vệ Lineage/Audit), `CASCADE` (Child items nội bộ), `SET NULL` (Optional assignment), `ARCHIVE` (Soft delete). |
| 13 | **Chỉ Tiêu Hiệu Năng Là Target SLOs Thực Tế** | **PASS** | Đổi các số liệu thành Target SLOs (API P95 $\le 200\text{ms}$, Geofence P95 $\le 20\text{ms}$, Recall Blast Radius $\le 500\text{ms}$), không đưa ra cam kết ảo. |
| 14 | **Không Còn Mâu Thuẫn Kiến Trúc Critical/High** | **PASS** | Toàn bộ 12 tài liệu kiến trúc kỹ thuật và 10 ADRs hoàn toàn đồng bộ với `MASTER_SPEC.md` và `PHASE_1_DOMAIN_ANALYSIS.md`. |

---

## 2. BẢNG TỔNG HỢP CÁC ĐIỀU CHỈNH ĐÃ HOÀN TẤT TRONG PHASE 2 LOCK

| Vấn đề Mâu thuẫn Ban đầu | Bản Thiết kế Cũ | Giải pháp Khóa Kiến trúc Cuối cùng (Final Lock) |
| :--- | :--- | :--- |
| **Ngưỡng Rủi ro Blockchain** | Hardcode `risk_score <= 25` | Chuyển thành `RiskPolicy.evaluate() == ALLOW_ANCHOR` cấu hình linh hoạt theo phiên bản. |
| **Nguồn Rebuild Đồ thị DAG** | Outbox events là nguồn rebuild | Tạo bảng riêng `domain_event_history` (Append-Only vĩnh viễn) làm nguồn sự thật tái tạo DAG. |
| **Băm Mật khẩu & Ký Token** | Ghi "JWT PBKDF2 210,000 rounds" | Mật khẩu: **Argon2id** (Tự động Rehash từ PBKDF2 khi đăng nhập); Token: **JWT RS256** (Private key trong Vault/Env). |
| **Số lượng Module** | Ghi 32 modules nhưng thực tế có 35 | Tách và định nghĩa đầy đủ **35 modules** riêng biệt trong `MODULE_ARCHITECTURE.md`. |
| **Phụ thuộc Identity vs Org** | Identity phụ thuộc Org, Org consume Event từ Identity | Tách `IdentityModule` độc lập; giao tiếp qua Auth Middleware Composition. |
| **Công nghệ Background Queue** | Ghi "Celery / BullMQ" | Chốt một giải pháp chuẩn duy nhất: **Celery 5.3+ + Redis 7 Broker**. |
| **Khả năng Phục hồi Outbox** | Worker crash làm kẹt status PROCESSING | Bổ sung cơ chế **Lease Recovery** (`locked_at`, `lease_timeout = 5 phút`). |
| **Lưu trữ Ngoại tuyến PWA** | Ghi chung chung SQLite cache | Chuẩn hóa **IndexedDB (Dexie.js)** cho 4 tác vụ hiện trường có chọn lọc. |

---

## 3. DANH MỤC TÀI LIỆU KIẾN TRÚC CHÍNH THỨC ĐÃ ĐƯỢC XÁC THỰC

```
tammysmartfruit/docs/
├── ARCHITECTURE.md                  [AUTHORITATIVE SYSTEM ARCHITECTURE BLUEPRINT]
├── MODULE_ARCHITECTURE.md           [CANONICAL 35-MODULE SPECIFICATIONS & CONTRACTS]
├── EVENT_ARCHITECTURE.md            [DOMAIN EVENT HISTORY, LEASE OUTBOX & CELERY QUEUE]
├── DATA_TRUST_ARCHITECTURE.md       [CLAIM MODEL, CONFIGURABLE RISK POLICY & APPROVAL]
├── TRACEABILITY_ARCHITECTURE.md     [EVENT-DERIVED DAG PROJECTION & RECALL ENGINE]
├── BLOCKCHAIN_ARCHITECTURE.md       [BLOCKCHAIN ADAPTER & SELECTIVE ANCHORING]
├── IOT_ARCHITECTURE.md              [TIMESCALEDB HYPERTABLES & TELEMETRY INGEST]
├── AI_ARCHITECTURE.md               [ISOLATED 4-TIER GUARD AI ENGINE & PROVENANCE]
├── SECURITY_ARCHITECTURE.md         [ARGON2ID, RS256, REHASH ON LOGIN & DATA SCOPE]
├── DEPLOYMENT_ARCHITECTURE.md       [DOCKER COMPOSE TOPOLOGY & PITR DISASTER RECOVERY]
├── LEGACY_MIGRATION_STRATEGY.md     [5R CODE REUSE & DATA MIGRATION PLAN]
├── PHASE_2_ARCHITECTURE_REVIEW.md   [PHASE 2 REVIEW REPORT]
├── PHASE_2_CLOSURE_REPORT.md        [THIS FINAL CLOSURE REPORT]
└── ADR/
    ├── ADR-005-modular-monolith.md
    ├── ADR-006-postgresql-postgis.md
    ├── ADR-007-timeseries-strategy.md
    ├── ADR-008-event-outbox-queue.md
    ├── ADR-009-object-storage.md
    ├── ADR-010-blockchain-abstraction.md
    ├── ADR-011-ai-service-boundary.md
    ├── ADR-012-multitenancy-datascope.md
    ├── ADR-013-bilingual-i18n.md
    └── ADR-014-offline-pwa-sync.md
```

---

## 4. KẾT LUẬN & TRẠNG THÁI CUỐI CÙNG (FINAL VERDICT)

```
======================================================================
              PHASE 2: FINAL APPROVED FOR PHASE 3
======================================================================
  - Xác nhận 3 quyết định then chốt:
    [PASS] Risk policy configurable confirmed (no hardcoded risk <= 25).
    [PASS] Durable domain event journal confirmed (domain_event_history -> DAG projection).
    [PASS] Argon2id + RS256 security decision confirmed (with legacy PBKDF2 rehash on login).

  - Hành động tiếp theo:
    * DỪNG LẠI và chờ Chủ dự án review, xác nhận bản báo cáo này.
    * Sau khi nhận lệnh phê duyệt sẽ bắt đầu Phase 3 (Database Conceptual/Logical/Physical DDL Design).
    * TUYỆT ĐỐI CHƯA VIẾT SOURCE CODE & CHƯA THIẾT KẾ DDL TRONG LƯỢT NÀY.
======================================================================
```
