"""
FastAPI Application Entrypoint
Tam My Smart Fruit Digital Supply Chain Platform — Unified Canonical Backend
Serves Modular Monolith V1 Domain Endpoints, AI Inference, Stream, IoT, and Traceability.
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

# Ensure root backend and models are accessible
root_dir = Path(__file__).resolve().parents[3]
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.middleware import RequestTracingMiddleware
from app.core.errors import register_exception_handlers
from app.core.database import check_db_health, init_database_schema_and_seeds
from app.api.v1.router import api_v1_router

# Import AI & IoT & Stream routers
try:
    from routers.predict import router as predict_router
    from routers.stream import router as stream_router
    from routers.sensors import router as sensors_router
    from routers.devices import router as devices_router
    from routers.stats import router as stats_router
    from routers.traceability import router as traceability_router
    _legacy_routers_loaded = True
except Exception as e:
    logger.warning(f"Could not load AI/Stream routers from root backend: {e}")
    _legacy_routers_loaded = False

# Configure structured JSON logging on startup
setup_logging(settings.LOG_LEVEL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    
    # 1. Initialize DB schema and seed canonical data
    try:
        await init_database_schema_and_seeds()
    except Exception as e:
        logger.error(f"Failed to initialize database schema and seeds: {e}", exc_info=True)
        
    yield
    
    # Stop camera hub if running on shutdown
    try:
        from routers.stream import hub
        hub.stop()
    except Exception:
        pass
    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG or settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.DEBUG or settings.APP_ENV != "production" else None,
    lifespan=lifespan
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Request & Correlation Tracing Middleware
app.add_middleware(RequestTracingMiddleware)

# 3. Standardized Error Exception Handlers
register_exception_handlers(app)

# 4. Health & Readiness Probes (C4 Infrastructure Endpoints)
@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe: returns 200 if the web process is running."""
    return {
        "status": "UP",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV
    }

@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe: checks database connection health."""
    db_healthy = await check_db_health()
    
    redis_healthy = False
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await r.ping()
        redis_healthy = bool(pong)
        await r.aclose()
    except Exception:
        pass

    overall_ready = db_healthy
    response_payload = {
        "status": "READY" if overall_ready else "NOT_READY",
        "database": "UP" if db_healthy else "DOWN",
        "redis": "UP" if redis_healthy else "DOWN"
    }

    if overall_ready:
        return JSONResponse(status_code=status.HTTP_200_OK, content=response_payload)
    else:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response_payload)

# 5. Mount API V1 Modular Monolith Domains
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# 6. Mount AI, Stream, IoT, Stats, and Traceability Routers
if _legacy_routers_loaded:
    app.include_router(predict_router)
    app.include_router(stream_router)
    app.include_router(sensors_router)
    app.include_router(devices_router)
    app.include_router(stats_router)
    app.include_router(traceability_router)

# 7. Mount Static Uploads directory
uploads_dir = Path(__file__).resolve().parents[3] / "backend" / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
