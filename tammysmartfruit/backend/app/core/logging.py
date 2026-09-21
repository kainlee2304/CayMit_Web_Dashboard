"""
Structured JSON Logging Module
Outputs machine-parseable structured logs with context tracing (Request ID, Correlation ID)
and strict redaction of sensitive credentials.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from app.core.request_context import get_request_id, get_correlation_id, get_actor_id, get_org_id

SENSITIVE_KEYS = {
    "password", "password_hash", "token", "access_token", "refresh_token",
    "secret", "totp_secret", "private_key", "jwt_private_key", "authorization",
    "cookie", "set-cookie", "credit_card", "secret_key"
}

def sanitize_dict(data: Any) -> Any:
    """Recursively redact sensitive keys from dictionaries/lists."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = sanitize_dict(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    return data

class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
            "actor_id": get_actor_id(),
            "org_id": get_org_id(),
        }
        
        # Attach extra metadata if passed in extra dict
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = sanitize_dict(record.extra_data)
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with structured JSON output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)
    
    # Suppress verbose third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)

logger = logging.getLogger("tammy.backend")
