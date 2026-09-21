# DATABASE ARCHITECTURE & PHYSICAL SCHEMA DESIGN — TAM MỸ SMART FRUIT ECOSYSTEM
## PRODUCTION POSTGRESQL 16, POSTGIS, TIMESCALEDB & DOMAIN OWNERSHIP

> **Tài liệu Thiết kế Kiến trúc Cơ sở Dữ liệu Chính thức (Authoritative Database Design)**  
> **Phiên bản:** 3.0.0-PROD  
> **Trạng thái:** Hoàn thành Thiết kế Vật lý Phase 3 (Physical DDL & Migrations Ready)  
> **Nền tảng mục tiêu:** PostgreSQL 16 + PostGIS (Spatial) + TimescaleDB (Time-Series) + Redis 7  

---

## 1. NGUYÊN TẮC THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE DESIGN PRINCIPLES)

1. **Ma trận Sở hữu Bảng Tuyệt đối (Single Module Table Ownership):** Mỗi bảng trong hệ thống thuộc quyền sở hữu duy nhất của 1 trong 35 Canonical Modules. Không có module nào được phép trực tiếp sửa đổi (`INSERT/UPDATE/DELETE`) bảng của module khác.
2. **Khóa Chính Chuẩn UUIDv7 (RFC 9562):** 100% các bảng sử dụng UUIDv7 làm Khóa chính (`Primary Key`), tối ưu hóa sắp xếp theo thời gian và đánh chỉ mục B-Tree (Index Locality), loại bỏ phân mảnh đĩa.
3. **Phân định Rõ ràng Khóa Công khai vs. Khóa Nội bộ:** Tem mã QR `/t/{trace_code}` sử dụng chuỗi ngẫu nhiên bảo mật (`CSPRNG 128-bit`) riêng biệt, tuyệt đối không lộ UUIDv7 nội bộ ra ngoài.
4. **Chuẩn hóa Thời gian & Không gian:** 100% cột thời gian lưu kiểu `TIMESTAMPTZ` (UTC). 100% tọa độ và đa giác ranh giới lưu chuẩn PostGIS `GEOMETRY(Polygon, 4326)` và `GEOMETRY(Point, 4326)`.
5. **Không Lưu Tệp Nhị phân trong Database:** PostgreSQL chỉ lưu Metadata (`object_key`, `sha256_hash`, `phash_hex`, `mime_type`, `size_bytes`), toàn bộ tệp nhị phân lưu trên MinIO / AWS S3.
6. **Bất biến Sổ Sự kiện & Kiểm toán (Append-Only):** Bảng `domain_event_history` và `audit_logs` có Trigger cấp CSDL ngăn chặn tuyệt đối lệnh `UPDATE` và `DELETE`.

---

## 2. MA TRẬN SỞ HỮU BẢNG 35 MODULE (DATABASE OWNERSHIP MATRIX)

| Nhóm Miền | Module Sở Hữu (Module Owner) | Danh Mục Các Bảng Thuộc Quyền Sở Hữu (Owned Tables) | Quyền Ghi (Writable By) | Quyền Đọc (Readable By) | Chính Sách Xóa (Delete Policy) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **I. Foundation** | `IdentityModule` (1) | `users`, `user_credentials`, `roles`, `permissions`, `role_permissions`, `user_roles`, `user_sessions`, `mfa_settings`, `auth_audit_logs` | Identity Service | All Services (via Interface) | `CASCADE` (Credential/Session), `RESTRICT` (Users) |
| | `OrganizationModule` (2) | `organizations`, `departments`, `teams`, `user_organization_memberships`, `membership_roles`, `data_scope_assignments`, `organization_relationships` | Organization Service | All Services | `RESTRICT` (Org/Scope) |
| | `MasterDataModule` (3) | `crops`, `crop_translations`, `crop_varieties`, `crop_variety_translations`, `quality_grades`, `quality_grade_translations`, `activity_types`, `units`, `disease_types`, `market_codes`, `packaging_specs`, `certificate_types`, `material_types` | Master Data Service | All Services (Cached) | `RESTRICT` (Code Masters), `CASCADE` (Translations) |
| | `ConfigurationModule` (4) | `system_configurations`, `mass_balance_policies`, `risk_policies`, `evidence_policies`, `assurance_policies`, `geofence_policies`, `blockchain_anchoring_policies`, `market_requirement_policies` | Config Admin Service | All Services | `RESTRICT` (Versioned Policies) |
| **II. Upstream Farm** | `GrowingAreaModule` (5) | `growing_areas` | Growing Area Service | Farm, Harvest, Traceability | `RESTRICT` |
| | `FarmModule` (6) | `farms`, `farm_farmer_assignments` | Farm Service | Agronomy, Harvest | `RESTRICT` |
| | `PlotModule` (7) | `plots`, `tree_groups` | Plot Service | Agronomy, IoT, AI, Harvest | `RESTRICT` |
| | `SeasonModule` (8) | `crop_seasons`, `yield_estimates` | Season Service | Activity, Harvest, Reporting | `RESTRICT` |
| | `ActivityModule` (9) | `farm_activities` | Activity Service | Agronomy, Quality, Audit | `RESTRICT` |
| | `MaterialModule` (10) | `materials`, `material_batches`, `material_usages` | Material Service | Activity, Quality | `RESTRICT` |
| | `IoTModule` (11) | `iot_gateways`, `iot_devices`, `sensors`, `device_assignments`, `sensor_readings` (Hypertable), `telemetry_evidence_snapshots`, `iot_alert_rules`, `iot_alerts` | IoT Worker / Ingest | Agronomy, Cold Chain, AI | `RETENTION 90 DAYS` (Raw), `PERMANENT` (Evidence Snapshots) |
| | `MediaModule` (12) | `media_assets` | Media Service | All Services (Metadata) | `RESTRICT` |
| | `AIModule` (13) | `ai_models`, `ai_model_versions`, `ai_inference_jobs`, `ai_predictions`, `ai_review_actions` | AI Engine Service | Quality, Agronomy | `RESTRICT` |
| **III. Supply Chain** | `HarvestModule` (14) | `harvest_batches`, `harvest_items`, `harvest_weight_records` | Harvest Service | Processing, Quality, Trace | `RESTRICT` |
| | `QualityModule` (15) | `quality_inspections`, `quality_samples`, `brix_tests`, `defect_findings` | Quality Service | Processing, Packing, Export | `RESTRICT` |
| | `ProcessingModule` (16)| `processing_batches`, `processing_inputs`, `processing_outputs`, `processing_losses`, `processing_rejects` | Processing Service | Packing, Trace, Mass Balance | `RESTRICT` |
| | `PackingModule` (17) | `brands`, `brand_eligibility_rules`, `brand_authorizations`, `packing_batches`, `packing_inputs`, `cartons`, `pallets`, `pallet_items`, `qr_trace_tokens` | Packing Service | Warehouse, Shipment, Public | `RESTRICT` |
| | `WarehouseModule` (18) | `warehouses`, `warehouse_zones`, `cold_rooms`, `storage_bins` | Warehouse Service | Inventory, Logistics | `RESTRICT` |
| | `InventoryModule` (19) | `inventory_items`, `stock_movements`, `inventory_reservations`, `temperature_excursions` | Inventory Service | Shipment, Sales | `RESTRICT` (Strict Locking) |
| | `LogisticsModule` (20) | `carriers`, `vehicles`, `drivers` | Logistics Service | Shipment | `RESTRICT` |
| | `ShipmentModule` (21) | `shipments`, `shipment_items`, `container_assignments`, `shipment_checkpoints` | Shipment Service | Export, Traceability | `RESTRICT` |
| | `ExportModule` (22) | `buyers`, `export_orders`, `export_order_items`, `market_requirement_sets`, `market_requirement_rules`, `compliance_evaluations`, `customs_records` | Export Service | Shipment, Finance, Customs | `RESTRICT` |
| | `CertificateModule` (23)| `certificates`, `certificate_scope_assignments`, `certificate_verifications`, `certificate_status_history` | Certificate Service | Export, Packing, Trace | `RESTRICT` |
| **IV. Trust & Trace**| `DataTrustModule` (24) | `verification_sessions`, `verification_steps` | Data Trust Service | Approval, Blockchain | `RESTRICT` |
| | `ClaimModule` (25) | `data_claims`, `claim_status_history`, `claim_disputes`, `claim_corrections` | Claim Service | Trust, Approval, Audit | `RESTRICT` (Never Overwrite) |
| | `EvidenceModule` (26) | `evidence_records`, `claim_evidence_links` | Evidence Service | Data Trust, Risk Engine | `RESTRICT` |
| | `RiskModule` (27) | `risk_assessments`, `risk_factors` | Risk Engine Worker | Data Trust, Approval | `RESTRICT` |
| | `TraceabilityModule` (28)| `trace_nodes`, `trace_edges`, `public_trace_cache` | Traceability Worker | Public QR Portal, Recall | `REBUILDABLE PROJECTION` |
| | `RecallModule` (29) | `product_recalls`, `recall_affected_items` | Recall Service | Traceability, Warehouse | `RESTRICT` |
| | `BlockchainModule` (30)| `blockchain_network_configs`, `anchor_jobs`, `blockchain_proofs`, `proof_verification_history` | Blockchain Worker | Public Trace, Audit | `RESTRICT` |
| | `ApprovalModule` (31) | `approval_requests`, `approval_steps`, `approval_actions` | Approval Engine | All Business Services | `RESTRICT` (4-Eyes Enforced) |
| | `AuditModule` (32) | `audit_logs` | Audit Worker / Trigger | Compliance Inspectors | `IMMUTABLE (NO UPDATE/DELETE)` |
| | `DocumentModule` (33) | `digital_documents`, `document_versions`, `entity_document_links` | Document Service | All Business Services | `RESTRICT` |
| | `NotificationModule` (34)| `notifications`, `notification_recipients`, `notification_preferences` | Notification Worker | User UI / Mobile Push | `CASCADE` (User Preferences) |
| | `ReportingModule` (35) | `analytical_report_snapshots` | Reporting Worker | Management Dashboard | `ARCHIVE 365 DAYS` |
| **Cross-Cutting** | `Event Infrastructure` | `domain_event_history`, `outbox_events`, `processed_events` | Core Backend / Workers | All Consumers | `IMMUTABLE` (Journal), `PURGEABLE` (Outbox) |

---

## 3. CHIẾN LƯỢC ĐỒNG THỜI & BẢO VỆ GIAO DỊCH (CONCURRENCY STRATEGIES)

1. **Kiểm Soát Tồn Kho Chống Xuất Trùng (No Double Outbound):**
   - Bảng `inventory_items` áp dụng cột `row_version INT NOT NULL` (Optimistic Locking).
   - Khi thực hiện Dispatch, câu lệnh SQL sử dụng `SELECT ... FOR UPDATE` trong Transaction để khóa dòng hàng tồn kho của Pallet:
     ```sql
     SELECT id, inventory_status, row_version 
     FROM inventory_items 
     WHERE pallet_id = :pallet_id AND inventory_status = 'AVAILABLE' 
     FOR UPDATE;
     ```
2. **Khóa Chống Đặt Chỗ Trùng có Giữ Lịch sử (Active Reservation Partial Unique Index):**
   - Ràng buộc Partial Unique Index trên bảng `inventory_reservations` bảo đảm chỉ có tối đa 1 đặt chỗ ACTIVE tại một thời điểm nhưng vẫn bảo lưu toàn bộ lịch sử các lần đặt chỗ trước đó:
     ```sql
     CREATE UNIQUE INDEX idx_unique_active_inventory_reservation 
     ON inventory_reservations (inventory_item_id) 
     WHERE (is_fulfilled = FALSE AND is_cancelled = FALSE AND released_at IS NULL);
     ```
3. **Khóa Chống Gán Trùng Chuyến Xe Đang Chạy (Active Pallet Shipment Partial Unique Index):**
   - Ràng buộc Partial Unique Index trên bảng `shipment_items` bảo đảm một Pallet không thể thuộc 2 chuyến xe đang active đồng thời:
     ```sql
     CREATE UNIQUE INDEX idx_unique_active_pallet_shipment
     ON shipment_items (pallet_id)
     WHERE (assignment_status = 'ACTIVE' AND released_at IS NULL);
     ```
4. **Bảo Toàn Khối Lượng Tự Động (Mass Balance Invariant):**
   - Hàm `fn_verify_processing_mass_balance()` là hàm STABLE tính toán và trả về `is_balanced BOOLEAN`. Khi phát hiện sai lệch vượt dung sai, Domain Service ghi nhận trạng thái `IMBALANCE_VIOLATION`, phát sự kiện `MassBalanceDiscrepancyEvent` và từ chối đóng lô.
