# SECURITY & MULTI-TENANCY ARCHITECTURE — TAM MỸ SMART FRUIT ECOSYSTEM
## AUTHENTICATION, DATA SCOPE ENFORCEMENT & CRYPTOGRAPHIC CONTROLS

> **Tài liệu Kiến trúc An toàn & Bảo mật Thông tin (Security Specification)**  
> **Phiên bản:** 2.1.0-PROD  
> **Nguyên tắc cốt lõi:** Zero Trust — Backend Enforced Authorization — Multi-Tenant Data Isolation  

---

## 1. MÔ HÌNH XÁC THỰC DANH TÍNH & MẬT MÃ HỌC (AUTHENTICATION & CRYPTO CONTROLS)

Hệ thống phân định rạch ròi giữa các cơ chế mật mã học, không gây nhầm lẫn thuật ngữ:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. BĂM MẬT KHẨU (PASSWORD HASHING & MIGRATION REHASH STRATEGY)                         │
│ - Mật khẩu Mới / Đổi Mật khẩu: Bắt buộc dùng `Argon2id` (Memory: 64MB, Iterations: 3,  │
│   Parallelism: 4) theo chuẩn OWASP Password Storage Guidelines.                        │
│ - Mật khẩu Legacy (Từ CSDL cũ chuyển đổi): Hỗ trợ kiểm tra bằng `PBKDF2-HMAC-SHA256`   │
│   (210,000 vòng lặp).                                                                  │
│ - Tự động Tái Băm (Automatic Rehash on Login): Ngay khi User đăng nhập thành công với   │
│   mật khẩu PBKDF2 cũ, hệ thống tự động băm lại bằng Argon2id và cập nhật vào CSDL.     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. KÝ SỐ TOKEN TRUY CẬP (ASYMMETRIC JWT RS256 SIGNING)                                 │
│ - Thuật toán: JWT `RS256` (Cặp khóa Bất đối xứng RSA 2048-bit).                        │
│ - Quản lý Khóa Bí mật: Private Key được nạp an toàn từ Biến Môi trường / Vault KMS     │
│   (TUYỆT ĐỐI KHÔNG lưu trong Application Database).                                    │
│ - Phân phối Public Key: Public Key được chia sẻ cho các Trusted Services / Nginx Gateway│
│   để tự động giải mã và xác thực token mà không cần gọi ngược về Auth Service.         │
│ - Thời hạn hiệu lực: Ngắn hạn (TTL = 30 phút).                                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. QUẢN LÝ REFRESH TOKEN (OPAQUE TOKEN ROTATION & REVOCATION)                          │
│ - Chuỗi Refresh Token ngẫu nhiên (CSPRNG 256-bit) được băm SHA-256 trước khi lưu vào   │
│   Redis (TTL = 14 ngày). Server KHÔNG lưu chuỗi gốc, chỉ lưu mã băm SHA-256.          │
│ - Cơ chế Xoay vòng (Rotation): Mỗi lần cấp Access Token mới sẽ sinh Refresh Token mới. │
│ - Phát hiện Tái sử dụng (Reuse Detection): Nếu một Refresh Token cũ bị sử dụng lại,    │
│   toàn bộ phiên của họ (Token Family) sẽ bị thu hồi ngay lập tức.                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. MÃ TRUY XUẤT CÔNG KHAI (PUBLIC TRACE TOKENS)                                        │
│ - Tem mã QR `/t/{trace_code}` sử dụng chuỗi ngẫu nhiên mật mã học (CSPRNG 128-bit)     │
│   được sinh độc lập hoàn toàn với khóa chính nội bộ UUIDv7.                            │
│ - UUIDv7 được sử dụng trong CSDL vì tính năng sắp xếp thời gian và tối ưu chỉ mục B-Tree│
│   (Index Locality), KHÔNG PHẢI là cơ chế bảo vệ quyền riêng tư hay bảo mật.            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. KIẾN TRÚC PHÂN QUYỀN ĐA TỔ CHỨC & PHẠM VI DỮ LIỆU (DATA SCOPE ENFORCEMENT)

Hệ thống bảo vệ dữ liệu ở tầng Backend bằng mô hình **3 Chiều (Resource + Action + Data Scope)**:

```python
class DataScope(str, Enum):
    OWN = "OWN"                     # Chỉ dữ liệu do chính User tạo ra (VD: Nông dân chỉ xem Plot của mình)
    ASSIGNED = "ASSIGNED"           # Dữ liệu được phân công phụ trách (VD: Kỹ thuật viên phụ trách 5 vườn)
    COOPERATIVE = "COOPERATIVE"     # Toàn bộ dữ liệu thuộc phạm vi Hợp tác xã
    ORGANIZATION = "ORGANIZATION"   # Toàn bộ dữ liệu thuộc Doanh nghiệp/Nhà máy sở hữu
    ALL = "ALL"                     # Toàn quyền hệ sinh thái (Chỉ dành cho admin_hq)

def enforce_data_scope(query, user_context, entity_model):
    """Tự động chèn bộ lọc phạm vi dữ liệu vào câu truy vấn SQL SQLAlchemy trên Backend"""
    if user_context.scope == DataScope.ALL:
        return query
    elif user_context.scope == DataScope.ORGANIZATION:
        return query.filter(entity_model.organization_id == user_context.org_id)
    elif user_context.scope == DataScope.OWN:
        return query.filter(entity_model.created_by == user_context.user_id)
    # Ngăn chặn hoàn toàn việc User truyền organization_id giả mạo trên URL/Body
```

---

## 3. MA TRẬN PHÂN QUYỀN 11 VAI TRÒ CHUẨN TẮC (CANONICAL RBAC MATRIX)

| Mã Vai Trò (`canonical_role`) | Tài Nguyên Được Phép Thao Tác | Hành Động Hợp Lệ (`Action`) | Phạm Vi Mặc Định (`Data Scope`) |
| :--- | :--- | :--- | :--- |
| **`admin_hq`** | Toàn bộ tài nguyên hệ sinh thái | Create, Read, Update, Delete, Approve, Config | `ALL` |
| **`technician`** | Vùng trồng, Thửa đất, Mùa vụ, Bệnh hại | Verify, Survey, ApproveSeason, Recommend | `COOPERATIVE` / `ASSIGNED` |
| **`farmer`** | Thửa đất của mình, Nhật ký, Thu hoạch | Create, Read, SubmitHarvest, LogActivity | `OWN` |
| **`packhouse_lead`**| Lô sơ chế, Đóng gói, Carton, Pallet, Tem QR | Transform, Pack, GenerateQR, Dispatch | `ORGANIZATION` |
| **`qa_qc`** | Kiểm định Brix, Quét AI, Phê duyệt xuất | ApproveQC, RejectLot, HoldQuarantine | `ORGANIZATION` |
| **`warehouse_keeper`**| Kho lạnh, Kệ lưu trữ, Tồn kho Pallet | ReceiveStock, MoveBin, DispatchStock | `ORGANIZATION` |
| **`logistics_driver`**| Vận đơn, Checkpoints, Nhiệt độ xe lạnh | UpdateCheckpoint, SignDelivery | `ASSIGNED` |
| **`export_officer`** | Hồ sơ xuất khẩu, Hải quan, Hóa đơn | CompileDossier, ConfirmCustoms | `ORGANIZATION` |
| **`auditor_inspector`**| Hồ sơ truy xuất, Báo cáo, Chứng chỉ | ReadOnly, Inspect, Certify | `ALL` (Read-Only) |
| **`buyer_partner`** | Lô hàng đặt mua, Chứng chỉ xuất xứ | ReadPurchasedLots, ConfirmReceived | `ASSIGNED` (Read-Only) |
| **`system_worker`** | Outbox, Blockchain Anchor, IoT Telemetry | AutoProcess, Ingest, AnchorMerkle | `ALL` (Internal Service) |
