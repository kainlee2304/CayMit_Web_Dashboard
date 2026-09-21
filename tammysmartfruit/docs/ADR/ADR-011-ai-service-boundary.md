# ADR-011: PHÂN LẬP DỊCH VỤ SUY LUẬN AI VÀ QUY TRÌNH 4 MÀNG LỌC
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-011
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Các mô hình AI Computer Vision (YOLOv11, ViT-100, EfficientNet) tiêu thụ tài nguyên GPU/CPU rất lớn và có thể gặp hiện tượng phân loại sai (Dương tính giả) khi người dùng chụp ảnh các vật thể không phải quả mít (xe cộ, đồ đạc, trái cây khác).

### 2. Quyết định (Decision)
1. **Phân lập Dịch vụ AI (AI Service Boundary):** Chạy phân hệ AI trên một Container riêng biệt (`tammy-ai-engine`) có gắn GPU, giao tiếp với Core API qua mạng nội bộ.
2. **Thiết lập 4 Màng Lọc Nghiêm Ngặt:** Bắt buộc ảnh đi tuần tự qua: *General Object Filter (Layer 1)* ➔ *ImageNet Pattern Guard (Layer 2)* ➔ *ViT 100-Fruit Identity Classifier (Layer 3)* ➔ *Mô hình Bệnh Cây/Quả chuyên sâu (Layer 4)*.
3. Kết quả AI chỉ mang tính chất Bằng chứng tham vấn (`Evidence / Risk Signal`), không được tự động trở thành phán quyết trạng thái cuối cùng.
