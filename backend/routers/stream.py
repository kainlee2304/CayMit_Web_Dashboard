"""
Router: Camera Stream - MJPEG live stream + Snapshot từ camera
"""
import cv2
import io
import os
import uuid
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy.orm import Session

from database import Prediction, get_db

router = APIRouter(prefix="/api/stream", tags=["Camera Stream"])

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


def _open_camera():
    """DirectShow ổn định hơn MSMF với webcam trên Windows."""
    if sys.platform == "win32":
        return cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    return cv2.VideoCapture(CAMERA_INDEX)


class CameraHub:
    """Một kết nối webcam dùng chung cho web, app và thao tác chụp."""

    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.started = False

    def start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
            threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while True:
            cap = _open_camera()
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 15)
            if not cap.isOpened():
                cap.release()
                time.sleep(2)
                continue
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                with self.lock:
                    self.frame = frame
                time.sleep(1 / 30)
            cap.release()
            time.sleep(1)

    def get_frame(self, timeout=5):
        self.start()
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                if self.frame is not None:
                    return self.frame.copy()
            time.sleep(0.05)
        return None


camera_hub = CameraHub()


@router.post("/capture")
def capture_and_predict(
    model_name: str = "auto",
    device_id: str = "web-camera",
    db: Session = Depends(get_db)
):
    """
    Chụp 1 frame từ camera → chạy YOLO → lưu DB → trả kết quả
    Dùng cho chế độ chụp định kỳ hoặc nút 'Chụp & Phân Tích' trên web
    """
    from model_service import model_service

    # Mở camera, chụp 1 frame
    frame = camera_hub.get_frame()
    if frame is None:
        # Mock nếu không có camera
        img = Image.new("RGB", (640, 480), (30, 60, 30))
        print("[Capture] Không có camera - dùng mock image")
    else:
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Inference
    result = model_service.predict(img, model_name)
    if not result.get("is_jackfruit", False):
        return {
            "predicted_class": result["predicted_class"],
            "confidence": 0.0,
            "all_scores": {},
            "model_used": result["model_used"],
            "is_jackfruit": False,
            "subject_type": "unknown",
            "status": result.get("status", "not_jackfruit"),
            "message": result.get("message"),
        }

    # Lưu ảnh
    filename = f"cam_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
    file_path = UPLOAD_DIR / filename
    img.save(str(file_path), format="JPEG", quality=90)

    # Lưu DB
    db_pred = Prediction(
        image_path=str(file_path),
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        model_used=result["model_used"],
        all_scores=result["all_scores"],
        device_id=device_id,
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)

    return {
        "id": db_pred.id,
        "predicted_class": db_pred.predicted_class,
        "confidence": db_pred.confidence,
        "all_scores": json.loads(db_pred.all_scores or "{}"),
        "model_used": db_pred.model_used,
        "image_filename": filename,
        "captured_at": db_pred.created_at.isoformat(),
        "is_jackfruit": True,
        "subject_type": result.get("subject_type"),
        "status": "detected",
        "message": result.get("message"),
    }


def generate_frames():
    """Generator MJPEG frames từ camera"""
    if camera_hub.get_frame() is None:
        # Camera không có → trả 1 frame thông báo
        img = Image.new("RGB", (640, 480), (20, 20, 30))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((200, 230), "Không tìm thấy camera", fill=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.getvalue() + b"\r\n")
        return

    while True:
        frame = camera_hub.get_frame()
        if frame is None:
            break
        try:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        except (GeneratorExit, BrokenPipeError):
            break


def generate_frames_with_ai(model_name: str = "auto"):
    """Generator MJPEG với YOLO overlay real-time"""
    from model_service import model_service
    import json

    if camera_hub.get_frame() is None:
        return

    CLASS_COLORS_BGR = {
        "pink_disease":            (180, 130, 244),
        "stem_cracking_gummosis":  (50,  160, 250),
        "batocera_rufomaculata":   (160, 130, 255),
        "stripe_canker":           (80,  200, 100),
    }
    CLASS_VI = {
        "pink_disease": "Nam Hong",
        "stem_cracking_gummosis": "Nut Than",
        "batocera_rufomaculata": "Sau Duc Than",
        "stripe_canker": "Soc Vo",
    }

    frame_count = 0
    last_result = None

    while True:
        frame = camera_hub.get_frame()
        if frame is None:
            break

        try:
            # Chỉ inference mỗi 15 frames (~1 lần/giây) để nhẹ CPU
            if frame_count % 15 == 0:
                try:
                    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    last_result = model_service.predict(pil_img, model_name)
                except Exception:
                    pass

            # Vẽ overlay nếu có kết quả
            if last_result and last_result.get("is_jackfruit", False):
                cls = last_result["predicted_class"]
                conf = last_result["confidence"]
                color = CLASS_COLORS_BGR.get(cls, (255, 255, 255))
                label_vi = CLASS_VI.get(cls, cls)

                # Box viền
                h, w = frame.shape[:2]
                cv2.rectangle(frame, (10, 10), (w-10, h-10), color, 2)

                # Background label
                label_text = f"{label_vi}: {conf*100:.0f}%"
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (10, 10), (10 + tw + 10, 10 + th + 14), color, -1)
                cv2.putText(frame, label_text, (15, 10 + th + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

            frame_count += 1
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        except (GeneratorExit, BrokenPipeError):
            break


@router.get("/camera")
def camera_stream():
    """Stream camera thô (không có AI)"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/camera/ai")
def camera_stream_ai(model_name: str = "auto"):
    """Stream camera + YOLO overlay real-time"""
    return StreamingResponse(
        generate_frames_with_ai(model_name),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
