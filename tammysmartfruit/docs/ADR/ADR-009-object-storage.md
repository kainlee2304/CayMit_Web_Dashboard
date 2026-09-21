# ADR-009: CHIẾN LƯỢC LƯU TRỮ TỆP TIN ĐA PHƯƠNG TIỆN BẰNG OBJECT STORAGE
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-009
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Hệ thống xử lý lượng lớn hình ảnh chụp thực địa, video camera giám sát, chứng nhận PDF và tem mã QR độ phân giải cao. Tuyệt đối không lưu dữ liệu nhị phân (Binary BLOB) trực tiếp vào PostgreSQL hay lưu trữ phân tán cục bộ trên ổ cứng máy chủ gây khó khăn khi scale.

### 2. Quyết định (Decision)
Trừu tượng hóa việc lưu trữ qua giao diện **S3-Compatible Object Storage (MinIO On-Premise / AWS S3 Cloud)**:
1. Cơ sở dữ liệu chỉ lưu trữ Metadata: `storage_key`, `file_hash (SHA-256)`, `mime_type`, `size_bytes`.
2. Ứng dụng Client tải ảnh lên và tải về qua **Presigned Upload/Download URLs** có thời hạn bảo mật (TTL 15 phút), giảm tải băng thông cho máy chủ Backend API.
3. Kích hoạt tính năng Bucket Versioning để bảo vệ dữ liệu bằng chứng không bị ghi đè hoặc xóa nhầm.
