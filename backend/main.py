"""
Main FastAPI Application - Hệ thống phát hiện bệnh cây Mít
"""
import json
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from database import create_tables
from routers import predict, sensors, devices, stats, stream, traceability

uploads_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
uploads_dir.mkdir(parents=True, exist_ok=True)


# ─── WebSocket Connection Manager ────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# ─── App Lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Startup] Tạo bảng database...")
    create_tables()
    print("[Startup] ✓ Database sẵn sàng")

    # Mount uploads folder
    uploads_dir.mkdir(parents=True, exist_ok=True)

    yield
    print("[Shutdown] Bye!")


# ─── App Init ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CayMit Disease Detection API",
    description="Hệ thống phát hiện bệnh cây Mít sử dụng YOLO AI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - Cho phép FE (Next.js) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: thay bằng domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (ảnh upload)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(predict.router)
app.include_router(sensors.router)
app.include_router(devices.router)
app.include_router(stats.router)
app.include_router(stream.router)
app.include_router(traceability.router)


# ─── WebSocket - Real-time notifications ─────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Chờ message từ client (heartbeat ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Expose manager để routers có thể broadcast
app.state.ws_manager = manager


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    frontend_index = Path(os.getenv("FRONTEND_DIR", "frontend")) / "index.html"
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    return {"status": "ok", "message": "CayMit Disease Detection API đang chạy 🌱"}


@app.get("/health", tags=["Health"])
def health():
    from model_service import model_service
    return {
        "status": "healthy",
        "models_loaded": model_service.get_available_models(),
    }


# Docker production bundles the statically exported Next.js site here. This
# mount is deliberately last so /api, /uploads, /ws and /health keep priority.
frontend_dir = Path(os.getenv("FRONTEND_DIR", "frontend"))
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
