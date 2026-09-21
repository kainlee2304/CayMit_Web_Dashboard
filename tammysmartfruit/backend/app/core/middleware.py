"""
HTTP Middleware Module
Propagates Request-ID and Correlation-ID headers, sets Async ContextVars,
and emits structured access logs.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.request_context import set_request_context, get_request_id, get_correlation_id
from app.core.logging import logger

class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract incoming tracing headers or generate new UUIDs
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        
        # Populate async ContextVar
        set_request_context(request_id=request_id, correlation_id=correlation_id)
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            
            # Attach tracing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log structured access line
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
                extra={"extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None
                }}
            )
            return response
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.error(
                f"{request.method} {request.url.path} FAILED ({duration_ms}ms): {e}",
                extra={"extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e)
                }}
            )
            raise
