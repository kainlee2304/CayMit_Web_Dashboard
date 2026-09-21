# TRACEABILITY & LINEAGE DAG ARCHITECTURE — TAM MỸ SMART FRUIT ECOSYSTEM
## EVENT-DERIVED READ PROJECTION, SPLIT/MERGE LINEAGE & RECALL ENGINE

> **Tài liệu Kiến trúc Đồ thị Truy xuất Nguồn gốc (Traceability Specification)**  
> **Phiên bản:** 2.1.0-PROD  
> **Nguyên tắc cốt lõi:** Đồ thị DAG là Read-Optimized Projection sinh từ Domain Events — Có thể tái xây dựng (Rebuildable) — Bảo toàn phả hệ 100%  

---

## 1. NGUYÊN TẮC THIẾT KẾ ĐỒ THỊ TRUY XUẤT (TRACEABILITY ARCHITECTURE PRINCIPLES)

1. **Phân định Rõ ràng Nguồn Sự Thật vs. Bản Chiếu Đọc:**
   - **Nguồn Sự Thật Bền Vững (Durable Source of Truth):** Bảng `domain_event_history` lưu trữ các sự kiện miền bất biến được phát sinh từ các Aggregate Roots (`HarvestBatch`, `ProcessingBatch`, `PackingBatch`, `Shipment`). Bảng này là Append-Only, không bao giờ bị xóa.
   - **Bản Chiếu Đồ thị Tối Ưu Đọc (Traceability DAG Projection):** Là cấu trúc bảng `trace_nodes` và `trace_edges` được tạo tự động bởi `TraceabilityModule` thông qua việc tiêu thụ Domain Events:
     $$\text{domain\_event\_history} \longrightarrow \text{trace\_nodes} \longrightarrow \text{trace\_edges} \longrightarrow \text{Public / Internal Projections}$$
   - **Khả năng Tái Xây Dựng (Rebuildable Projection):** Nếu bản chiếu cần hiệu chỉnh hoặc nâng cấp thuật toán, hệ thống có thể Replay toàn bộ sự kiện từ `domain_event_history` để tái tạo 100% đồ thị DAG.
2. **Không Khóa Đồ thị Khổng lồ Trong Một Giao dịch:** Các nút và cạnh được thêm từng bước theo từng sự kiện cục bộ, không biến toàn bộ chuỗi cung ứng thành một Aggregate Root đơn lẻ gây nghẽn database.

---

## 2. CẤU TRÚC BẢNG NÚT & CẠNH ĐỒ THỊ TRUY XUẤT (PROJECTION SCHEMA)

```sql
-- Bảng các Nút trong Đồ thị Truy xuất (Trace Nodes Projection)
CREATE TABLE trace_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(60) NOT NULL, -- PLOT, SEASON, HARVEST_BATCH, PROCESSING_BATCH, CARTON, PALLET, SHIPMENT
    node_code VARCHAR(80) UNIQUE NOT NULL, -- HAR-2026-000001, PRO-2026-000001, PAL-2026-000001
    entity_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    data_hash CHAR(64) NOT NULL, -- SHA-256 mã băm Canonical JSON của nút
    blockchain_proof_id UUID,
    metadata JSONB
);

-- Bảng các Cạnh định hướng trong Đồ thị (Trace Edges: Split / Merge / Transform)
CREATE TABLE trace_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    target_node_id UUID REFERENCES trace_nodes(id) ON DELETE RESTRICT,
    relationship_type VARCHAR(60) NOT NULL, -- HARVESTED_FROM, PROCESSED_INTO, PACKED_INTO, AGGREGATED_TO, DISPATCHED_IN
    input_quantity_kg NUMERIC(10,2),
    output_quantity_kg NUMERIC(10,2),
    contribution_ratio NUMERIC(6,4) NOT NULL, -- Tỷ lệ đóng góp khối lượng (0.0001 -> 1.0000)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL,
    UNIQUE (source_node_id, target_node_id, relationship_type)
);

CREATE INDEX idx_trace_edges_source ON trace_edges(source_node_id);
CREATE INDEX idx_trace_edges_target ON trace_edges(target_node_id);
```

---

## 3. THUẬT TOÁN TRUY XUẤT HAI CHIỀU & THU HỒI NÔNG SẢN

### 3.1. Truy xuất Ngược (Backward Traceability):
Khi người tiêu dùng hoặc nhà nhập khẩu quét mã QR trên thùng carton (`CAR-01`):
```sql
WITH RECURSIVE backward_lineage AS (
    SELECT id, node_type, node_code, data_hash, 1 AS depth
    FROM trace_nodes
    WHERE node_code = :target_code
    
    UNION ALL
    
    SELECT parent.id, parent.node_type, parent.node_code, parent.data_hash, bl.depth + 1
    FROM trace_nodes parent
    JOIN trace_edges e ON e.source_node_id = parent.id
    JOIN backward_lineage bl ON bl.id = e.target_node_id
)
SELECT * FROM backward_lineage ORDER BY depth DESC;
```

### 3.2. Truy xuất Xuôi & Quét Vùng Ảnh hưởng Thu hồi (Forward Traceability & Recall Blast Radius):
Khi phát hiện một thửa đất bị nhiễm nấm hoặc thuốc BVTV vượt ngưỡng:
```sql
WITH RECURSIVE forward_lineage AS (
    SELECT id, node_type, node_code, 1 AS depth
    FROM trace_nodes
    WHERE node_code = :compromised_code
    
    UNION ALL
    
    SELECT child.id, child.node_type, child.node_code, fl.depth + 1
    FROM trace_nodes child
    JOIN trace_edges e ON e.target_node_id = child.id
    JOIN forward_lineage fl ON fl.id = e.source_node_id
)
SELECT DISTINCT node_type, node_code FROM forward_lineage WHERE node_type IN ('PALLET', 'SHIPMENT');
```
*Mục tiêu hiệu năng (Target SLO):* Quét toàn bộ đồ thị DAG và lập danh sách 100% các Pallet/Container bị ảnh hưởng trong thời gian **$\le 500\text{ms}$ (P95)**.
