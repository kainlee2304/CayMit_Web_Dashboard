# MODULE ARCHITECTURE SPECIFICATION — TAM MỸ SMART FRUIT ECOSYSTEM
## CANONICAL 35-MODULE REGISTRY, CONTRACTS & BOUNDARIES

> **Tài liệu Đặc tả 35 Module Nghiệp vụ Chuẩn tắc (Canonical Module Registry)**  
> **Phiên bản:** 2.1.0-PROD  
> **Phạm vi áp dụng:** Toàn bộ tầng Backend Application & Domain Services  

---

## 1. NGUYÊN TẮC RÀNG BUỘC MODULE (MODULE BOUNDARY INVARIANTS)

1. **Ranh giới Dữ liệu Tuyệt đối (Database Ownership):** Mỗi Entity và Table thuộc quyền sở hữu duy nhất của 1 Module. Không một Module nào được phép truy vấn SQL trực tiếp hoặc chỉnh sửa bảng thuộc sở hữu của Module khác.
2. **Giao tiếp qua Hợp đồng Công khai (Public Service Interfaces):** Việc đọc/ghi dữ liệu liên module bắt buộc thông qua Public Application Services hoặc lắng nghe Domain Events bất đồng bộ.
3. **Cấm Phụ thuộc Vòng tròn (Zero Circular Dependency):**
   - `IdentityModule` sở hữu thông tin xác thực User/Credential.
   - `OrganizationModule` sở hữu cấu trúc Tổ chức và phân công thành viên (`Membership`).
   - Tầng Auth Middleware phối hợp 2 module qua Application Composition mà không để 2 module phụ thuộc trực tiếp vòng tròn.
4. **Quyền sở hữu Chính sách (Policy Ownership):**
   - `BrandEligibilityPolicy`: Do `PackingModule` sở hữu và thực thi trước khi in tem thương hiệu.
   - `MarketRequirementPolicy`: Do `ExportModule` sở hữu và đối soát trước khi duyệt hồ sơ hải quan.

---

## 2. DANH MỤC 35 MODULE CHUẨN TẮC (CANONICAL 35 MODULE REGISTRY)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ NHÓM I: NỀN TẢNG, DANH TÍNH & DỮ LIỆU CHỦ (4 Modules)                                  │
│ 1. IdentityModule | 2. OrganizationModule | 3. MasterDataModule | 4. ConfigurationModule│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ NHÓM II: VÙNG TRỒNG, NÔNG HỘ & CANH TÁC (9 Modules)                                    │
│ 5. GrowingAreaModule | 6. FarmModule | 7. PlotModule | 8. SeasonModule                │
│ 9. ActivityModule | 10. MaterialModule | 11. IoTModule | 12. MediaModule | 13. AIModule│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ NHÓM III: THU HOẠCH, SƠ CHẾ & CHUỖI CUNG ỨNG (10 Modules)                               │
│ 14. HarvestModule | 15. QualityModule | 16. ProcessingModule | 17. PackingModule       │
│ 18. WarehouseModule | 19. InventoryModule | 20. LogisticsModule | 21. ShipmentModule    │
│ 22. ExportModule | 23. CertificateModule                                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ NHÓM IV: ĐỘ TIN CẬY DỮ LIỆU, TRUY XUẤT NGUỒN GỐC & SỔ CÁI (12 Modules)                 │
│ 24. DataTrustModule | 25. ClaimModule | 26. EvidenceModule | 27. RiskModule            │
│ 28. TraceabilityModule | 29. RecallModule | 30. BlockchainModule | 31. ApprovalModule  │
│ 32. AuditModule | 33. DocumentModule | 34. NotificationModule | 35. ReportingModule     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### CHI TIẾT TỪNG MODULE TRONG REGISTRY

#### NHÓM I: NỀN TẢNG & DANH TÍNH (MODULE 1 - 4)

##### 1. `IdentityModule`
- **Trách nhiệm:** Quản lý tài khoản người dùng, xác thực đăng nhập (Argon2id / PBKDF2), cấp phát Access Token (JWT HS256/RS256) và Refresh Token xoay vòng (hóa băm trong Redis), thu hồi phiên và bảo mật MFA.
- **Owned Aggregates & Tables:** `User` (Aggregate Root), `UserCredential`, `SessionTokenRecord`, `MfaSetting`.
- **Public Interfaces:** `IIdentityService.getUserById()`, `IIdentityService.validateCredentials()`, `IIdentityService.verifyToken()`.
- **Events Emitted:** `UserRegisteredEvent`, `UserLoggedInEvent`, `UserSuspendedEvent`.
- **Events Consumed:** Không.
- **Allowed Dependencies:** Không.
- **Forbidden Dependencies:** `OrganizationModule` và toàn bộ các module chuỗi cung ứng.
- **Authorization & Audit:** Xác thực danh tính người dùng; ghi audit log 100% các phiên đăng nhập và đổi mật khẩu.

##### 2. `OrganizationModule`
- **Trách nhiệm:** Quản lý cơ cấu đa tổ chức (Multi-Tenancy), phòng ban, đội ngũ, mối quan hệ hợp tác và phân công thành viên (`UserOrganizationMembership`).
- **Owned Aggregates & Tables:** `Organization` (Aggregate Root), `Department`, `Team`, `UserOrganizationMembership`, `OrgRelationship`.
- **Public Interfaces:** `IOrganizationService.getOrgDetails()`, `IOrganizationService.getMemberships(user_id)`, `IOrganizationService.validateOrgActive()`.
- **Events Emitted:** `OrganizationCreatedEvent`, `MemberAssignedEvent`, `MemberRoleUpdatedEvent`.
- **Events Consumed:** `UserRegisteredEvent` (tạo phân công mặc định khi có user mới).
- **Allowed Dependencies:** Không.
- **Forbidden Dependencies:** `IdentityModule` (giao tiếp lỏng qua Event và ID).

##### 3. `MasterDataModule`
- **Trách nhiệm:** Quản lý danh mục dữ liệu chủ song ngữ VI/EN có phiên bản: Giống cây (`crop_varieties`), loại bệnh hại, đơn vị đo lường, quy cách bao bì, mã thị trường quốc tế.
- **Owned Aggregates & Tables:** `Crop` (Aggregate Root), `CropVariety`, `MasterCode`, `VarietyTranslation`, `QualityGradeMaster`.
- **Public Interfaces:** `IMasterDataService.getVarietyByCode()`, `IMasterDataService.getTranslations()`, `IMasterDataService.validateCode()`.
- **Events Emitted:** `VarietyAddedEvent`, `MasterDataUpdatedEvent`.
- **Events Consumed:** Không.
- **Allowed Dependencies:** Không.

##### 4. `ConfigurationModule`
- **Trách nhiệm:** Quản lý tham số cấu hình hệ thống: Ngưỡng dung sai Mass Balance có phiên bản (`TolerancePolicy`), bán kính cảnh báo Geofence GPS, cấu hình API mạng Blockchain.
- **Owned Aggregates & Tables:** `SystemConfiguration` (Aggregate Root), `TolerancePolicy`, `GeofencePolicy`.
- **Public Interfaces:** `IConfigService.getToleranceForCrop()`, `IConfigService.getGeofenceThreshold()`, `IConfigService.getBlockchainSettings()`.
- **Events Emitted:** `ConfigurationChangedEvent`.
- **Events Consumed:** Không.
- **Allowed Dependencies:** `MasterDataModule`.

---

#### NHÓM II: VÙNG TRỒNG, NÔNG HỘ & CANH TÁC (MODULE 5 - 13)

##### 5. `GrowingAreaModule`
- **Trách nhiệm:** Quản lý Mã số Vùng trồng (PUC) xuất khẩu, thông tin pháp lý vùng sản xuất, vùng đệm và đa giác PostGIS ranh giới toàn vùng.
- **Owned Aggregates & Tables:** `GrowingArea` (Aggregate Root), `AreaBoundary`, `PucRegistration`.
- **Public Interfaces:** `IGrowingAreaService.getAreaDetails()`, `IGrowingAreaService.validatePucActive()`.
- **Events Emitted:** `GrowingAreaRegisteredEvent`, `GrowingAreaApprovedEvent`, `PucExpiredEvent`.
- **Allowed Dependencies:** `OrganizationModule`, `MasterDataModule`.

##### 6. `FarmModule`
- **Trách nhiệm:** Quản lý nông trại thuộc sở hữu của Nông hộ/Doanh nghiệp, địa chỉ hành chính, chứng nhận quyền sử dụng đất và hợp đồng liên kết HTX.
- **Owned Aggregates & Tables:** `Farm` (Aggregate Root), `FarmContract`, `FarmerProfile`.
- **Public Interfaces:** `IFarmService.getFarmByFarmer()`, `IFarmService.validateFarmOwnership()`.
- **Events Emitted:** `FarmCreatedEvent`, `FarmVerifiedEvent`.
- **Allowed Dependencies:** `OrganizationModule`, `GrowingAreaModule`.

##### 7. `PlotModule`
- **Trách nhiệm:** Quản lý thửa đất / lô vườn chi tiết, đa giác không gian PostGIS (`GEOMETRY(Polygon, 4326)`), diện tích (ha) và kiểm tra Geofence điểm chụp GPS ngoài thực địa (`ST_Contains`).
- **Owned Aggregates & Tables:** `Plot` (Aggregate Root), `PlotBoundary`, `TreeGroup`.
- **Public Interfaces:** `IPlotService.getPlotById()`, `IPlotService.validatePointInPlot(lat, lng)`, `IPlotService.getTreeGroups()`.
- **Events Emitted:** `PlotCreatedEvent`, `PlotBoundaryUpdatedEvent`, `TreeGroupRegisteredEvent`.
- **Allowed Dependencies:** `FarmModule`, `MasterDataModule`.

##### 8. `SeasonModule`
- **Trách nhiệm:** Quản lý chu kỳ mùa vụ canh tác trên từng plot (`DRAFT` ➔ `PLANNED` ➔ `ACTIVE` ➔ `HARVESTING` ➔ `COMPLETED` ➔ `CLOSED`), dự báo năng suất ước tính.
- **Owned Aggregates & Tables:** `CropSeason` (Aggregate Root), `YieldEstimateHistory`.
- **Public Interfaces:** `ISeasonService.getActiveSeasonForPlot()`, `ISeasonService.activateSeason()`, `ISeasonService.recordHarvestProgress()`.
- **Events Emitted:** `SeasonCreatedEvent`, `SeasonActivatedEvent`, `SeasonCompletedEvent`.
- **Events Consumed:** `HarvestBatchAcceptedEvent`.
- **Allowed Dependencies:** `PlotModule`, `MasterDataModule`.

##### 9. `ActivityModule`
- **Trách nhiệm:** Quản lý Nhật ký canh tác (Farm Diary): ghi nhận hoạt động tưới tiêu, bón phân, tỉa cành, bao trái, phun thuốc BVTV kèm ảnh hiện trường, vị trí GPS và thiết bị.
- **Owned Aggregates & Tables:** `FarmActivity` (Aggregate Root), `ActivityEvidenceAttachment`.
- **Public Interfaces:** `IActivityService.logActivity()`, `IActivityService.getLastPesticideSpray()`, `IActivityService.getActivitiesBySeason()`.
- **Events Emitted:** `FarmActivityRecordedEvent`, `PesticideSprayedEvent`.
- **Allowed Dependencies:** `SeasonModule`, `MaterialModule`.

##### 10. `MaterialModule`
- **Trách nhiệm:** Quản lý danh mục và kho vật tư nông nghiệp (Phân bón, thuốc BVTV sinh học), số lô sản xuất, hạn dùng và thời gian cách ly an toàn (PHI - Pre-Harvest Interval).
- **Owned Aggregates & Tables:** `InputMaterial` (Aggregate Root), `MaterialBatch`, `MaterialUsageLog`.
- **Public Interfaces:** `IMaterialService.validatePhiCompliance(plot_id, harvest_date)`, `IMaterialService.deductMaterialStock()`.
- **Events Emitted:** `MaterialBatchReceivedEvent`, `MaterialUsageRecordedEvent`.
- **Allowed Dependencies:** `MasterDataModule`.

##### 11. `IoTModule`
- **Trách nhiệm:** Tiếp nhận số liệu cảm biến vi khí hậu qua MQTT/HTTP, nạp TimescaleDB Hypertable, tổng hợp dữ liệu 5 phút/1 giờ và phát hiện sự cố môi trường.
- **Owned Aggregates & Tables:** `IoTGateway` (Aggregate Root), `IoTDevice`, `SensorMetadata`, `sensor_telemetry_raw` (Hypertable).
- **Public Interfaces:** `IIoTService.ingestTelemetry()`, `IIoTService.getRecentMetrics(plot_id)`.
- **Events Emitted:** `TelemetryIngestedEvent`, `EnvironmentAnomalyAlertEvent`.
- **Allowed Dependencies:** `PlotModule`, `ConfigurationModule`.

##### 12. `MediaModule`
- **Trách nhiệm:** Quản lý tệp đa phương tiện (Ảnh, video, PDF), tính toán mã băm `SHA-256`, tạo Perceptual Hash (pHash) chống trùng ảnh và cung cấp Presigned URL từ S3/MinIO.
- **Owned Aggregates & Tables:** `MediaAsset` (Aggregate Root), `MediaMetadata`, `ImageHashRecord`.
- **Public Interfaces:** `IMediaService.createPresignedUploadUrl()`, `IMediaService.verifyAndStoreMetadata()`, `IMediaService.checkDuplicateImage()`.
- **Events Emitted:** `MediaUploadedEvent`, `DuplicateImageDetectedEvent`.
- **Allowed Dependencies:** Không.

##### 13. `AIModule`
- **Trách nhiệm:** Giao tiếp với AI Vision Engine qua 4 màng lọc độc lập (General Object Filter, ImageNet Guard, ViT 100-Fruit Classifier, Tree/Fruit Disease Classifiers), lưu trữ kết quả phân loại, độ tin cậy và tạo Bằng chứng/Tín hiệu Rủi ro.
- **Owned Aggregates & Tables:** `AIInferenceJob` (Aggregate Root), `PredictionRecord`, `ModelRegistryEntry`.
- **Public Interfaces:** `IAIService.submitInferenceJob()`, `IAIService.getInferenceResult()`.
- **Events Emitted:** `AIInferenceCompletedEvent`, `HighRiskPestDetectedEvent`.
- **Allowed Dependencies:** `MediaModule`, `MasterDataModule`.

---

#### NHÓM III: THU HOẠCH, SƠ CHẾ & CHUỖI CUNG ỨNG (MODULE 14 - 23)

##### 14. `HarvestModule`
- **Trách nhiệm:** Quản lý phiếu thu hoạch từng phần (`HarvestBatch`), tự động kế thừa 100% giống cây, mã vùng trồng từ Season; đối soát thời gian cách ly PHI; kiểm tra trần năng suất và ghi nhận khối lượng cân thực tế.
- **Owned Aggregates & Tables:** `HarvestBatch` (Aggregate Root), `HarvestItem`, `HarvestInspectionNote`.
- **Public Interfaces:** `IHarvestService.createHarvestBatch()`, `IHarvestService.acceptHarvestBatch()`, `IHarvestService.getHarvestDetails()`.
- **Events Emitted:** `HarvestBatchCreatedEvent`, `HarvestBatchSubmittedEvent`, `HarvestBatchAcceptedEvent`, `HarvestBatchRejectedEvent`.
- **Events Consumed:** `PesticideSprayedEvent`.
- **Allowed Dependencies:** `SeasonModule`, `PlotModule`, `MaterialModule`, `MasterDataModule`.

##### 15. `QualityModule`
- **Trách nhiệm:** Quản lý quy trình kiểm tra chất lượng (QC) tại trạm tiếp nhận và xưởng sơ chế: đo độ ngọt (Brix), kiểm tra độ già, phân hạng Grade A/B/C, tổng hợp kết quả AI Vision và cấp chứng nhận kiểm định chất lượng nội bộ.
- **Owned Aggregates & Tables:** `QualityInspection` (Aggregate Root), `SampleBrixTest`, `DefectReport`.
- **Public Interfaces:** `IQualityService.createInspection()`, `IQualityService.recordQcResult()`, `IQualityService.approveForPackaging()`.
- **Events Emitted:** `QCInspectionCompletedEvent`, `LotQualityApprovedEvent`, `LotQualityRejectedEvent`.
- **Events Consumed:** `HarvestBatchSubmittedEvent`, `AIInferenceCompletedEvent`.
- **Allowed Dependencies:** `HarvestModule`, `AIModule`, `MasterDataModule`.

##### 16. `ProcessingModule`
- **Trách nhiệm:** Quản lý công đoạn sơ chế, làm sạch, cắt tỉa, xử lý nhiệt/chiếu xạ, gộp nhiều lô thu hoạch (`Merge`) hoặc phân tách thành phẩm (`Split`), kiểm soát Cân bằng Khối lượng nghiêm ngặt (`Mass Balance Invariant`).
- **Owned Aggregates & Tables:** `ProcessingBatch` (Aggregate Root), `ProcessingInput`, `ProcessingOutput`, `ProcessingWasteLoss`.
- **Public Interfaces:** `IProcessingService.startProcessing()`, `IProcessingService.completeProcessing()`, `IProcessingService.calculateMassBalance()`.
- **Events Emitted:** `ProcessingStartedEvent`, `ProcessingCompletedEvent`, `MassBalanceDiscrepancyEvent`.
- **Allowed Dependencies:** `HarvestModule`, `QualityModule`, `ConfigurationModule`.

##### 17. `PackingModule`
- **Trách nhiệm:** Quản lý đóng gói thùng Carton và xếp Pallet theo chuẩn xuất khẩu, kiểm tra điều kiện gắn nhãn thương hiệu độc quyền (`BrandEligibilityPolicy`), sinh mã định danh SSCC-18 và in tem mã QR truy xuất.
- **Owned Aggregates & Tables:** `PackingBatch` (Aggregate Root), `ProductCarton`, `Pallet` (Aggregate Root), `PalletItem`.
- **Public Interfaces:** `IPackingService.packCartons()`, `IPackingService.assemblePallet()`, `IPackingService.generateQrLabels()`.
- **Events Emitted:** `PackingBatchCompletedEvent`, `PalletAssembledEvent`, `PalletQCApprovedEvent`.
- **Events Consumed:** `ProcessingCompletedEvent`.
- **Allowed Dependencies:** `ProcessingModule`, `MasterDataModule`, `ConfigurationModule`.

##### 18. `WarehouseModule`
- **Trách nhiệm:** Quản lý mặt bằng kho bãi, cấu trúc vị trí (`Kho` ➔ `Khu vực` ➔ `Phòng lạnh` ➔ `Kệ lưu trữ/Bin`), điều kiện nhiệt độ phòng lạnh và cấp phép nhập/xuất kho.
- **Owned Aggregates & Tables:** `Warehouse` (Aggregate Root), `WarehouseZone`, `ColdRoom`, `StorageBin`.
- **Public Interfaces:** `IWarehouseService.getAvailableLocations()`, `IWarehouseService.assignPalletToBin()`.
- **Events Emitted:** `WarehouseLocationAssignedEvent`.
- **Allowed Dependencies:** `OrganizationModule`.

##### 19. `InventoryModule`
- **Trách nhiệm:** Quản lý trạng thái tồn kho của từng Pallet (`AVAILABLE`, `RESERVED`, `QUARANTINE`, `DAMAGED`, `EXPIRED`), thực hiện giao dịch chuyển kho bất biến (`StockMovement`: IN, OUT, TRANSFER, ADJUST) và ngăn chặn tồn kho âm/xuất trùng.
- **Owned Aggregates & Tables:** `InventoryItem` (Aggregate Root), `StockMovementRecord`, `InventoryReservation`.
- **Public Interfaces:** `IInventoryService.receivePallet()`, `IInventoryService.reserveStock()`, `IInventoryService.dispatchPallet()`.
- **Events Emitted:** `StockReceivedEvent`, `StockDispatchedEvent`, `StockHoldQuarantineEvent`.
- **Events Consumed:** `PalletQCApprovedEvent`.
- **Allowed Dependencies:** `WarehouseModule`, `PackingModule`.

##### 20. `LogisticsModule`
- **Trách nhiệm:** Quản lý nhà vận chuyển, phương tiện xe tải lạnh, tài xế, số niêm phong container (Seal) và thiết bị định vị GPS hành trình.
- **Owned Aggregates & Tables:** `Carrier` (Aggregate Root), `Vehicle`, `DriverProfile`, `TransportRoute`.
- **Public Interfaces:** `ILogisticsService.assignCarrier()`, `ILogisticsService.validateDriverAssignment()`.
- **Events Emitted:** `CarrierAssignedEvent`.
- **Allowed Dependencies:** `OrganizationModule`.

##### 21. `ShipmentModule`
- **Trách nhiệm:** Quản lý vận đơn xuất xưởng và hành trình lô hàng (`DRAFT` ➔ `READY_FOR_PICKUP` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `AT_PORT` ➔ `CUSTOMS_CLEARING` ➔ `EXPORTED` ➔ `DELIVERED`), ghi nhận Checkpoints và giám sát nhiệt độ chuỗi lạnh.
- **Owned Aggregates & Tables:** `Shipment` (Aggregate Root), `ShipmentPalletItem`, `ShipmentCheckpoint`, `ColdChainExcursionLog`.
- **Public Interfaces:** `IShipmentService.createShipment()`, `IShipmentService.recordCheckpoint()`, `IShipmentService.completeDelivery()`.
- **Events Emitted:** `ShipmentDispatchedEvent`, `CheckpointRecordedEvent`, `TemperatureExcursionAlertEvent`, `ShipmentDeliveredEvent`.
- **Events Consumed:** `StockDispatchedEvent`.
- **Allowed Dependencies:** `InventoryModule`, `LogisticsModule`.

##### 22. `ExportModule`
- **Trách nhiệm:** Quản lý hồ sơ xuất khẩu quốc tế (Commercial Invoice, Packing List, C/O, Phytosanitary, Bill of Lading, Customs Declaration), kiểm tra tính tương thích yêu cầu thị trường (`MarketRequirementPolicy`), gọi hợp đồng chính thức với `CertificateModule`.
- **Owned Aggregates & Tables:** `ExportOrder` (Aggregate Root), `ExportDocumentAttachment`, `CustomsDeclarationRecord`, `MarketRequirementRule`.
- **Public Interfaces:** `IExportService.compileExportDossier()`, `IExportService.validateMarketCompliance()`, `IExportService.confirmCustomsClearance()`.
- **Events Emitted:** `ExportDossierCompiledEvent`, `CustomsClearedEvent`, `ExportConfirmedEvent`.
- **Events Consumed:** `ShipmentDispatchedEvent`.
- **Allowed Dependencies:** `ShipmentModule`, `CertificateModule`, `MasterDataModule`, `DocumentModule`.

##### 23. `CertificateModule`
- **Trách nhiệm:** Quản lý vòng đời các chứng nhận (`VietGAP`, `GlobalGAP`, `Organic`, `HACCP`, `PUC`, `PHC`), số hiệu chứng chỉ, tổ chức cấp phép, ngày hết hạn và kích hoạt cảnh báo gia hạn định kỳ.
- **Owned Aggregates & Tables:** `Certificate` (Aggregate Root), `CertificateScopeAssignment`, `AuditInspectionReport`.
- **Public Interfaces:** `ICertificateService.validateCertificateValid(scope_id, cert_type)`, `ICertificateService.registerCertificate()`.
- **Events Emitted:** `CertificateVerifiedEvent`, `CertificateExpiringSoonEvent`, `CertificateRevokedEvent`.
- **Allowed Dependencies:** `OrganizationModule`, `MasterDataModule`, `DocumentModule`.

---

#### NHÓM IV: ĐỘ TIN CẬY DỮ LIỆU, TRUY XUẤT NGUỒN GỐC & SỔ CÁI (MODULE 24 - 35)

##### 24. `DataTrustModule`
- **Trách nhiệm:** Điều phối quy trình thẩm định dữ liệu 7 bước, chuẩn hóa payload Canonical JSON, quản lý cấp độ tin cậy (`Assurance Levels 0-3`), đánh giá chữ ký số người thẩm định và phối hợp với `ApprovalModule` để phát sự kiện `BlockchainAnchorEligibleEvent`.
- **Owned Aggregates & Tables:** `TrustVerificationSession` (Aggregate Root), `AssuranceLevelPolicy`.
- **Public Interfaces:** `IDataTrustService.processClaimVerification()`, `IDataTrustService.getAssuranceLevel()`, `IDataTrustService.evaluateAnchorEligibility()`.
- **Events Emitted:** `DataAssurancePromotedEvent`, `VerificationRejectedEvent`, `BlockchainAnchorEligibleEvent`.
- **Allowed Dependencies:** `ClaimModule`, `EvidenceModule`, `RiskModule`, `ApprovalModule`.

##### 25. `ClaimModule`
- **Trách nhiệm:** Quản lý các khẳng định dữ liệu quan trọng (Giống cây, Vùng trồng, Ngày cách ly, Tiêu chuẩn an toàn), nguồn gốc khẳng định (`source_type`) và lịch sử thay đổi trạng thái khẳng định.
- **Owned Aggregates & Tables:** `DataClaim` (Aggregate Root), `ClaimTransitionLog`.
- **Public Interfaces:** `IClaimService.createClaim()`, `IClaimService.updateClaimStatus()`, `IClaimService.getClaimsForEntity()`.
- **Events Emitted:** `ClaimCreatedEvent`, `ClaimStatusUpdatedEvent`.
- **Allowed Dependencies:** `MasterDataModule`.

##### 26. `EvidenceModule`
- **Trách nhiệm:** Thu thập và liên kết bằng chứng khách quan (Ảnh hiện trường pHash, Số liệu cảm biến IoT, Kết quả AI, Phiếu Lab) với từng Claim cụ thể.
- **Owned Aggregates & Tables:** `EvidenceRecord` (Aggregate Root), `EvidenceSourceMapping`.
- **Public Interfaces:** `IEvidenceService.attachEvidence()`, `IEvidenceService.getEvidenceForClaim()`.
- **Events Emitted:** `EvidenceAttachedEvent`.
- **Allowed Dependencies:** `MediaModule`, `IoTModule`, `AIModule`.

##### 27. `RiskModule`
- **Trách nhiệm:** Động cơ đánh giá rủi ro (Risk Engine 0 - 100 điểm) dựa trên sai lệch GPS, bất thường năng suất, phát hiện ảnh chụp trùng lặp hoặc vi phạm thời gian cách ly PHI.
- **Owned Aggregates & Tables:** `RiskAssessment` (Aggregate Root), `RiskFactorEvaluation`, `RiskRuleWeight`.
- **Public Interfaces:** `IRiskService.evaluateEntityRisk()`, `IRiskService.getRiskScore()`.
- **Events Emitted:** `RiskAssessedEvent`, `HighRiskAnomalyFlaggedEvent`.
- **Allowed Dependencies:** `PlotModule`, `IoTModule`, `MediaModule`.

##### 28. `TraceabilityModule`
- **Trách nhiệm:** Xây dựng và truy vấn Đồ thị Có hướng Không Chu trình (DAG) dạng Read-Optimized Projection, tự động sinh nút (`TraceNode`) và cạnh (`TraceEdge`) từ Domain Events, hỗ trợ truy ngược (Backward), truy xuôi (Forward) và chiếu dữ liệu công khai `/t/{trace_code}`.
- **Owned Aggregates & Tables:** `TraceProjectionRegistry` (Aggregate Root), `TraceNode`, `TraceEdge`, `PublicTraceCache`.
- **Public Interfaces:** `ITraceabilityService.getBackwardLineage(trace_code)`, `ITraceabilityService.getForwardLineage(source_id)`, `ITraceabilityService.getPublicTraceData(trace_code)`.
- **Events Emitted:** `TraceNodeCreatedEvent`, `TraceLineageLinkedEvent`.
- **Events Consumed:** Lắng nghe toàn bộ Domain Events từ Harvest, Processing, Packing, Shipment, Export.
- **Allowed Dependencies:** `MasterDataModule`.

##### 29. `RecallModule`
- **Trách nhiệm:** Quản lý quy trình thu hồi nông sản khẩn cấp: nhận diện nguồn gốc sự cố, quét thuật toán DAG để xác định toàn bộ các lô sơ chế, pallet, container và nhà nhập khẩu bị ảnh hưởng (Blast Radius), khóa mã QR công khai.
- **Owned Aggregates & Tables:** `ProductRecall` (Aggregate Root), `RecallAffectedItem`, `RecallRecoveryLog`.
- **Public Interfaces:** `IRecallService.initiateRecall()`, `IRecallService.analyzeBlastRadius()`, `IRecallService.updateRecoveryQuantity()`.
- **Events Emitted:** `RecallInitiatedEvent`, `RecallActiveEvent`, `RecallClosedEvent`.
- **Allowed Dependencies:** `TraceabilityModule`, `PackingModule`, `ShipmentModule`.

##### 30. `BlockchainModule`
- **Trách nhiệm:** Giao tiếp với hạ tầng Chuỗi khối qua giao diện `IBlockchainAdapter`, ký số bảo mật, gom nhóm các mã băm Merkle Tree định kỳ, lưu trữ `transaction_hash`, `block_number` và cung cấp hàm kiểm tra tính toàn vẹn độc lập.
- **Owned Aggregates & Tables:** `BlockchainProof` (Aggregate Root), `AnchorBatchJob`, `LedgerNetworkConfig`.
- **Public Interfaces:** `IBlockchainService.queueAnchorJob()`, `IBlockchainService.verifyProof()`, `IBlockchainService.getProofByEntity()`.
- **Events Emitted:** `BlockchainAnchorCompletedEvent`, `BlockchainAnchorFailedEvent`.
- **Events Consumed:** `BlockchainAnchorEligibleEvent` (DUY NHẤT).
- **Allowed Dependencies:** `ConfigurationModule`.

##### 31. `ApprovalModule`
- **Trách nhiệm:** Cung cấp động cơ phê duyệt quy trình chuẩn theo nguyên tắc 4 mắt (4-Eyes Principle), kiểm soát điều kiện `creator_id != approver_id`, phân công người duyệt theo vai trò và ghi nhận lý do từ chối/hoàn trả.
- **Owned Aggregates & Tables:** `ApprovalRequest` (Aggregate Root), `ApprovalStep`, `ApprovalActionLog`.
- **Public Interfaces:** `IApprovalService.submitRequest()`, `IApprovalService.approve()`, `IApprovalService.reject()`.
- **Events Emitted:** `ApprovalSubmittedEvent`, `ApprovalGrantedEvent`, `ApprovalRejectedEvent`.
- **Allowed Dependencies:** `IdentityModule`, `OrganizationModule`.

##### 32. `AuditModule`
- **Trách nhiệm:** Ghi nhận toàn bộ thay đổi dữ liệu nhạy cảm (`before_state` / `after_state`), địa chỉ IP, User Agent, ID tương quan vào bảng `audit_logs` Append-Only bất biến.
- **Owned Aggregates & Tables:** `AuditTrail` (Aggregate Root), `audit_logs` (Append-Only Table).
- **Public Interfaces:** `IAuditService.logAction()`, `IAuditService.queryAuditLogs()`.
- **Events Emitted:** Không.
- **Events Consumed:** Lắng nghe toàn bộ Audit Events và State Changes.
- **Allowed Dependencies:** Không.

##### 33. `DocumentModule`
- **Trách nhiệm:** Quản lý chứng từ gốc số hóa, biên bản kiểm định, hóa đơn thương mại, hợp đồng điện tử và phân phối tệp dùng chung cho toàn hệ thống.
- **Owned Aggregates & Tables:** `DigitalDocument` (Aggregate Root), `DocumentVersion`, `DocumentAccessGrant`.
- **Public Interfaces:** `IDocumentService.storeDocument()`, `IDocumentService.getDocumentMetadata()`.
- **Events Emitted:** `DocumentStoredEvent`, `DocumentArchivedEvent`.
- **Allowed Dependencies:** `MediaModule`, `MasterDataModule`.

##### 34. `NotificationModule`
- **Trách nhiệm:** Phát tán thông báo thời gian thực qua WebSocket `/ws`, Email SMTP và SMS/Push notification, quản lý hộp thư đến in-app.
- **Owned Aggregates & Tables:** `NotificationMessage` (Aggregate Root), `UserInboxRecord`, `NotificationTemplate`.
- **Public Interfaces:** `INotificationService.sendNotification()`, `INotificationService.getUserInbox()`.
- **Events Emitted:** `NotificationDeliveredEvent`.
- **Events Consumed:** Lắng nghe toàn bộ Alert Events và Notification Triggers.
- **Allowed Dependencies:** `IdentityModule`.

##### 35. `ReportingModule`
- **Trách nhiệm:** Tổng hợp dữ liệu phân tích sản lượng, tỷ lệ sâu bệnh theo vùng, hiệu suất chuỗi lạnh và tạo các báo cáo PDF/Excel phục vụ ban giám đốc và cơ quan hải quan.
- **Owned Aggregates & Tables:** `AnalyticalReport` (Aggregate Root), `ReportSchedule`, `ReportSnapshot`.
- **Public Interfaces:** `IReportingService.generateReport()`, `IReportingService.getDashboardMetrics()`.
- **Events Emitted:** `ReportGeneratedEvent`.
- **Events Consumed:** `HarvestBatchAcceptedEvent`, `ProcessingCompletedEvent`, `ShipmentDeliveredEvent`.
- **Allowed Dependencies:** `MasterDataModule`, `DocumentModule`.
