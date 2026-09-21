# ADR-013: KIẾN TRÚC SONG NGỮ VIỆT - ANH TOÀN DIỆN VÀ KHÔNG PHỤ THUỘC NGÔN NGỮ
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-013
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Hệ thống phục vụ cả nông dân Việt Nam tại vườn và các đối tác thương mại, hải quan quốc tế tại Mỹ, EU, Nhật Bản. Giao diện không được pha trộn ngôn ngữ, không được hard-code văn bản và cơ sở dữ liệu không được dùng chuỗi dịch làm khóa nghiệp vụ.

### 2. Quyết định (Decision)
1. **Kiến trúc Từ điển Độc lập:** 100% văn bản giao diện (Labels, Buttons, Toasts, Table Headers, Charts, Error messages) được quản lý qua các tệp từ điển JSON (`locales/vi/` và `locales/en/`).
2. **Cơ sở dữ liệu Độc lập Ngôn ngữ:** Dùng mã chuẩn hóa (VD: `variety_code = JACKFRUIT_THAI`, `status = STAGE_HARVEST`), tách riêng bảng dịch `crop_variety_translations (variety_id, locale, name)`.
3. **Backend trả về Mã Lỗi (Error Codes):** Backend chỉ trả về mã định danh chuẩn dạng JSON (VD: `{"code": "GROWING_AREA_NOT_FOUND"}`) và Frontend sẽ tự động tra cứu để hiển thị đúng ngôn ngữ của phiên người dùng.
