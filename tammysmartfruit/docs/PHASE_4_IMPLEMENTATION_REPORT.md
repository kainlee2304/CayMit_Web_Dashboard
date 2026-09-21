# PHASE 4 CLOSURE REPORT — BACKEND CORE FOUNDATION & REAL RUNTIME VERIFICATION
## PRODUCTION-GRADE MODULAR MONOLITH CORE ARCHITECTURE VERIFICATION

> **Tài liệu Báo cáo Nghiệm thu Toàn diện Phase 4 (Comprehensive Phase 4 Closure Report)**  
> **Dự án:** Tam Mỹ Smart Fruit Supply Chain & Digital Operations Platform  
> **Trạng thái:** `PHASE 4 FOUNDATION: FINAL APPROVED FOR DOMAIN IMPLEMENTATION`  
> **Ngày hoàn thành:** 2026-09-02  
> **Môi trường thực thi thực tế:**  
> - **Backend Framework:** FastAPI 0.110+ | Async SQLAlchemy 2.0 | Pydantic V2 | Python 3.11.9  
> - **Cơ sở dữ liệu:** PostgreSQL 16.14 + PostGIS 3.6.4 + TimescaleDB 2.29.2 (Docker `pg16-test-db`, Port `5433`)  
> - **Bộ nhớ đệm & Message Broker:** Redis 7.0-alpine (Docker `redis-test`, Port `6379`)  
> - **Tiến trình xử lý nền:** Celery 5.6+ with Redis Broker  

---

## 1. TỔNG HỢP KẾT QUẢ RUNTIME FOUNDATION GATES

| Hạng mục Kiểm tra (Quality Gate) | Kết Quả | Bằng chứng Thực thi (Evidence) |
| :--- | :---: | :--- |
| **1. Celery + Redis Real E2E Pipeline** | **PASS** | Worker daemon PID 15316, broker `redis://127.0.0.1:6379/1`, Queue `default`. Event `9d88c63f...` chuyển `PENDING` → Celery dispatch → `COMPLETED` + `processed_events` ghi nhận. Replay event trùng lặp được phát hiện và bỏ qua đúng chuẩn Idempotency. |
| **2. Runtime Non-Superuser DB Role** | **PASS** | Role `tammy_app_user` (không có quyền SUPERUSER) kết nối DB thực tế: `domain_event_history` và `audit_logs` có quyền SELECT/INSERT (PASS), nhưng bị CHẶN HOÀN TOÀN khi cố tình UPDATE hoặc DELETE (PASS - Blocked as expected). |
| **3. Stale JWT Privilege Protection** | **PASS** | Server-side verification tại `get_current_principal`: User bị vô hiệu hóa (`is_active=False`) lập tức bị chặn 401; User bị đình chỉ (`is_suspended=True`) bị chặn 403; Thành viên tổ chức bị thu hồi (`membership_status='TERMINATED'`) bị chặn 403; Chuyển tổ chức không hợp lệ bị chặn 403. |
| **4. Toàn bộ Pytest Suite (27/27 Tests)** | **PASS** | 27/27 tests passed trong 25.18s bao phủ Security, RBAC, DataScope, Auth API, Org API, Audit Immutability, Event Journal, Transactional Outbox, Health/Readiness. |
| **5. FastAPI Import & Startup** | **PASS** | Khởi tạo thành công ứng dụng `Tam My Smart Fruit Backend`, lifespan probe kết nối PostgreSQL và Redis hoàn tất. |
| **6. OpenAPI Schema Generation** | **PASS** | Tự động sinh tệp `openapi.json` đầy đủ các endpoints chuẩn RESTful. |
| **7. Secret & Credentials Audit** | **PASS** | `.env`, `*.key`, `*.key.pub`, `jwt_rs256.key` được cấu hình nghiêm ngặt trong `.gitignore`. Mọi log và audit payload tự động thanh lọc (Redacted) các khóa nhạy cảm. |
| **8. API Contract & Error Envelopes** | **PASS** | Smoke-test thực tế: `/health` (200), `/ready` (200), `/auth/login` (200), `/auth/refresh` (200), `/auth/me` (200), `/organizations` (200), `/organizations/{id}` (200). Đã xác thực cấu trúc lỗi chuẩn máy đọc cho 401 (`MISSING_TOKEN`), 403 (`PERMISSION_DENIED` & `CROSS_TENANT_ACCESS_DENIED`), 404, 422 (`VALIDATION_ERROR`), 500 (Sanitized). |

---

## 2. CHI TIẾT CÁC LỖI ĐÃ PHÁT HIỆN & BIỆN PHÁP KHẮC PHỤC (FAILURES FOUND & FIXES APPLIED)

Trong quá trình chạy Runtime Verification trên môi trường thực tế, hệ thống đã phát hiện và xử lý triệt để 5 vấn đề:

1. **Vấn đề Ambiguous Foreign Keys giữa `User` và `Role`**:
   - *Hiện tượng:* Bảng `user_roles` có cả 2 khóa ngoại `user_id` và `granted_by` đều trỏ tới `users.id`.
   - *Khắc phục:* Bổ sung tường minh `primaryjoin="User.id == foreign(UserRole.user_id)"` và `secondaryjoin="Role.id == foreign(UserRole.role_id)"` trên SQLAlchemy relationship.
2. **Kiểu dữ liệu `ip_address` trong bảng `audit_logs` & `user_sessions`**:
   - *Hiện tượng:* PostgreSQL định nghĩa cột `ip_address` là kiểu `INET`, trong khi model ORM ban đầu khai báo `String(50)`.
   - *Khắc phục:* Chuyển đổi định nghĩa cột sang `from sqlalchemy.dialects.postgresql import INET`.
3. **Asyncpg Connection Pool trên Windows Proactor Loop trong Pytest**:
   - *Hiện tượng:* Khi chạy nhiều test async tuần tự, kết nối bị gắn vào event loop đã đóng của test trước.
   - *Khắc phục:* Cấu hình `NullPool` trong `conftest.py` và tạo hàm `get_worker_db_context()` chuyên biệt cho Celery worker/background tasks.
4. **Celery Worker Task Discovery**:
   - *Hiện tượng:* Celery daemon khi khởi chạy độc lập không tự động nạp các tác vụ trong `outbox_tasks.py`.
   - *Khắc phục:* Cấu hình `include=["app.workers.outbox_tasks"]` trực tiếp trong `celery_app.py`.
5. **Bảo vệ Stale JWT khi quyền hoặc trạng thái thay đổi ở Server-Side**:
   - *Hiện tượng:* Token JWT có thời hạn hiệu lực nhưng nếu User bị khóa hoặc bị thu hồi vai trò giữa chừng thì vẫn có thể thao tác nếu chỉ kiểm tra chữ ký tĩnh.
   - *Khắc phục:* Tích hợp cơ chế xác thực trạng thái thực tế thời gian thực tại `get_current_principal` dependency: kiểm tra `is_active`, `is_suspended`, `membership_status` và đồng bộ permissions trực tiếp từ CSDL.

---

## 3. BẰNG CHỨNG THỰC THI CELERY + REDIS RUNTIME E2E

```
=================================================================
[START] REAL CELERY + REDIS + POSTGRESQL 16 RUNTIME E2E VERIFICATION
=================================================================

[STEP 1] Checking Redis Broker Connection...
 -> Redis Ping (redis://localhost:6379/1): OK (PONG)

[STEP 2] Launching Real Celery Worker daemon...
 -> Celery Worker spawned (PID: 15316, Queue: 'default', Pool: threads)

[STEP 3] Generating Domain Event and Enqueueing to outbox_events (PENDING)...
 -> Initial outbox_events state: PENDING (Event ID: 9d88c63f-edc9-48cf-89dc-486ea07fffdf)

[STEP 4] Dispatching Celery Task via Redis Broker...
 -> Celery Task dispatched: Task ID = d0acdfdb-331e-4581-a042-1c31e2b0f3a2, Queue = 'default'

[STEP 5] Awaiting Celery Worker task execution (Polling Redis Backend)...
 -> Celery Task Result from Redis: {'status': 'SUCCESS', 'result': {'status': 'COMPLETED', 'event_id': '9d88c63f-edc9-48cf-89dc-486ea07fffdf', 'consumer': 'CELERY_REAL_E2E_CONSUMER'}, 'date_done': '2026-09-02T15:28:43.331933+00:00', 'task_id': 'd0acdfdb-331e-4581-a042-1c31e2b0f3a2'}

[STEP 6] Verifying Final Database State...
 -> Final outbox_events state: COMPLETED (Processed at: 2026-09-02 15:28:43.291021+00:00)
 -> processed_events idempotency record exists: True

[STEP 7] Testing Idempotency: Re-dispatching identical task to Celery...
 -> Replay Execution Result from Redis: {'status': 'SUCCESS', 'result': {'status': 'COMPLETED', 'event_id': '9d88c63f-edc9-48cf-89dc-486ea07fffdf', 'consumer': 'CELERY_REAL_E2E_CONSUMER'}, 'date_done': '2026-09-02T15:28:43.897458+00:00', 'task_id': '24b9e1d5-f047-4a62-b4ae-a23645d37dc2'}

=================================================================
[SUCCESS] CELERY + REDIS + POSTGRESQL 16 REAL E2E TEST: 100% PASS
=================================================================
  Worker PID            : 15316
  Broker Connection     : redis://localhost:6379/1
  Task ID               : d0acdfdb-331e-4581-a042-1c31e2b0f3a2
  Queue                 : default
  Initial Outbox State  : PENDING
  Final Outbox State    : COMPLETED
  Processed Events State: IDEMPOTENT_RECORD_PERSISTED
  Idempotency Replay    : PASS (Idempotency check intercepted, no duplicate side effects)
=================================================================
```

---

## 4. BẰNG CHỨNG THỰC THI RUNTIME DB ROLE VERIFICATION

```
[1] Connecting as Admin/Superuser to configure runtime role...
 -> Role tammy_app_user configured.
 -> Permissions granted & UPDATE/DELETE revoked on domain_event_history and audit_logs.

[2] Connecting as Runtime User (tammy_app_user)...

--- RUNTIME ROLE VERIFICATION REPORT ---
  domain_event_history: SELECT       : PASS
  domain_event_history: INSERT       : PASS
  domain_event_history: UPDATE       : PASS (Blocked as expected)
  domain_event_history: DELETE       : PASS (Blocked as expected)
  audit_logs: SELECT                 : PASS
  audit_logs: INSERT                 : PASS
  audit_logs: UPDATE                 : PASS (Blocked as expected)
  audit_logs: DELETE                 : PASS (Blocked as expected)

[SUCCESS] Runtime Application Role (tammy_app_user) fully verified!
```

---

## 5. BẰNG CHỨNG THỰC THI TOÀN BỘ TEST SUITE (27/27 TESTS PASSED)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Project\CayMit_Web_Dashboard\tammysmartfruit\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO

collecting ... collected 27 items

tests/test_audit_and_events.py::test_audit_logging_and_immutability PASSED [  3%]
tests/test_audit_and_events.py::test_domain_event_journal_persistence PASSED [  7%]
tests/test_audit_and_events.py::test_transactional_outbox_lifecycle_and_idempotency PASSED [ 11%]
tests/test_auth_api.py::test_auth_login_argon2id_success PASSED          [ 14%]
tests/test_auth_api.py::test_auth_login_pbkdf2_rehash_migration PASSED   [ 18%]
tests/test_auth_api.py::test_auth_login_invalid_password_returns_401 PASSED [ 22%]
tests/test_auth_api.py::test_refresh_token_rotation_and_reuse_detection PASSED [ 25%]
tests/test_auth_api.py::test_auth_me_endpoint PASSED                     [ 29%]
tests/test_auth_api.py::test_auth_logout PASSED                          [ 33%]
tests/test_health_api.py::test_health_liveness_probe PASSED              [ 37%]
tests/test_health_api.py::test_ready_readiness_probe PASSED              [ 40%]
tests/test_health_api.py::test_request_correlation_id_propagation PASSED [ 44%]
tests/test_org_api.py::test_admin_hq_can_view_all_organizations PASSED   [ 48%]
tests/test_org_api.py::test_farmer_sees_only_own_organization PASSED     [ 51%]
tests/test_org_api.py::test_cross_tenant_isolation_rejection PASSED      [ 55%]
tests/test_org_api.py::test_create_organization_rbac_enforcement PASSED  [ 59%]
tests/test_rbac_datascope.py::test_principal_has_permission PASSED       [ 62%]
tests/test_rbac_datascope.py::test_enforce_data_scope_filtering PASSED   [ 66%]
tests/test_security.py::test_argon2id_hashing_and_verification PASSED    [ 70%]
tests/test_security.py::test_pbkdf2_legacy_verification_and_rehash_flag PASSED [ 74%]
tests/test_security.py::test_jwt_rs256_signing_and_decoding PASSED       [ 77%]
tests/test_security.py::test_jwt_rs256_tampering_rejection PASSED        [ 81%]
tests/test_security.py::test_opaque_refresh_token_and_sha256 PASSED      [ 85%]
tests/test_stale_jwt_mitigation.py::test_deactivated_user_token_is_blocked_immediately PASSED [ 88%]
tests/test_stale_jwt_mitigation.py::test_suspended_user_token_is_blocked_immediately PASSED [ 92%]
tests/test_stale_jwt_mitigation.py::test_revoked_membership_blocks_organization_access PASSED [ 96%]
tests/test_stale_jwt_mitigation.py::test_unauthorized_organization_switch_is_blocked PASSED [100%]

============================= 27 passed in 25.18s =============================
```

---

## 6. KẾT LUẬN & PHÊ DUYỆT CUỐI CÙNG (FINAL EXIT APPROVAL)

Mọi yêu cầu kiểm chứng runtime thực tế, bảo mật cơ sở dữ liệu, an toàn Token, tiến trình Celery, và quy chuẩn API đã được xác nhận đạt 100%.

- **Remaining Blockers:** `NONE`
- **Final Official Status:** `PHASE 4 FOUNDATION: FINAL APPROVED FOR DOMAIN IMPLEMENTATION`
