# ADR-010: TRỪU TƯỢNG HÓA KẾT NỐI CHUỖI KHỐI BẰNG BLOCKCHAIN ADAPTER
## ARCHITECTURE DECISION RECORD — TAM MỸ SMART FRUIT ECOSYSTEM

- **Mã định danh:** ADR-010
- **Trạng thái:** ACCEPTED (Đã phê duyệt)
- **Ngày quyết định:** 28/08/2026

### 1. Ngữ cảnh (Context)
Công nghệ Blockchain phát triển nhanh chóng và có nhiều mạng lưới khác nhau (Ethereum L2, Quorum, Hyperledger Fabric). Nếu gắn chặt code nghiệp vụ vào SDK của một nhà cung cấp cụ thể, hệ thống sẽ bị Vendor Lock-in và khó nâng cấp.

### 2. Quyết định (Decision)
Định nghĩa giao diện chuẩn **`BlockchainAdapter`** tại tầng Domain Infrastructure:
1. Nghiệp vụ chuỗi cung ứng chỉ giao tiếp với `IBlockchainAdapter.anchor_batch()` và `IBlockchainAdapter.verify_proof()`.
2. Áp dụng chiến lược **Dual-Ledger**:
   - V1: Kết hợp Sổ cái băm SHA-256 nội bộ với Adapter neo Merkle Root lên mạng lưới **Ethereum Layer 2 (Polygon / Arbitrum)**.
   - V2+: Có thể cắm thêm Adapter mạng doanh nghiệp (Permissioned Quorum / Hyperledger) mà không sửa đổi một dòng code nghiệp vụ nào.
