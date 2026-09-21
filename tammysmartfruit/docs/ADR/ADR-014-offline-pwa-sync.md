# ADR-014: CHIẾN LƯỢC HOẠT ĐỘNG NGOẠI TUYẾN OFFLINE-FIRST BẰNG INDEXEDDB CHO CÁC TÁC VỤ HIỆN TRƯỜNG
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-014
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Nông dân khi tác nghiệp tại các khu vườn sâu hoặc tài xế vận tải container trên các cung đường đèo có thể gặp tình trạng mất sóng di động 3G/4G. Nếu hệ thống yêu cầu kết nối Internet liên tục cho toàn bộ tính năng, trải nghiệm hiện trường sẽ bị gián đoạn.

### 2. Quyết định (Decision)
Triển khai mô hình **Offline-First PWA sử dụng IndexedDB (thông qua thư viện Dexie.js)**:
1. **Phạm vi Giới Hạn Cụ Thể (Selected Workflows Only):** Không offline toàn bộ hệ thống ERP, chỉ kích hoạt chế độ ngoại tuyến cho 4 tác vụ thực địa thiết yếu:
   - *Ghi Nhật ký Canh tác (Farm Activity Diary)*
   - *Khảo sát & Giám định Bệnh Cây (Field Inspection)*
   - *Tạo Bản nháp Thu hoạch (Harvest Draft)*
   - *Hàng đợi Tải Ảnh Hiện trường (Offline Photo Queue).*
2. **Lưu trữ Cục bộ Chuẩn Web:** Sử dụng **IndexedDB** làm bộ nhớ cục bộ chuẩn trên trình duyệt di động (Android Chrome / iOS Safari), tránh sự phức tạp quá mức của SQLite WASM + OPFS trong giai đoạn V1.
3. Tệp ảnh và dữ liệu được gắn dấu thời gian thiết bị kết hợp mã băm cục bộ (`local_sha256`). Khi có mạng trở lại, Service Worker đồng bộ hóa ngầm lên máy chủ và kích hoạt kiểm tra đối soát rủi ro.
