# BUSINESS RULES SPECIFICATION - TAM MỸ SMART FRUIT ECOSYSTEM

> **Tài liệu quy tắc nghiệp vụ chuẩn (Authoritative Business Rules & Invariants)**  
> **Phiên bản:** 1.0.0-PROD  
> **Áp dụng:** Toàn bộ hệ sinh thái Tam Mỹ Smart Fruit  

---

## 1. Quy tắc Chuỗi cung ứng & Vòng đời Nông sản (Traceability & Lineage Invariants)

### 1.1. Ma trận chuyển đổi trạng thái hợp lệ (State Transition Matrix)
Vòng đời nông sản từ Nông trại đến Bàn ăn (Farm to Market) được kiểm soát qua các trạng thái tuần tự và không thể nhảy cóc:

| Trạng thái hiện tại (`current_stage`) | Trạng thái kế tiếp hợp lệ (`allowed_next_stages`) | Hành động nghiệp vụ kích hoạt (Action) |
| :--- | :--- | :--- |
| `created` *(Khởi tạo)* | `cultivation`, `harvest` | `StartCultivation()`, `PlanHarvest()` |
| `cultivation` *(Canh tác)* | `cultivation`, `harvest` | `LogActivity()`, `StartHarvest()` |
| `harvest` *(Thu hoạch)* | `processing`, `packing` | `TransferToPackhouse()`, `DirectPack()` |
| `processing` *(Sơ chế)* | `processing`, `packing`, `cold_storage` | `SortAndGrade()`, `PackOutput()` |
| `packing` *(Đóng gói)* | `packing`, `cold_storage`, `logistics` | `Palletize()`, `StoreInColdRoom()` |
| `cold_storage` *(Kho lạnh)* | `cold_storage`, `logistics` | `DispatchToCarrier()` |
| `logistics` *(Vận chuyển)* | `logistics`, `export`, `market` | `ArriveAtPort()`, `DeliverToBuyer()` |
| `export` *(Xuất khẩu)* | `export`, `market` | `CustomsClearance()`, `ExportConfirm()` |
| `market` *(Thị trường)* | *(Trạng thái kết thúc — Khóa bất biến)* | `LockBatch()` |

---

## 2. Quy tắc Data Trust & Chống Khai Gian (Anti-Fraud & Verification Rules)

### 2.1. Cấm nhập lại dữ liệu đã xác thực ở đầu nguồn (Upstream Inheritance Rule)
- Giống mít (VD: `Mít Thái Changai`, `Mít Ruột Đỏ Tam Mỹ`), mã vùng trồng (PUC), tọa độ ranh giới thửa đất (Plot Geofence) sau khi được Kỹ thuật viên thẩm định ở `Assurance Level 2+` sẽ tự động kế thừa xuống các khâu thu hoạch, sơ chế, đóng gói, vận chuyển.
- Tuyệt đối không cho phép bất kỳ nhân viên trung gian nào sửa đổi tên giống hoặc vùng xuất xứ.

### 2.2. Quy tắc 4 Cấp độ Khẳng định Dữ liệu (Assurance Level Rules)
- **LEVEL 0 (Declared):** Dữ liệu do người dùng tự khai (nông dân khai lần đầu). Chưa có giá trị pháp lý cao.
- **LEVEL 1 (System Validated):** Hệ thống tự động đối soát Geofence GPS, thời gian cách ly PHI, hạn sử dụng vật tư và sản lượng tối đa của vườn.
- **LEVEL 2 (Organization Verified):** Kỹ thuật viên HTX / Chuyên viên QA Tam Mỹ khảo sát thực địa, kiểm tra mẫu và ký duyệt điện tử.
- **LEVEL 3 (Independent Certified):** Có kết quả kiểm nghiệm của Phòng Lab độc lập hoặc chứng nhận của Tổ chức cấp chứng chỉ (SGS, Eurofins, Cục BVTV).

### 2.3. Pipeline Neo Chuỗi khối Chọn lọc (Blockchain Anchoring Pipeline)
- Dữ liệu thô do người dùng tự khai (`Level 0`) **tuyệt đối không được neo lên Blockchain**.
- Chỉ neo các sự kiện nghiệp vụ đã qua thẩm định và phê duyệt (`Level 2+`):
$$\text{Capture} \rightarrow \text{Validate} \rightarrow \text{Evidence} \rightarrow \text{Risk Assessment} \rightarrow \text{Verification} \rightarrow \text{Approval} \rightarrow \text{Blockchain Anchor}$$

---

## 3. Quy tắc Cân bằng Khối lượng (Mass Balance Invariant)

Tại bất kỳ công đoạn biến đổi vật lý nào (Thu hoạch ➔ Sơ chế ➔ Đóng gói ➔ Kho lạnh ➔ Xuất khẩu), hệ thống bắt buộc kiểm tra nguyên tắc bảo toàn hai chiều:

$$\left| \text{Total Valid Input} - (\text{Total Output} + \text{Total Documented Loss} + \text{Total Reject}) \right| \le \text{Total Valid Input} \times \text{Configured\_Tolerance}$$

- **Dung sai cấu hình (`Configured_Tolerance`)**: Được cấu hình và phiên bản hóa theo danh mục sản phẩm (Mặc định ban đầu cho Mít tươi là $\mathbf{1.5\%}$).
- **Xử lý vi phạm**: Nếu chênh lệch vượt quá dung sai:
  - Hệ thống tự động gắn cờ `MASS_BALANCE_VIOLATION_ALERT` và khóa quyền xuất xưởng của lô.
  - Bắt buộc lập biên bản giải trình có chữ ký 4 mắt của Trưởng xưởng sơ chế và Chuyên viên QA Lead trước khi mở khóa.

---

## 4. Danh mục Vai trò Chuẩn tắc (Canonical Role Codes)

Mọi phân quyền nghiệp vụ và xác thực JWT bắt buộc dùng mã định danh chuẩn tắc (không dùng văn bản hiển thị):
1. `admin_hq`: Quản trị viên cấp cao Tổng công ty Tam Mỹ.
2. `technician`: Cán bộ Kỹ thuật Nông nghiệp vùng trồng / Hợp tác xã.
3. `farmer`: Nông hộ / Xã viên canh tác trực tiếp.
4. `packhouse_lead`: Trưởng xưởng Sơ chế & Cơ sở Đóng gói.
5. `qa_qc`: Chuyên viên Kiểm soát Chất lượng & An toàn thực phẩm.
6. `warehouse_keeper`: Thủ kho Bảo quản & Kho lạnh WMS.
7. `logistics_driver`: Tài xế Vận tải & Điều phối Đội xe lạnh.
8. `export_officer`: Chuyên viên Hồ sơ Xuất khẩu & Thủ tục Hải quan.
9. `auditor_inspector`: Thanh tra Độc lập / Tổ chức Cấp Chứng chỉ.
10. `buyer_partner`: Đối tác Thu mua Quốc tế & Chuỗi Phân phối B2B.
11. `system_worker`: Tiến trình Hệ thống Nền (Background Worker / Job Engine).

---

## 5. Quy tắc Bảo vệ Thương hiệu Tam Mỹ (Brand Protection Rules)

- Nhãn hiệu độc quyền **"Tam Mỹ Smart Fruit Premium"** chỉ được áp dụng khi thỏa mãn 100% các tiêu chí:
  1. Trái mít đạt phân hạng **Grade A** (Trọng lượng từ 9kg - 15kg, hình thái cân đối, không nứt nẻ).
  2. Vùng trồng có chứng nhận `VietGAP` hoặc `GlobalGAP` còn hiệu lực.
  3. Điểm đánh giá AI Computer Vision $> 90\%$ xác nhận không nhiễm sâu đục trái, nấm hồng hay thối nhũn.
  4. Đã qua xử lý kiểm soát chất lượng tại cơ sở đóng gói được Tam Mỹ chứng nhận.
  5. Toàn bộ nguyên liệu đầu vào trong lô sơ chế/đóng gói phải thuộc cùng một giống mít thuần chủng (`JACKFRUIT_THAI` hoặc `JACKFRUIT_RED`).

---

## 6. Quy tắc Phê duyệt 4 Mắt & Đính chính Lịch sử (Immutability & Correction)

1. **Nguyên tắc 4 Mắt (4-Eyes Principle):** Người tạo dữ liệu không được phép tự phê duyệt dữ liệu của mình. Mọi quyết định xuất kho, nghiệm thu thu hoạch, duyệt chứng chỉ đều bắt buộc có 2 cá nhân độc lập tham gia.
2. **Quy tắc Đính chính (Never Overwrite History):** Tuyệt đối không xóa hoặc ghi đè bản ghi đã được duyệt hoặc neo Blockchain. Mọi đính chính phải tạo bản ghi mới mang trạng thái `CORRECTION` liên kết với bản ghi cũ (`SUPERSEDED`), lưu đầy đủ lý do, chữ ký và dấu vết kiểm toán (`audit_logs`).
