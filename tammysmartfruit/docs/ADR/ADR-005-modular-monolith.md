# ADR-005: CHỌN KIẾN TRÚC MODULAR MONOLITH CHO GIAI ĐOẠN ĐẦU
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-005
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Hệ thống Tam Mỹ Smart Fruit có nhiều phân hệ nghiệp vụ đan xen phức tạp (Nông nghiệp, Thu hoạch, Sơ chế, Đóng gói, Kho lạnh, Logistics, Xuất khẩu, AI, IoT, Blockchain). Đội ngũ cần quyết định giữa hai mô hình kiến trúc: **Microservices phân tán** hoặc **Modular Monolith**.

### 2. Các phương án đánh giá (Options)
- **Phương án A (Microservices):** Chia nhỏ hệ thống thành 10+ dịch vụ độc lập với database riêng, giao tiếp qua gRPC / Kafka.
- **Phương án B (Modular Monolith - Được chọn):** Đóng gói toàn bộ 32 modules trong một ứng dụng duy nhất, phân định ranh giới nghiêm ngặt qua Public Services và Domain Events nội bộ, dùng chung 1 PostgreSQL database.

### 3. Quyết định (Decision) & Lý do
**Chọn Phương án B (Modular Monolith)** vì:
1. Giảm thiểu chi phí hạ tầng và độ phức tạp DevOps trong giai đoạn đầu.
2. Cho phép thực hiện các giao dịch ACID nội bộ (Transactional Outbox, Mass Balance) một cách an toàn và nhất quán, tránh được bài toán Distributed Transactions (Saga / 2PC) phức tạp.
3. Vẫn đảm bảo tính module hóa cao, sẵn sàng tách nhỏ thành Microservice trong tương lai nếu một module cụ thể phát sinh nhu cầu scale độc lập.
