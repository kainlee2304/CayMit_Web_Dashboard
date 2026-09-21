# ADR-006: SỬ DỤNG POSTGRESQL VÀ POSTGIS CHO DỮ LIỆU ĐỊA KHÔNG GIAN
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-006
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Nghiệp vụ quản lý vùng trồng xuất khẩu (PUC), nông trại và các thửa đất canh tác đòi hỏi lưu trữ ranh giới đa giác (Polygons) và tính toán kiểm tra điểm chụp ảnh ngoài thực địa có nằm trong thửa đất hay không (Point-in-Polygon Geofence Validation).

### 2. Quyết định (Decision)
Sử dụng **PostgreSQL 16 kết hợp Extension PostGIS**:
1. Kiểu dữ liệu `GEOMETRY(Polygon, 4326)` và `GEOMETRY(Point, 4326)` cho phép lưu trữ chuẩn hệ tọa độ WGS84.
2. Hàm không gian `ST_Contains` và `ST_Distance` được tối ưu hóa qua chỉ mục R-Tree (GIST Index), cho phép đối soát Geofence với thời gian dưới $5\text{ms}$.
3. Loại bỏ hoàn toàn việc lưu trữ tọa độ dưới dạng chuỗi văn bản thuần (Plain Text JSON) gây rủi ro sai sót và không thể truy vấn không gian.
