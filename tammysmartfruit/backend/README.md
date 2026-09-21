# TAM MỸ SMART FRUIT — BACKEND CORE FOUNDATION (PHASE 4)

Production-grade Modular Monolith Backend API built with **FastAPI, Async SQLAlchemy 2.0, Pydantic V2, PostgreSQL 16 (PostGIS + TimescaleDB), Redis 7, and Celery 5.3+**.

---

## 1. Kiến Trúc & Cấu Trúc Thư Mục (Architecture Structure)

```
tammysmartfruit/backend/
├── app/
│   ├── main.py                    # FastAPI app initialization, lifespan, CORS, error handlers, middleware
│   ├── core/
│   │   ├── config.py              # Pydantic V2 Settings (.env loader)
│   │   ├── database.py            # Async SQLAlchemy 2.0 Engine, session generator, health checks
│   │   ├── security.py            # Argon2id, PBKDF2 rehash, RS256 JWT, CSPRNG Refresh Token
│   │   ├── errors.py              # Standardized machine-readable error responses
│   │   ├── logging.py             # Structured JSON logging with credential redaction
│   │   ├── request_context.py     # Request-ID & Correlation-ID ContextVars
│   │   ├── middleware.py          # HTTP tracing & structured access logging middleware
│   │   └── rbac.py                # 11 Canonical Roles, 5 Canonical Scopes, SQL DataScope filters
│   ├── shared/
│   │   ├── base_model.py          # DeclarativeBase mapped to PostgreSQL 16 schema
│   │   └── dependencies.py        # Principal resolution & RBAC permission guards
│   ├── modules/
│   │   ├── identity/              # Users, Credentials, Roles, Permissions, Sessions, Auth router
│   │   ├── organization/          # Organizations, Departments, Teams, Memberships, Scope router
│   │   ├── audit/                 # Append-only audit logger with secret redaction
│   │   ├── events/                # Domain Event journal with canonical SHA-256 payload hash
│   │   └── outbox/                # Transactional Outbox with lease recovery & consumer idempotency
│   ├── workers/
│   │   ├── celery_app.py          # Celery configuration with Redis broker & canonical queues
│   │   └── outbox_tasks.py        # Celery outbox poller & dispatcher task
│   └── api/
│       └── v1/
│           └── router.py          # API V1 Router mounting /auth, /organizations
├── scripts/
│   └── seed_dev_data.py           # Seed script (Roles, Perms, HQ Org, Admin, Farmer, Legacy user)
├── tests/
│   ├── conftest.py                # Pytest async fixtures (NullPool, AsyncClient)
│   ├── test_security.py           # Unit tests (Argon2id, PBKDF2, JWT RS256, Refresh Token rotation)
│   ├── test_rbac_datascope.py     # Unit tests (RBAC evaluation, DataScope SQL filter)
│   ├── test_auth_api.py           # Real DB Integration tests (Login, PBKDF2 rehash, Refresh, Logout, Me)
│   ├── test_org_api.py            # Real DB Integration tests (Orgs, Cross-Tenant Isolation 403)
│   ├── test_audit_and_events.py   # Real DB Integration tests (Audit append-only, Event journal, Outbox)
│   └── test_health_api.py         # Infrastructure tests (/health, /ready, Request Tracing)
├── pytest.ini
├── requirements.txt
└── run_dev.py
```

---

## 2. Các Quy Chuẩn Đã Được Triển Khai & Kiểm Chứng (Implemented & Verified Standards)

1. **Authentication & Cryptography**:
   - Mật khẩu mới băm bằng **Argon2id** (64MB memory, 3 iterations, 4 parallelism).
   - Tự động phát hiện và nâng cấp (Automatic Rehash on Login) tài khoản cũ từ `PBKDF2-HMAC-SHA256` sang `Argon2id`.
   - Access Token: Ký số bất đối xứng **JWT RS256** (RSA 2048-bit), kiểm tra nghiêm ngặt `issuer`, `audience`, `exp`, `sub`, `roles`, `permissions`, `scope`.
   - Refresh Token: Chuỗi ngẫu nhiên mật mã học **CSPRNG 256-bit**, băm SHA-256 lưu DB/Redis, cơ chế xoay vòng (Rotation) và **Reuse Detection** (thu hồi toàn bộ Token Family nếu phát hiện token cũ bị gửi lại).

2. **RBAC & Multi-Tenant Data Scope**:
   - 11 Vai trò chuẩn tắc (`admin_hq`, `technician`, `farmer`, `packhouse_lead`, `qa_qc`, `warehouse_keeper`, `logistics_driver`, `export_officer`, `auditor_inspector`, `buyer_partner`, `system_worker`).
   - 5 Phạm vi dữ liệu (`OWN`, `ASSIGNED`, `COOPERATIVE`, `ORGANIZATION`, `ALL`).
   - Kiểm tra phân quyền đa chiều tại Application Services (`require_permission`) kết hợp bộ lọc SQL động `enforce_data_scope`. Chống triệt để việc tấn công truyền giả mạo `organization_id`.

3. **Audit Infrastructure**:
   - Ghi nhận nhật ký kiểm toán bất biến vào bảng `audit_logs` trong cùng Database Transaction.
   - Tự động thanh lọc (Redact) các trường nhạy cảm: `password`, `token`, `secret`, `private_key`.
   - PostgreSQL Database Trigger bảo vệ chống UPDATE/DELETE bảng `audit_logs`.

4. **Domain Event Journal & Transactional Outbox**:
   - Sổ nhật ký sự kiện bền vững `domain_event_history` lưu trữ vĩnh viễn với mã băm SHA-256 Canonical Payload để phục vụ tái xây dựng Đồ thị Truy xuất DAG.
   - Hàng đợi `outbox_events` với cơ chế khóa Lease Recovery (`status = 'PROCESSING'`, `lease_expires_at`), Exponential Backoff khi thất bại, và Consumer Idempotency qua bảng `processed_events`.

5. **Error Contract & Tracing**:
   - Định dạng lỗi chuẩn máy đọc: `{"error": {"code": "...", "message_key": "...", "field_errors": [], "request_id": "..."}}`.
   - Middleware gắn và lan truyền `X-Request-ID`, `X-Correlation-ID` qua request context, database logs, audit entries, domain events, và Celery tasks.

6. **Infrastructure Probes**:
   - `/health`: Liveness probe HTTP 200.
   - `/ready`: Readiness probe kiểm tra kết nối thời gian thực tới PostgreSQL 16 và Redis 7.

---

## 3. Hướng Dẫn Khởi Chạy & Kiểm Thử (Running & Testing)

### Cài đặt môi trường:
```bash
pip install -r requirements.txt
```

### Nạp dữ liệu mẫu (Seeding):
```bash
python -m scripts.seed_dev_data
```

### Khởi chạy Backend Server:
```bash
python run_dev.py
```
Tài liệu tương tác OpenAPI / Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### Chạy toàn bộ Test Suite (23/23 Tests):
```bash
pytest -v
```
