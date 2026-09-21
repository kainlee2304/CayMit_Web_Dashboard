# SYSTEM ARCHITECTURE - TAMMYSMARTFRUIT (PRE-PHASE 2 PROTOTYPE)

> ⚠️ **STATUS: PRESERVED LEGACY SPECIFICATION / HISTORICAL REFERENCE ONLY**  
> Bản lưu trữ nguyên trạng kiến trúc Prototype ban đầu phục vụ nghiên cứu di chuyển và tái sử dụng mã nguồn.  
> **Kiến trúc chính thức:** Vui lòng xem [ARCHITECTURE.md](file:///d:/Project/CayMit_Web_Dashboard/tammysmartfruit/docs/ARCHITECTURE.md).

---

## 1. Sơ đồ Kiến trúc Tổng thể (High-Level Architecture)

```mermaid
graph TD
    subgraph Client_Layer ["Tầng Giao Diện (Frontend & Public)"]
        UI_Web["Next.js Web Dashboard (React 19 / Turbopack)"]
        UI_QR["Giao diện Tra cứu QR Di động (Public Trace)"]
        UI_Admin["Trang Quản trị & Phân quyền User"]
    end

    subgraph Gateway_API ["Tầng Dịch vụ & Cổng API (FastAPI Backend)"]
        API_Auth["Auth & RBAC (PBKDF2 / Bearer Token)"]
        API_Predict["AI Inference Router (Upload / Realtime)"]
        API_Trace["Blockchain Ledger Router (SHA-256 Chain)"]
        API_Sensors["IoT Telemetry & Device Control"]
        API_Stream["Live MJPEG Stream & Auto Capture"]
        WS_Server["WebSocket Real-time Broadcast (/ws)"]
    end

    subgraph AI_Engine ["Tầng Trí tuệ Nhân tạo (AI Pipeline)"]
        Guard_Obj["General Object Filter (YOLO11n)"]
        Guard_ViT["Fruit Identity Classifier (ViT-100)"]
        Guard_ImgNet["ImageNet Domain Gate (EfficientNet-B0)"]
        Model_Tree["Tree Disease Classifier (YOLOv11 / best_11.pt)"]
        Model_Fruit_YOLO["Fruit Disease Classifier (best.pt)"]
        Model_Fruit_Eff["Fruit Disease Classifier (EfficientNet-B0)"]
    end

    subgraph Data_Storage ["Tầng Lưu trữ Dữ liệu"]
        DB_SQL["Relational DB (SQLite / PostgreSQL)"]
        FS_Uploads["File System Storage (Uploads / Static Images)"]
    end

    subgraph Edge_Hardware ["Tầng Thiết bị IoT & Edge"]
        Jetson["NVIDIA Jetson Nano / Raspberry Pi (Camera Stream)"]
        Sensors["Cảm biến DHT22 / Độ ẩm đất"]
        Actuators["Rơ le đèn trợ sáng / Chuông"]
    end

    UI_Web <-->|REST API / WebSocket| Gateway_API
    UI_QR <-->|REST API| API_Trace
    UI_Admin <-->|REST API| API_Auth

    API_Predict --> AI_Engine
    API_Trace --> DB_SQL
    API_Sensors --> DB_SQL
    API_Auth --> DB_SQL
    API_Predict --> FS_Uploads

    Edge_Hardware <-->|HTTP Polling / Stream / Telemetry| API_Sensors
    Edge_Hardware <-->|MJPEG Stream| API_Stream
```

---

## 2. Luồng xử lý Chẩn đoán AI (AI Pipeline Architecture)

```mermaid
flowchart TD
    Start([Nhận ảnh tải lên]) --> Preprocess[Tiền xử lý: Resize, Chuẩn hóa RGB]
    Preprocess --> Guard_General{Bộ lọc đồ vật chung\nGeneral Object Filter}
    
    Guard_General -- Phát hiện đồ vật/người --> Not_Fruit[Trả về: not_jackfruit\n'Không phát hiện cây hoặc quả mít']
    Guard_General -- Không trùng đồ vật khác --> Guard_ViT{Bộ lọc nhận diện trái\nVision Transformer ViT}
    
    Guard_ViT -- Là quả khác Sầu riêng/Xoài... --> Not_Jackfruit[Trả về: not_jackfruit\n'Phát hiện quả khác không phải mít']
    Guard_ViT -- Là mít hoặc thân cây --> Auto_Router{Bộ định tuyến tự động\nAuto Routing}
    
    Auto_Router -- Thân / Cành mít --> YOLO_Tree[Chạy mô hình best_11.pt\nPhát hiện Sâu đục thân, Nấm hồng, Nứt thân, Sọc vỏ]
    Auto_Router -- Quả mít --> YOLO_Fruit[Chạy mô hình best.pt / EfficientNet\nPhát hiện Sâu đục trái, Thối trái, Trái bình thường]
    
    YOLO_Tree --> Check_Conf{Kiểm tra ngưỡng tin cậy\nConfidence >= 0.75}
    YOLO_Fruit --> Check_Conf
    
    Check_Conf -- Đạt chuẩn --> Save_Result[Lưu Database & Gửi WebSocket cho FE]
    Check_Conf -- Dưới ngưỡng --> Low_Conf[Trả về trạng thái không chắc chắn / Cảnh báo]
```

---

## 3. Kiến trúc Sổ cái Chuỗi khối (Permissioned Blockchain Architecture)

```
+---------------------------------------------------------------------------------------+
| KHỐI 0 (Khởi tạo lô)                                                                  |
| Block Index: 0 | Stage: created | Trace Code: TM-260828-A1B2C3                        |
| Previous Hash: 0000000000000000000000000000000000000000000000000000000000000000       |
| Current Hash : a1f8...39e0                                                            |
+---------------------------------------------------------------------------------------+
                                           │
                                           ▼ (Previous Hash trỏ tới a1f8...39e0)
+---------------------------------------------------------------------------------------+
| KHỐI 1 (Canh tác / Bón phân sinh học)                                                 |
| Block Index: 1 | Stage: cultivation | Actor: HTX Mit Ben Tre                          |
| Previous Hash: a1f8...39e0                                                            |
| Current Hash : 7b2c...881a                                                            |
+---------------------------------------------------------------------------------------+
                                           │
                                           ▼ (Previous Hash trỏ tới 7b2c...881a)
+---------------------------------------------------------------------------------------+
| KHỐI 2 (Thu hoạch & Kiểm định AI)                                                     |
| Block Index: 2 | Stage: harvest | AI Inspection: Healthy (98.5%)                      |
| Previous Hash: 7b2c...881a                                                            |
| Current Hash : 4e99...bf02                                                            |
+---------------------------------------------------------------------------------------+
```

---

## 4. Tích hợp Phần cứng Edge IoT (Edge IoT Integration)

- **Giao tiếp hai chiều (Bidirectional Polling & Push):**
  1. *Telemetry Push:* Thiết bị gửi chỉ số nhiệt độ, độ ẩm lên `/api/sensors` mỗi 30 - 60 giây.
  2. *Command Polling:* Thiết bị định kỳ kiểm tra lệnh chờ (`/api/devices/command/{device_id}`) để bật/tắt đèn trợ sáng hoặc chụp hình.
  3. *Camera Streaming:* Thiết bị stream trực tiếp luồng video MJPEG lên `/api/stream/camera`.
