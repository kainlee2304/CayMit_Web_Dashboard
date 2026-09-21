# DATA TRUST & ASSURANCE ARCHITECTURE — TAM MỸ SMART FRUIT ECOSYSTEM
## MULTI-LAYER VERIFICATION, CLAIM MODEL & ANCHORING ELIGIBILITY ENGINE

> **Tài liệu Kiến trúc Độ tin cậy Dữ liệu & Chống Gian lận (Data Trust Specification)**  
> **Phiên bản:** 2.1.0-PROD  
> **Nguyên tắc cốt lõi:** Blockchain không tạo ra sự thật vật lý — Sự tin cậy được xây dựng bằng kiểm chứng đa tầng  

---

## 1. TRIẾT LÝ XÂY DỰNG ĐỘ TIN CẬY DỮ LIỆU (DATA TRUST PHILOSOPHY)

Hệ thống Tam Mỹ Smart Fruit bác bỏ hoàn toàn tư duy *"Cứ đưa dữ liệu lên Blockchain là trở thành dữ liệu thật"*. Dữ liệu thô do người dùng tự khai (`Level 0`) nếu đưa thẳng lên Blockchain chỉ làm cho dữ liệu sai khó bị sửa chữa.

Do đó, sự tin cậy được kiến tạo qua **12 Lớp Kiểm Soát Độc Lập**:
```
1. Xác thực Danh tính (Identity) 
   ➔ 2. Phân quyền Nghiệp vụ (RBAC + Data Scope) 
   ➔ 3. Dữ liệu Chủ kiểm soát (Master Data) 
   ➔ 4. Kế thừa Thượng nguồn Bắt buộc (System Inheritance) 
   ➔ 5. Đối soát Geofence Không gian (PostGIS GPS) 
   ➔ 6. Dữ liệu Môi trường Khách quan (IoT Sensors) 
   ➔ 7. Màng lọc Thị giác Khách quan (AI Guards) 
   ➔ 8. Cân bằng Khối lượng Bất biến (Mass Balance) 
   ➔ 9. Thẩm định Thực địa Chuyên gia (Human Verification) 
   ➔ 10. Phê duyệt 4 Mắt Độc lập (4-Eyes Approval) 
   ➔ 11. Chứng nhận Phòng Lab Độc lập (Independent Lab/Cert) 
   ➔ 12. Neo Dấu Vân Tay Chuỗi Khối (BlockchainAnchorEligibleEvent)
```

---

## 2. QUY TRÌNH THẨM ĐỊNH DỮ LIỆU 7 BƯỚC (7-STEP VERIFICATION PIPELINE)

```mermaid
flowchart TD
    Step1["1. CAPTURE\nTiếp nhận dữ liệu khai báo ban đầu từ Nông dân / Công nhân\n(Trạng thái: LEVEL_0_DECLARED)"] --> Step2["2. VALIDATE & NORMALIZE\nĐối soát tự động: Cấu trúc JSON, Mã Master Data, Thời gian cách ly PHI,\nKiểm tra GPS trong thửa đất PostGIS, Kiểm tra trần năng suất"]
    
    Step2 --> Step3["3. EVIDENCE ATTACHMENT\nGắn kết bằng chứng khách quan: Ảnh hiện trường (pHash),\nSố liệu vi khí hậu IoT, Kết quả quét AI Computer Vision"]
    
    Step3 --> Step4["4. RISK ASSESSMENT (Risk Engine)\nTính toán điểm rủi ro (RiskScore 0 - 100).\nNếu Risk > 60: Tự động chặn và gắn cờ cảnh báo bất thường"]
    
    Step4 --> Step5["5. HUMAN VERIFICATION\nKỹ thuật viên HTX / Chuyên viên QA Tam Mỹ kiểm tra thực địa,\nđối chiếu mẫu quả và ký xác thực điện tử (LEVEL_2_VERIFIED)"]
    
    Step5 --> Step6["6. FOUR-EYES APPROVAL (ApprovalModule)\nCấp quản lý độc lập (Khác với người tạo bản ghi) phê duyệt chính thức\n(creator_id != approver_id)"]
    
    Step6 --> Step7["7. ANCHOR ELIGIBILITY EVALUATION\nKiểm tra 5 điều kiện tiên quyết -> Phát sự kiện BlockchainAnchorEligibleEvent ->\nBlockchainModule tiếp nhận & neo lên Sổ cái"]
```

---

## 3. ĐIỀU KIỆN TIÊN QUYẾT ĐỦ ĐIỀU KIỆN NEO CHUỖI KHỐI (ANCHORING GATING CONDITIONS)

Sự kiện `BlockchainAnchorEligibleEvent` **CHỈ ĐƯỢC PHÉP PHÁT SINH** khi thỏa mãn đồng thời 100% các tiêu chuẩn sau:
1. **Chính sách Cấp độ Tin cậy Thỏa mãn (Assurance Policy Satisfied):** Bản ghi đạt mức `LEVEL_2_ORGANIZATION_VERIFIED` hoặc `LEVEL_3_INDEPENDENT_CERTIFIED` theo quy định của từng loại sự kiện.
2. **Quyết định Đánh giá Rủi ro Chấp thuận (`RiskPolicy.evaluate() == ALLOW_ANCHOR`):** Điểm rủi ro tổng hợp thỏa mãn ngưỡng chính sách đang có hiệu lực (`effective_date_aware`, `versioned`, `auditable` — ngưỡng mặc định ban đầu là $25\text{ điểm}$, nhưng có thể tùy biến theo danh mục sản phẩm).
3. **Chính sách Bằng chứng Đầy đủ (Evidence Policy Satisfied):** Đầy đủ các bằng chứng khách quan bắt buộc (Ảnh chụp hiện trường kèm pHash, Số liệu cảm biến IoT, hoặc Kết quả kiểm định AI).
4. **Xác thực Chuyên gia Hoàn tất (Verification Completed):** Đã có chữ ký số điện tử của Kỹ thuật viên nông nghiệp hoặc Chuyên viên QA có thẩm quyền.
5. **Phê duyệt 4 Mắt Độc Lập Hoàn tất (Four-Eyes Approval Completed):** Yêu cầu phê duyệt từ `ApprovalModule` được thông qua với ràng buộc bất biến $\text{creator\_id} \ne \text{approver\_id}$.
6. **Loại Sự kiện Hợp lệ (Event Type Permitted):** Sự kiện thuộc danh mục được phép neo theo cấu hình của `BlockchainAnchoringPolicy`.

---

## 4. MÔ HÌNH KHẲNG ĐỊNH DỮ LIỆU (CLAIM MODEL SCHEMA)

```sql
CREATE TABLE data_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_type VARCHAR(80) NOT NULL, -- CROP_VARIETY, AREA_PUC, PHI_SAFE, QUALITY_GRADE, BIO_SAFETY
    subject_type VARCHAR(60) NOT NULL, -- TREE_GROUP, PLOT, HARVEST_BATCH, PACKING_BATCH, PALLET
    subject_id UUID NOT NULL,
    value_code VARCHAR(80) NOT NULL, -- VD: JACKFRUIT_THAI, GRADE_A, PASSED
    value_json JSONB,
    declared_by UUID NOT NULL,
    declared_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source_type VARCHAR(60) NOT NULL, -- FARMER_DECLARATION, TECHNICIAN_INSPECTION, LAB_RESULT, AI_INFERENCE, IOT_DEVICE, CERTIFICATION_BODY
    assurance_level VARCHAR(40) NOT NULL DEFAULT 'LEVEL_0_DECLARED',
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', -- PENDING, VERIFIED, REJECTED, DISPUTED, REVOKED
    verified_by UUID,
    verified_at TIMESTAMPTZ,
    verification_method VARCHAR(80),
    approval_request_id UUID, -- Liên kết với ApprovalModule
    risk_score NUMERIC(5,2) DEFAULT 0.00,
    blockchain_proof_id UUID,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_by_claim_id UUID
);

CREATE INDEX idx_claims_subject ON data_claims(subject_type, subject_id) WHERE is_current = TRUE;
```

---

## 5. QUY TRÌNH ĐÍNH CHÍNH & KHÔNG GHI ĐÈ LỊCH SỬ (NEVER OVERWRITE)

```mermaid
stateDiagram-v2
    [*] --> VERIFIED: Đã qua thẩm định Level 2+ & Neo Blockchain
    VERIFIED --> DISPUTED: Phát hiện sai sót / Khiếu nại chất lượng
    DISPUTED --> INVESTIGATING: Hội đồng QA & Kỹ thuật mở phiên điều tra
    INVESTIGATING --> SUPERSEDED: Xác nhận có sai sót nghiệp vụ
    SUPERSEDED --> CORRECTION_RECORDED: Tạo bản ghi mới liên kết corrects_claim_id
    CORRECTION_RECORDED --> [*]: Phát BlockchainAnchorEligibleEvent neo bản ghi Đính chính
```

*Nguyên tắc bất biến:* Bản ghi ban đầu **không bao giờ bị xóa hoặc cập nhật đè**. Bảng `data_claims` áp dụng quy tắc xóa `ON DELETE RESTRICT` đối với các Claim đã được xác minh (`VERIFIED`), đảm bảo tính toàn vẹn tuyệt đối trước cơ quan thanh tra kiểm toán.
