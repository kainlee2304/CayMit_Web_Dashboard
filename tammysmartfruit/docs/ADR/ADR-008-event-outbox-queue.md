# ADR-008: ÁP DỤNG TRANSACTIONAL OUTBOX PATTERN VÀ CELERY + REDIS QUEUE
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-008
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Khi một sự kiện quan trọng xảy ra (ví dụ: Phê duyệt Lô thu hoạch), hệ thống vừa phải cập nhật cơ sở dữ liệu, vừa phải cập nhật đồ thị DAG Traceability, gửi thông báo và xếp hàng tác vụ neo Blockchain. Nếu gọi trực tiếp Blockchain hoặc dịch vụ ngoài trong Database Transaction, giao dịch sẽ bị treo hoặc không nhất quán nếu mạng lỗi.

### 2. Quyết định (Decision)
Chuẩn hóa kiến trúc xử lý bất đồng bộ sử dụng **Transactional Outbox Pattern kết hợp Celery 5.3+ và Redis 7**:
1. Trong cùng một ACID Transaction của PostgreSQL, ghi bản ghi trạng thái nghiệp vụ và đồng thời `INSERT` sự kiện vào bảng `outbox_events`.
2. Áp dụng cơ chế **Lease Recovery** (`locked_at`, `lease_timeout = 5 minutes`) với kỹ thuật `FOR UPDATE SKIP LOCKED` để giải cứu các sự kiện bị kẹt nếu Worker gặp sự cố.
3. Sử dụng **Celery** làm Worker Runtime và **Redis 7** làm Message Broker, phân chia 5 kênh hàng đợi chuyên biệt.
4. Đảm bảo nguyên tắc At-Least-Once Delivery kết hợp Idempotency Key (bảng `processed_events`) để không bao giờ bị trùng lặp giao dịch.
