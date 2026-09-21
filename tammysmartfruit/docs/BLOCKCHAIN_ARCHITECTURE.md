# BLOCKCHAIN & CRYPTOGRAPHIC LEDGER ARCHITECTURE — TAM MỸ SMART FRUIT ECOSYSTEM
## ADAPTER INTERFACE, LEDGER OPTIONS EVALUATION & SELECTIVE ANCHORING

> **Tài liệu Kiến trúc Chuỗi khối & Sổ cái Bất biến (Blockchain Specification)**  
> **Phiên bản:** 2.1.0-PROD  
> **Nguyên tắc cốt lõi:** Phân định rõ Sổ cái băm nội bộ vs. Mạng Blockchain phân tán — Trừu tượng hóa qua Adapter Interface  

---

## 1. PHÂN BIỆT THUẬT NGỮ CỐT LÕI (BLOCKCHAIN TERMINOLOGY CLARITY)

1. **Sổ cái băm mật mã học nội bộ (Internal Tamper-Evident Hash-Chain):**
   - Cơ chế liên kết các bản ghi trong cơ sở dữ liệu quan hệ bằng mã băm `SHA-256` tuần tự (`current_hash = SHA256(canonical_payload + previous_hash)`).
   - Tác dụng: Phát hiện ngay lập tức bất kỳ sự can thiệp / chỉnh sửa trái phép nào vào dữ liệu trong database nội bộ.
   - **Lưu ý:** Đây **không phải là mạng lưới Blockchain phân tán** (Distributed Ledger), vì dữ liệu vẫn nằm trên máy chủ cơ sở dữ liệu nội bộ.
2. **Mạng lưới Chuỗi khối phân tán (Actual Distributed Blockchain Network):**
   - Mạng lưới có nhiều nút đồng thuận độc lập bên ngoài (Consensus Nodes), dữ liệu neo không thể bị đảo ngược bởi bất kỳ quản trị viên cơ sở dữ liệu đơn lẻ nào.
   - Tác dụng: Cung cấp bằng chứng pháp lý độc lập (Non-repudiation) trước khách hàng quốc tế, hải quan và tổ chức chứng nhận.

---

## 2. GIAO DIỆN HỢP ĐỒNG BLOCKCHAIN ADAPTER (BLOCKCHAIN ADAPTER INTERFACE)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AnchorProofRequest(BaseModel):
    batch_id: str
    merkle_root: str
    event_count: int
    canonical_payload_summary: Dict[str, Any]
    timestamp: str

class BlockchainProofResponse(BaseModel):
    network_name: str
    transaction_hash: str
    block_number: int
    merkle_root: str
    contract_address: Optional[str]
    anchored_at: str
    status: str # SUCCESS, PENDING, FAILED

class IBlockchainAdapter(ABC):
    @abstractmethod
    async def anchor_batch(self, request: AnchorProofRequest) -> BlockchainProofResponse:
        """Gửi mã gốc Merkle Root của lô sự kiện lên mạng lưới chuỗi khối."""
        pass

    @abstractmethod
    async def verify_proof(self, transaction_hash: str, merkle_root: str) -> bool:
        """Xác minh tính hợp lệ và sự tồn tại của giao dịch trên chuỗi khối."""
        pass

    @abstractmethod
    async def get_network_status(self) -> Dict[str, Any]:
        """Kiểm tra tình trạng hoạt động và độ trễ của nút mạng."""
        pass
```

---

## 3. CHÍNH SÁCH NEO CHỌN LỌC (SELECTIVE ANCHORING POLICY)

1. **Sự kiện Kích hoạt:** `BlockchainModule` **CHỈ LẮNG NGHE DUY NHẤT** sự kiện `BlockchainAnchorEligibleEvent` phát ra từ `DataTrustModule`.
2. **Quy trình Gom nhóm Merkle Tree (Batch Anchoring):**
   - Định kỳ mỗi 1 giờ (hoặc khi gom đủ 500 sự kiện), Celery Worker gom nhóm các mã băm `canonical_data_hash` lại.
   - Xây dựng cây Merkle (Merkle Tree) và tính toán mã đỉnh `Merkle Root`.
   - Gửi 1 giao dịch duy nhất lên mạng Ethereum Layer 2 (Polygon / Arbitrum) qua `IBlockchainAdapter`.
   - Tiết kiệm **$99.9\%$ chi phí giao dịch** và bảo vệ 100% bí mật kinh doanh của chuỗi cung ứng.
