# LEGACY DATA MIGRATION & TRANSFORMATION SPECIFICATION
## MAPPING SQLITE (CAYMIT.DB) TO CANONICAL POSTGRESQL 16 ENTERPRISE SCHEMA

> **Tài liệu Đặc tả Chuyển đổi & Ánh xạ Dữ liệu Cũ (Legacy Data Mapping Specification)**  
> **Phiên bản:** 3.0.0-PROD  
> **Nguồn:** SQLite Database (`backend/caymit.db`)  
> **Đích:** PostgreSQL 16 Enterprise Schema (35 Modules)  

---

## 1. NGUYÊN TẮC CHUYỂN ĐỔI DỮ LIỆU CŨ (MIGRATION PRINCIPLES)

1. **Bảo Toàn Xuất Xứ (Provenance Tagging):** Toàn bộ dữ liệu chuyển đổi từ hệ thống cũ bắt buộc gắn cờ xuất xứ `source_origin = 'LEGACY_IMPORT'`.
2. **Không Tự Động Nâng Cấp Độ Tin Cậy:** Dữ liệu giống cây hoặc vùng trồng dạng chuỗi tự do (Free-text) từ SQLite chỉ được gán mức độ tin cậy ban đầu là `LEVEL_0_DECLARED`. Muốn lên `LEVEL_2_VERIFIED`, Kỹ thuật viên phải mở phiên thẩm định và ký xác thực.
3. **Chiến Lược Tái Băm Mật Khẩu (Password Rehash Pipeline):**
   - Mật khẩu cũ được import vào `user_credentials` với `password_algo = 'PBKDF2_LEGACY'` và `rehash_required = TRUE`.
   - Khi người dùng đăng nhập lần đầu tiên thành công, hệ thống tự động băm lại bằng `Argon2id` và cập nhật bản ghi.

---

## 2. BẢNG ÁNH XẠ CHI TIẾT CÁC THỰC THỂ (DETAILED ETL MAPPING MATRIX)

| Bảng Cũ trong SQLite (`caymit.db`) | Phân Loại 5R | Bảng Đích trong PostgreSQL 16 Mới | Quy Tắc Chuyển Đổi & Ánh Xạ Dữ Liệu (ETL Transformation Rules) |
| :--- | :---: | :--- | :--- |
| **`trace_users`** | **TRANSFORM** | `users`, `user_credentials`, `user_organization_memberships` | - Tạo bản ghi `users` với `id = generate_uuid_v7()`.<br>- Chuyển mật khẩu cũ sang `user_credentials` gắn cờ `rehash_required = TRUE`.<br>- Tự động gán quyền thành viên vào tổ chức mặc định: `TAMMY_HQ`. |
| **`trace_batches`** | **MIGRATE** | `harvest_batches`, `trace_nodes` | - Chuyển đổi các lô cũ sang `harvest_batches` với trạng thái `harvest_status = 'ACCEPTED'`.<br>- Tạo nút tương ứng trong `trace_nodes` với `node_type = 'HARVEST_BATCH'` và gắn `data_hash` cũ. |
| **`trace_events`** | **MIGRATE** | `domain_event_history`, `trace_edges` | - Chuyển đổi các sự kiện cũ thành các bản ghi trong `domain_event_history`.<br>- Thiết lập các cạnh định hướng `trace_edges` với `contribution_ratio = 1.0000`. |
| **`predictions`** | **TRANSFORM** | `ai_inference_jobs`, `ai_predictions` | - Ánh xạ kết quả suy luận AI cũ sang `ai_predictions` thuộc Layer 4.<br>- Gán `confidence_score` và nhãn bệnh chuẩn hóa từ Master Data. |
| **`sensor_data`** | **MIGRATE** | `sensor_readings` (TimescaleDB) | - Import toàn bộ chuỗi số liệu nhiệt độ, độ ẩm cũ vào bảng `sensor_readings` theo đúng mốc thời gian `time`. |
| **`mock_audit_events`** | **DROP** | *Không import* | - Các bản ghi giả lập/test của môi trường cũ được hủy bỏ hoàn toàn trước khi golive. |

---

## 3. SCRIPT CHUYỂN ĐỔI DỮ LIỆU MẪU (PYTHON ETL MIGRATION SCRIPT TEMPLATE)

```python
"""
Tam Mỹ Smart Fruit - One-Time Legacy Migration Script (ETL)
Connects to SQLite caymit.db and securely populates PostgreSQL 16.
"""
import sqlite3
import psycopg2
import uuid

def migrate_legacy_data():
    sqlite_conn = sqlite3.connect("backend/caymit.db")
    pg_conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/tammysmartfruit")
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # 1. Fetch legacy users
    sqlite_cursor.execute("SELECT id, username, password_hash, role, full_name FROM trace_users")
    legacy_users = sqlite_cursor.fetchall()
    
    for user in legacy_users:
        user_id = str(uuid.uuid4())
        username, old_hash, role, full_name = user[1], user[2], user[3], user[4]
        
        # Insert user
        pg_cursor.execute("""
            INSERT INTO users (id, username, full_name, is_active, preferred_locale)
            VALUES (%s, %s, %s, TRUE, 'vi')
            ON CONFLICT (username) DO NOTHING
        """, (user_id, username, full_name))
        
        # Insert legacy credential with rehash_required = TRUE
        pg_cursor.execute("""
            INSERT INTO user_credentials (user_id, password_hash, password_algo, rehash_required)
            VALUES (%s, %s, 'PBKDF2_LEGACY', TRUE)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, old_hash))
        
    pg_conn.commit()
    print("[ETL] Successfully migrated legacy users with password rehash flags.")

if __name__ == "__main__":
    migrate_legacy_data()
```
