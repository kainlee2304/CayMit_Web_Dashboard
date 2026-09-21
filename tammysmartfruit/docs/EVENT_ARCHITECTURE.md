# EVENT & ASYNC QUEUE ARCHITECTURE — TAM MỸ SMART FRUIT ECOSYSTEM
## DOMAIN EVENTS, TRANSACTIONAL OUTBOX WITH LEASE RECOVERY & CELERY QUEUE

> **Tài liệu Kiến trúc Sự kiện & Xử lý Bất đồng bộ (Event & Queue Specification)**  
> **Phiên bản:** 2.1.0-PROD  
> **Áp dụng:** Toàn bộ tầng giao tiếp liên module và tích hợp ngoại vi  

---

## 1. PHÂN LOẠI SỰ KIỆN HỆ THỐNG (EVENT TAXONOMY)

Hệ thống phân định rạch ròi giữa 4 loại sự kiện, không trộn lẫn mục đích sử dụng:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. DOMAIN EVENTS (Sự kiện Miền Nội bộ)                                                 │
│ - Đại diện cho một sự thật đã diễn ra trong Domain Model (VD: `HarvestBatchAccepted`). │
│ - Được phát sinh trực tiếp từ Aggregate Root bên trong DB Transaction.                 │
│ - Tác dụng: Kích hoạt cập nhật Traceability DAG Projection, tính toán Mass Balance.    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. INTEGRATION EVENTS (Sự kiện Tích hợp Ngoại vi)                                     │
│ - Đóng gói dữ liệu tối giản để truyền ra hệ thống bên ngoài (Hải quan, Đối tác B2B).   │
│ - Chuyển tiếp qua Celery Worker / Webhook có xác thực chữ ký HMAC.                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. AUDIT EVENTS (Sự kiện Kiểm toán Bất biến)                                           │
│ - Ghi nhận dấu vết thao tác của người dùng: `before_state`, `after_state`, IP, Actor.   │
│ - Ghi trực tiếp vào bảng `audit_logs` (Append-Only) trong cùng DB Transaction.         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. BLOCKCHAIN ANCHOR ELIGIBLE EVENT (Sự kiện Đủ điều kiện Neo Chuỗi khối)             │
│ - Chỉ phát sinh khi thỏa mãn 100% 5 điều kiện: Level 2+, Risk OK, Evidence OK,         │
│   Verification OK, 4-Eyes Approval OK.                                                 │
│ - Xử lý bất đồng bộ qua Celery Worker để gom nhóm Merkle Tree và neo chuỗi khối.      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CẤU TRÚC PHẦN TỬ SỰ KIỆN CHUẨN (CANONICAL DOMAIN EVENT SCHEMA)

Mọi Domain Event trong hệ sinh thái đều bắt buộc kế thừa cấu trúc JSON Envelope chuẩn:

```json
{
  "event_id": "0191632f-a18b-7000-8cb4-816223405781",
  "event_type": "BlockchainAnchorEligibleEvent",
  "event_version": "1.0.0",
  "aggregate_type": "HarvestBatch",
  "aggregate_id": "0191632e-f001-7000-9ab1-332211009988",
  "organization_id": "01916320-0000-7000-8000-000000000001",
  "actor_id": "01916322-1111-7000-8111-222233334444",
  "occurred_at": "2026-08-28T09:30:00.000Z",
  "correlation_id": "req-987654321-trace-abc",
  "causation_id": "0191632f-a000-7000-8cb4-777223405000",
  "payload": {
    "entity_type": "HARVEST_BATCH",
    "entity_code": "HAR-2026-000125",
    "canonical_data_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "assurance_level": "LEVEL_2_ORGANIZATION_VERIFIED",
    "verifier_id": "01916322-1111-7000-8111-222233334444",
    "approver_id": "01916322-2222-7000-8222-555566667777",
    "risk_score": 12.50,
    "evidence_count": 3
  }
}
```

---

## 3. PHÂN BIỆT RẠCH RÒI: SỔ NHẬT KÝ SỰ KIỆN BỀN VỮNG VS. HÀNG ĐỢI OUTBOX

Hệ thống phân định rạch ròi giữa 2 bảng để bảo vệ khả năng tái xây dựng Đồ thị Truy xuất (Traceability DAG Projection):

### A. Sổ Nhật ký Sự kiện Bền vững (`domain_event_history` - Durable Event Journal):
- **Bản chất:** Bảng Append-Only lưu trữ vĩnh viễn các sự kiện miền quan trọng để phục vụ kiểm toán và **tái xây dựng (Rebuild) 100% Đồ thị Truy xuất DAG** khi cần.
- **Quy tắc:** Tuyệt đối không bao giờ bị xóa, cắt tỉa hay cập nhật.

```sql
CREATE TABLE domain_event_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    event_version VARCHAR(20) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_id VARCHAR(120),
    causation_id UUID,
    payload JSONB NOT NULL,
    payload_hash CHAR(64) NOT NULL, -- SHA-256 mã băm Canonical JSON của payload
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domain_history_aggregate ON domain_event_history(aggregate_type, aggregate_id);
CREATE INDEX idx_domain_history_time ON domain_event_history(occurred_at ASC);
```

### B. Hàng đợi Giao dịch Outbox (`outbox_events` - Reliable Delivery Queue):
- **Bản chất:** Bảng trung gian xử lý gửi bất đồng bộ tin cậy (At-Least-Once Delivery) sang Message Broker / Celery Workers.
- **Quy tắc:** Có vòng đời trạng thái (`PENDING` ➔ `PROCESSING` ➔ `COMPLETED` / `FAILED`), hỗ trợ cơ chế Lease Recovery và **có thể được dọn dẹp/lưu trữ theo chính sách Retention Policy** (ví dụ: chuyển sang bảng lưu trữ lạnh sau 30 ngày thành công). Đây **KHÔNG PHẢI** là nguồn duy nhất để Rebuild Traceability.

```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    event_version VARCHAR(20) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(30) DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(80),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 5,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

-- Chỉ mục phân vùng trạng thái phục vụ Polling và Phục hồi sự cố (Lease Timeout 5 phút)
CREATE INDEX idx_outbox_recoverable ON outbox_events(status, created_at) 
WHERE status = 'PENDING' OR (status = 'PROCESSING' AND locked_at < NOW() - INTERVAL '5 minutes');
```

### Cơ chế Polling an toàn với Lease Timeout:
```sql
UPDATE outbox_events
SET status = 'PROCESSING',
    locked_at = NOW(),
    locked_by = :worker_id
WHERE id IN (
    SELECT id FROM outbox_events
    WHERE status = 'PENDING' 
       OR (status = 'PROCESSING' AND locked_at < NOW() - INTERVAL '5 minutes')
    ORDER BY created_at ASC
    LIMIT 50
    FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

---

## 4. QUY HOẠCH HÀNG ĐỢI NỀN CELERY + REDIS (CELERY QUEUE TOPOLOGY)

Backend chuẩn hóa sử dụng **Celery 5.3+** với **Redis 7** làm Message Broker:

| Tên Hàng Đợi (Celery Queue) | Ưu Tiên | Concurrency | Mục Đích Sử Dụng |
| :--- | :---: | :---: | :--- |
| `queue_critical_trust` | **CAO NHẤT** | 5 Workers | Xử lý neo Blockchain Merkle Batch, ký số bằng chứng, cập nhật DAG Projection. |
| `queue_iot_telemetry` | **CAO** | 8 Workers | Nhận luồng dữ liệu cảm biến, nạp TimescaleDB và phát hiện cảnh báo vi khí hậu. |
| `queue_ai_inference` | **TRUNG BÌNH** | 2 Workers (GPU) | Xếp hàng xử lý ảnh tải lên từ hiện trường qua 4 màng lọc AI. |
| `queue_notifications` | **BÌNH THƯỜNG**| 4 Workers | Phát tán thông báo WebSocket, gửi Email SMTP và tin nhắn cảnh báo khẩn cấp. |
| `queue_reports_batch` | **THẤP** | 2 Workers | Tổng hợp báo cáo sản lượng tuần/tháng, kết xuất tệp PDF/Excel chứng từ. |

---

## 5. CƠ CHẾ XỬ LÝ TRÙNG LẶP & IDEMPOTENCY

1. **Khóa Định Danh Idempotency Key:** Mọi sự kiện đều gắn `event_id` duy nhất (UUIDv7).
2. **Bảng Ghi Nhận Sự Kiện Đã Xử Lý (Processed Events Log):**
```sql
CREATE TABLE processed_events (
    event_id UUID NOT NULL,
    consumer_name VARCHAR(80) NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, consumer_name)
);
```
3. Khi Celery Consumer nhận tác vụ:
   - Thực hiện kiểm tra trùng lặp: `INSERT INTO processed_events (event_id, consumer_name) VALUES (:id, :consumer) ON CONFLICT DO NOTHING`.
   - Nếu số dòng ảnh hưởng $= 0$, Task tự động thoát an toàn (No-op), đảm bảo tính toán tài chính, khối lượng và neo chuỗi khối hoàn toàn Idempotent.
