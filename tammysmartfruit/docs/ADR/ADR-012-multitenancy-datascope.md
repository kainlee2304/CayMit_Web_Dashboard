# ADR-012: THIẾT KẾ ĐA TỔ CHỨC VÀ BẢO VỆ DỮ LIỆU BẰNG DATA SCOPE TRÊN BACKEND
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-012
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Nhiều tổ chức khác nhau (Tam Mỹ HQ, các Hợp tác xã, Doanh nghiệp đóng gói, Nhà xe, Đơn vị chứng nhận) cùng hoạt động trên một hệ thống. Tuyệt đối không được để lộ dữ liệu bí mật kinh doanh giữa các tổ chức đối thủ, và không cho phép người dùng can thiệp sửa tham số `organization_id` trên API để xem trộm dữ liệu.

### 2. Quyết định (Decision)
1. **Mô hình Dữ liệu Đa tổ chức:** Mọi bảng nghiệp vụ đều bắt buộc có cột `organization_id NOT NULL`.
2. **Ép Buộc Phân Quyền trên Backend (Backend-Enforced Data Scope):**
   - Trích xuất định danh và phạm vi quyền (`OWN`, `ASSIGNED`, `COOPERATIVE`, `ORGANIZATION`, `ALL`) từ Token JWT đã xác thực.
   - Tự động chèn điều kiện lọc `WHERE organization_id = :current_user_org_id` ở tầng Application Services/Repositories, bất kể Frontend truyền tham số gì.
