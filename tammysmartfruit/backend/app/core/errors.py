"""
Standardized Error Contract & Custom Exceptions Module
Enforces machine-readable error codes and structured response format:
{
  "error": {
    "code": "...",
    "message_key": "...",
    "field_errors": [...],
    "request_id": "..."
  }
}
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.request_context import get_request_id
from app.core.logging import logger

class FieldError(BaseModel):
    field: str
    code: str
    message_key: str

class ErrorDetail(BaseModel):
    code: str
    message_key: str
    field_errors: List[FieldError] = []
    request_id: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

class AppException(Exception):
    """Base application exception with standardized error code."""
    def __init__(
        self,
        code: str,
        message_key: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        field_errors: Optional[List[FieldError]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message_key = message_key
        self.status_code = status_code
        self.field_errors = field_errors or []
        self.details = details or {}
        super().__init__(message_key)

class UnauthorizedException(AppException):
    def __init__(self, message_key: str = "errors.auth.unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(code=code, message_key=message_key, status_code=status.HTTP_401_UNAUTHORIZED)

class ForbiddenException(AppException):
    def __init__(self, message_key: str = "errors.auth.forbidden", code: str = "PERMISSION_DENIED"):
        super().__init__(code=code, message_key=message_key, status_code=status.HTTP_403_FORBIDDEN)

class NotFoundException(AppException):
    def __init__(self, message_key: str = "errors.resource.notFound", code: str = "RESOURCE_NOT_FOUND"):
        super().__init__(code=code, message_key=message_key, status_code=status.HTTP_404_NOT_FOUND)

class ConflictException(AppException):
    def __init__(self, message_key: str = "errors.resource.conflict", code: str = "RESOURCE_CONFLICT"):
        super().__init__(code=code, message_key=message_key, status_code=status.HTTP_409_CONFLICT)

class ValidationException(AppException):
    def __init__(
        self,
        message_key: str = "errors.validation.failed",
        code: str = "VALIDATION_ERROR",
        field_errors: Optional[List[Any]] = None
    ):
        converted_errors = []
        if field_errors:
            for fe in field_errors:
                if isinstance(fe, FieldError):
                    converted_errors.append(fe)
                elif isinstance(fe, dict):
                    converted_errors.append(FieldError(
                        field=fe.get("field", ""),
                        code=fe.get("code", "INVALID"),
                        message_key=fe.get("message_key", fe.get("message", "errors.validation.invalid"))
                    ))
        super().__init__(
            code=code,
            message_key=message_key,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            field_errors=converted_errors
        )

class MassBalanceViolationException(AppException):
    def __init__(self, message_key: str = "errors.massBalance.violation", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="MASS_BALANCE_VIOLATION",
            message_key=message_key,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class FourEyesViolationException(AppException):
    def __init__(self, message_key: str = "errors.approval.fourEyesViolation"):
        super().__init__(
            code="FOUR_EYES_VIOLATION",
            message_key=message_key,
            status_code=status.HTTP_403_FORBIDDEN
        )

def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with FastAPI application."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        req_id = get_request_id()
        logger.warning(
            f"AppException: code={exc.code}, key={exc.message_key}, status={exc.status_code}",
            extra={"extra_data": {"code": exc.code, "field_errors": [f.model_dump() for f in exc.field_errors]}}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message_key": exc.message_key,
                    "field_errors": [f.model_dump() for f in exc.field_errors],
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = get_request_id()
        field_errors = []
        for error in exc.errors():
            loc = ".".join(str(x) for x in error.get("loc", []))
            err_type = error.get("type", "invalid")
            field_errors.append({
                "field": loc,
                "code": err_type.upper().replace(".", "_"),
                "message_key": f"errors.validation.{err_type}"
            })
            
        logger.warning(f"RequestValidationError: {len(field_errors)} field error(s)")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message_key": "errors.validation.failed",
                    "field_errors": field_errors,
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id()
        logger.exception(f"Unhandled server error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message_key": "errors.server.internal",
                    "field_errors": [],
                    "request_id": req_id
                }
            }
        )
