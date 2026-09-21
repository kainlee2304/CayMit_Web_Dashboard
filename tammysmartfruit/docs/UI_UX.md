# UI/UX DESIGN SYSTEM & SPECIFICATION - TAM MỸ SMART FRUIT ECOSYSTEM

Tài liệu này xác định toàn bộ hệ thống thiết kế (Design System), bảng màu nhận diện, typography, thành phần giao diện và quy chuẩn trải nghiệm người dùng theo đúng chỉ dẫn của **`MASTER_SPEC.md`** và **`AGENTS.md`**.

---

## 1. Nguyên tắc Thiết kế Cốt lõi (Core UX Principles)

1. **Thân thiện với Nông dân & Hiện trường (Farmer-First & Field Usability):**
   - Nút bấm lớn (Touch Target $\ge 48\text{px}$), khoảng cách rộng, thao tác 1 chạm dễ dàng ngoài vườn nắng gắt.
   - Hỗ trợ chế độ Offline-first và tối ưu hóa đường truyền mạng 3G/4G yếu.
2. **Chuẩn mực Thương hiệu Cao cấp:**
   - **Màu thương hiệu chủ đạo (Primary Brand Color):** `#2F8F3A` (Xanh nông nghiệp Tam Mỹ).
   - **Phông chữ chuẩn (Standard Typography):** `Be Vietnam Pro` (Hiển thị dấu tiếng Việt và chữ tiếng Anh hoàn hảo, sắc nét).
3. **Kiến trúc Song ngữ Độc lập (100% Bilingual VI / EN):**
   - Không pha trộn tiếng Việt và tiếng Anh trên cùng một màn hình.
   - Toàn bộ Text đều qua hàm dịch `{t("namespace.key")}`.

---

## 2. Bảng Màu Chuẩn (Color System & Tokens)

### 2.1. Màu Thương hiệu (Brand Colors)
- **Primary Brand:** `#2F8F3A` (Tam Mỹ Leaf Green) — Nút bấm chính, viền active, icon thương hiệu.
- **Primary Hover/Active:** `#26732E` / `#38A845`.
- **Primary Subdued/Tint:** `rgba(47, 143, 58, 0.12)` — Nền badge, vùng chọn, card highlight.

### 2.2. Màu Nền & Bề mặt (Surface & Neutral Tokens)
- **Dark Mode Background:** `#0B0F17` (Deep Night).
- **Dark Mode Card Surface:** `#131B26` với viền `#1E293B`.
- **Light Mode Background:** `#F8FAFC` (Clean Gray).
- **Light Mode Card Surface:** `#FFFFFF` với viền `#E2E8F0`.

### 2.3. Màu Nhận diện Trạng thái & Sâu bệnh (Domain Status Colors)

| Mã trạng thái / Loại bệnh | Mã màu Hex | Ý nghĩa |
| :--- | :--- | :--- |
| **Khỏe mạnh / Hoàn tất (`HEALTHY` / `COMPLETED`)** | `#2F8F3A` | Đạt chuẩn xuất khẩu, cây sinh trưởng tốt |
| **Cảnh báo rủi ro / Chờ duyệt (`PENDING` / `WARNING`)** | `#F59E0B` | Cần kỹ thuật viên kiểm tra thực địa |
| **Nguy hiểm / Bác bỏ / Lỗi (`REJECTED` / `CRITICAL`)** | `#EF4444` | Phát hiện sâu đục trái, nứt thân, gãy chuỗi SHA-256 |
| **Sâu đục thân (`batocera_rufomaculata`)** | `#8B5CF6` | Cảnh báo sâu đục mô thân cành |
| **Nấm hồng (`pink_disease`)** | `#EC4899` | Bệnh nấm phát tán mùa mưa |
| **Nứt thân chảy nhựa (`stem_cracking`)** | `#F97316` | Bệnh xì mủ thân cây |
| **Ngoài phạm vi (`not_jackfruit`)** | `#64748B` | Vật thể lạ không thuộc hệ sinh thái mít |

---

## 3. Hệ thống Typography (Typography Hierarchy)

- **Font Family:** `Be Vietnam Pro`, `system-ui`, `-apple-system`, `sans-serif`.
- **Monospace (Dành cho mã băm SHA-256, Mã QR & SSCC):** `ui-monospace`, `SFMono-Regular`, `Menlo`, `monospace`.
- **Cỡ chữ & Trọng lượng:**
  - `Display / H1`: `2.25rem (36px)`, Bold (700/800), Line height 1.2.
  - `H2 / Section Title`: `1.5rem (24px)`, SemiBold (600), Line height 1.3.
  - `H3 / Card Title`: `1.125rem (18px)`, SemiBold (600).
  - `Body Standard`: `0.9375rem (15px)`, Regular (400), Line height 1.6.
  - `Caption / Badge`: `0.75rem (12px)`, Medium (500), Tracking 0.05em.

---

## 4. Cấu trúc Thành phần Giao diện Chuẩn (UI Components)

1. **Sidebar Phân quyền Thông minh (Dynamic Role-based Navigation):** Tự động lọc menu hiển thị theo quyền của User (`farmer`, `technician`, `packhouse_lead`, `qa_qc`, `admin_hq`).
2. **Bộ thẻ Chỉ số Vận hành (KPI Stat Cards):** Hiển thị sản lượng thu hoạch, nhiệt độ kho lạnh, tỷ lệ trái loại 1 kèm biểu đồ mini (Sparkline).
3. **Trình kéo thả Giám định AI (AI Vision Upload & Dropzone):** Kèm camera live stream và thanh trượt trực quan thể hiện điểm tin cậy %.
4. **Dòng thời gian Chuỗi khối (Cryptographic DAG Timeline):** Thể hiện chuỗi khối dọc với đường line nối xanh `#2F8F3A`, con dấu thời gian UTC, người thực hiện và nút sao chép mã băm SHA-256.
5. **Tem QR Xuất khẩu (Export QR Label Generator):** Hỗ trợ in chuẩn kích thước tem dán thùng Carton và mã SSCC dán trên Pallet.
