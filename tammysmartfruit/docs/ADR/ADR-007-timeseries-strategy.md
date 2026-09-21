# ADR-007: SỬ DỤNG EXTENSION TIMESCALEDB CHO DỮ LIỆU IOT CHUỖI THỜI GIAN
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-007
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Các trạm quan trắc vi khí hậu tại vườn mít và các thiết bị cảm biến nhiệt độ trong kho lạnh/xe container gửi về hàng triệu bản ghi đo lường (telemetry readings) mỗi tháng. Việc lưu trữ bằng bảng quan hệ CRUD thông thường sẽ làm phình to database và làm chậm các truy vấn nghiệp vụ.

### 2. Quyết định (Decision)
Tích hợp **TimescaleDB Extension** trực tiếp vào PostgreSQL:
1. Tạo Hypertable phân vùng theo thời gian 7 ngày một khối (`chunk_time_interval => INTERVAL '7 days'`).
2. Kích hoạt chính sách nén cột tự động sau 14 ngày, giảm **$90\%$ dung lượng lưu trữ đĩa**.
3. Tạo các Continuous Aggregates (Tổng hợp liên tục 5 phút / 1 giờ) để phục vụ vẽ đồ thị trên Web Dashboard tức thời mà không cần quét bảng thô.
