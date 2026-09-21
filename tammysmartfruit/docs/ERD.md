# ENTITY RELATIONSHIP DIAGRAMS (ERD) — TAM MỸ SMART FRUIT ECOSYSTEM
## DOMAIN-PARTITIONED CONCEPTUAL & LOGICAL RELATIONSHIP MODELS

> **Tài liệu Sơ đồ Quan hệ Thực thể Theo Miền Nghiệp vụ (Domain-Partitioned ERD)**  
> **Phiên bản:** 3.0.0-PROD  
> **Nguyên tắc:** Phân tách rõ ràng theo từng phân hệ — Không nhồi nhét toàn bộ bảng vào 1 sơ đồ đơn lẻ  

---

## 1. PHÂN HỆ NỀN TẢNG, DANH TÍNH & ĐA TỔ CHỨC (FOUNDATION & IDENTITY ERD)

```mermaid
erDiagram
    users ||--o| user_credentials : "has authentication"
    users ||--o{ user_sessions : "maintains"
    users ||--o| mfa_settings : "configures"
    users ||--o{ user_roles : "assigned"
    roles ||--o{ user_roles : "granted to"
    roles ||--o{ role_permissions : "contains"
    permissions ||--o{ role_permissions : "grouped in"
    
    organizations ||--o{ departments : "contains"
    departments ||--o{ teams : "contains"
    users ||--o{ user_organization_memberships : "belongs to"
    organizations ||--o{ user_organization_memberships : "employs"
    user_organization_memberships ||--o{ membership_roles : "has"
    user_organization_memberships ||--o{ data_scope_assignments : "enforces"

    users {
        UUID id PK
        VARCHAR username UK
        VARCHAR email UK
        VARCHAR full_name
        VARCHAR preferred_locale
    }
    user_credentials {
        UUID id PK
        UUID user_id FK
        VARCHAR password_hash
        VARCHAR password_algo
        BOOLEAN rehash_required
    }
    organizations {
        UUID id PK
        VARCHAR org_code UK
        VARCHAR org_name_vi
        VARCHAR org_type
    }
```

---

## 2. PHÂN HỆ VÙNG TRỒNG, THỬA ĐẤT & CANH TÁC (FARM, AGRONOMY & GIS ERD)

```mermaid
erDiagram
    organizations ||--o{ growing_areas : "manages"
    growing_areas ||--o{ farms : "contains"
    farms ||--o{ plots : "subdivided into"
    plots ||--o{ tree_groups : "plants"
    crop_varieties ||--o{ tree_groups : "classified by"
    crops ||--o{ crop_varieties : "categorized under"
    
    plots ||--o{ crop_seasons : "cycles"
    crop_seasons ||--o{ yield_estimates : "forecasts"
    crop_seasons ||--o{ farm_activities : "logs"
    activity_types ||--o{ farm_activities : "types"
    farm_activities ||--o{ material_usages : "consumes"
    material_batches ||--o{ material_usages : "drawn from"
    materials ||--o{ material_batches : "produced in"

    growing_areas {
        UUID id PK
        VARCHAR puc_registration_code UK
        GEOMETRY boundary_polygon
        NUMERIC total_area_hectares
    }
    plots {
        UUID id PK
        VARCHAR plot_code UK
        GEOMETRY boundary_polygon
        NUMERIC area_hectares
    }
    crop_seasons {
        UUID id PK
        VARCHAR season_code UK
        DATE start_date
        VARCHAR season_status
        NUMERIC forecasted_yield_kg
    }
```

---

## 3. PHÂN HỆ THU HOẠCH, SƠ CHẾ & CÂN BẰNG KHỐI LƯỢNG (HARVEST & PROCESSING ERD)

```mermaid
erDiagram
    crop_seasons ||--o{ harvest_batches : "yields"
    harvest_batches ||--o{ harvest_items : "contains"
    harvest_batches ||--o{ harvest_weight_records : "weighed on"
    
    harvest_batches ||--o{ processing_inputs : "consumed as raw input"
    processing_batches ||--o{ processing_inputs : "aggregates"
    processing_batches ||--o{ processing_outputs : "produces"
    processing_batches ||--o{ processing_losses : "documents waste"
    processing_batches ||--o{ processing_rejects : "discards defect"
    mass_balance_policies ||--o{ processing_batches : "governs tolerance"

    harvest_batches {
        UUID id PK
        VARCHAR harvest_code UK
        DATE harvest_date
        NUMERIC total_net_weight_kg
        VARCHAR harvest_status
        VARCHAR phi_compliance_status
    }
    processing_batches {
        UUID id PK
        VARCHAR processing_code UK
        NUMERIC total_input_weight_kg
        NUMERIC total_output_weight_kg
        NUMERIC total_documented_loss_kg
        VARCHAR mass_balance_status
    }
```

---

## 4. PHÂN HỆ ĐÓNG GÓI, KHO LẠNH & TỒN KHO (PACKING & INVENTORY ERD)

```mermaid
erDiagram
    processing_outputs ||--o{ packing_inputs : "allocated to"
    packing_batches ||--o{ packing_inputs : "receives"
    brands ||--o{ packing_batches : "branded with"
    packing_batches ||--o{ cartons : "packs"
    cartons ||--o{ pallet_items : "stacked onto"
    pallets ||--o{ pallet_items : "contains"
    
    pallets ||--o| inventory_items : "tracked as stock"
    storage_bins ||--o{ inventory_items : "placed in"
    cold_rooms ||--o{ storage_bins : "houses"
    warehouses ||--o{ warehouse_zones : "structured into"
    warehouse_zones ||--o{ cold_rooms : "contains"
    
    inventory_items ||--o{ stock_movements : "records movement"
    inventory_items ||--o| inventory_reservations : "locked for order"

    pallets {
        UUID id PK
        VARCHAR pallet_code UK
        VARCHAR sscc_18_code UK
        NUMERIC total_net_weight_kg
        VARCHAR pallet_qc_status
        VARCHAR pallet_inventory_status
    }
    inventory_items {
        UUID id PK
        UUID pallet_id UK
        VARCHAR inventory_status
        INT row_version
    }
```

---

## 5. PHÂN HỆ VẬN TẢI, XUẤT KHẨU & HẢI QUAN (LOGISTICS & EXPORT ERD)

```mermaid
erDiagram
    buyers ||--o{ export_orders : "places"
    export_orders ||--o{ export_order_items : "contains lines"
    pallets ||--o| export_order_items : "fulfilled by"
    export_orders ||--o| customs_records : "clears customs"
    
    carriers ||--o{ vehicles : "operates"
    carriers ||--o{ drivers : "employs"
    carriers ||--o{ shipments : "transports"
    shipments ||--o{ shipment_items : "loads pallets"
    shipments ||--o{ shipment_checkpoints : "logs GPS and Temp"
    shipments ||--o| container_assignments : "sealed with"

    export_orders {
        UUID id PK
        VARCHAR order_code UK
        VARCHAR incoterms
        VARCHAR order_status
        VARCHAR compliance_status
    }
    shipments {
        UUID id PK
        VARCHAR shipment_code UK
        VARCHAR shipment_status
        TIMESTAMPTZ scheduled_departure_at
    }
```

---

## 6. PHÂN HỆ DATA TRUST, BẰNG CHỨNG & PHÊ DUYỆT 4 MẮT (DATA TRUST & APPROVAL ERD)

```mermaid
erDiagram
    data_claims ||--o{ claim_evidence_links : "supported by"
    evidence_records ||--o{ claim_evidence_links : "links to"
    data_claims ||--o{ verification_sessions : "verified in"
    verification_sessions ||--o{ verification_steps : "performs"
    
    data_claims ||--o{ claim_status_history : "tracks lifecycle"
    data_claims ||--o| claim_disputes : "contested via"
    data_claims ||--o| claim_corrections : "superseded through"
    
    approval_requests ||--o{ approval_steps : "sequenced in"
    approval_steps ||--o{ approval_actions : "acted by four-eyes"

    data_claims {
        UUID id PK
        VARCHAR claim_type
        VARCHAR subject_type
        UUID subject_id
        VARCHAR value_code
        VARCHAR assurance_level
        VARCHAR verification_status
        BOOLEAN is_current
    }
    approval_requests {
        UUID id PK
        VARCHAR request_code UK
        VARCHAR entity_type
        UUID entity_id
        VARCHAR current_status
    }
```

---

## 7. PHÂN HỆ TRUY XUẤT NGUỒN GỐC & CHUỖI KHỐI (TRACEABILITY DAG & BLOCKCHAIN ERD)

```mermaid
erDiagram
    domain_event_history ||--o{ trace_edges : "rebuilds lineage"
    trace_nodes ||--o{ trace_edges : "source node (parent)"
    trace_nodes ||--o{ trace_edges : "target node (child)"
    
    domain_event_history ||--o| blockchain_proofs : "anchored as proof"
    anchor_jobs ||--o{ blockchain_proofs : "batched into Merkle Tree"
    blockchain_network_configs ||--o{ anchor_jobs : "broadcasted onto"
    blockchain_proofs ||--o{ proof_verification_history : "audited by public"

    domain_event_history {
        UUID id PK
        UUID event_id UK
        VARCHAR event_type
        VARCHAR aggregate_type
        UUID aggregate_id
        JSONB payload
        CHAR payload_hash
        TIMESTAMPTZ occurred_at
    }
    trace_nodes {
        UUID id PK
        VARCHAR node_type
        VARCHAR node_code UK
        UUID entity_id
        CHAR data_hash
    }
    trace_edges {
        UUID id PK
        UUID source_node_id FK
        UUID target_node_id FK
        VARCHAR relationship_type
        NUMERIC contribution_ratio
    }
    blockchain_proofs {
        UUID id PK
        UUID business_event_id UK
        CHAR canonical_data_hash
        CHAR merkle_leaf_hash
        VARCHAR proof_status
    }
```
