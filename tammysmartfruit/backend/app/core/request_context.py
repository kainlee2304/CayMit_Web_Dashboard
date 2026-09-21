"""
Request Context Module
Maintains async request-scoped context variables (Request ID, Correlation ID, Actor, Org)
"""

from contextvars import ContextVar
from typing import Optional
import uuid

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")
_correlation_id_ctx_var: ContextVar[str] = ContextVar("correlation_id", default="")
_actor_id_ctx_var: ContextVar[Optional[str]] = ContextVar("actor_id", default=None)
_org_id_ctx_var: ContextVar[Optional[str]] = ContextVar("org_id", default=None)

def set_request_context(
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> None:
    req_id = request_id or str(uuid.uuid4())
    corr_id = correlation_id or req_id
    _request_id_ctx_var.set(req_id)
    _correlation_id_ctx_var.set(corr_id)
    if actor_id:
        _actor_id_ctx_var.set(actor_id)
    if org_id:
        _org_id_ctx_var.set(org_id)

def get_request_id() -> str:
    val = _request_id_ctx_var.get()
    return val if val else str(uuid.uuid4())

def get_correlation_id() -> str:
    val = _correlation_id_ctx_var.get()
    return val if val else get_request_id()

def get_actor_id() -> Optional[str]:
    return _actor_id_ctx_var.get()

def get_org_id() -> Optional[str]:
    return _org_id_ctx_var.get()
