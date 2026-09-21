"""
Audit Infrastructure Service
Appends immutable audit records into audit_logs table within active DB transactions.
Enforces automatic redaction of credentials and secrets.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.request_context import get_request_id, get_correlation_id, get_actor_id, get_org_id
from app.core.logging import sanitize_dict, logger
from app.modules.audit.models import AuditLog

class AuditService:
    @staticmethod
    async def record_audit(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        actor_role: Optional[str] = None,
        state_before_json: Optional[Dict[str, Any]] = None,
        state_after_json: Optional[Dict[str, Any]] = None,
        change_diff_json: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Record an immutable audit log entry.
        All JSON payloads are sanitized of sensitive tokens and passwords before persistence.
        """
        req_id = get_request_id()
        corr_id = get_correlation_id()
        
        resolved_actor_id = actor_id
        if not resolved_actor_id:
            ctx_actor = get_actor_id()
            if ctx_actor:
                try:
                    resolved_actor_id = uuid.UUID(ctx_actor)
                except ValueError:
                    pass
                    
        resolved_org_id = organization_id
        if not resolved_org_id:
            ctx_org = get_org_id()
            if ctx_org:
                try:
                    resolved_org_id = uuid.UUID(ctx_org)
                except ValueError:
                    pass

        # If details provided, use as state_after_json or change_diff_json
        after_payload = state_after_json or details

        # Sanitize payloads
        clean_before = sanitize_dict(state_before_json) if state_before_json else None
        clean_after = sanitize_dict(after_payload) if after_payload else None
        clean_diff = sanitize_dict(change_diff_json) if change_diff_json else None

        audit_entry = AuditLog(
            organization_id=resolved_org_id,
            actor_id=resolved_actor_id,
            actor_role=actor_role,
            action=action.upper(),
            resource_type=resource_type.upper(),
            resource_id=resource_id,
            request_id=req_id,
            correlation_id=corr_id,
            ip_address=ip_address,
            user_agent=user_agent,
            state_before_json=clean_before,
            state_after_json=clean_after,
            change_diff_json=clean_diff,
            occurred_at=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        # We don't commit here; audit participates in the parent business transaction
        return audit_entry

    record_audit_log = record_audit
