"""
RBAC & Data Scope Enforcement Engine
Enforces 3-dimensional authorization: RESOURCE + ACTION + DATA SCOPE.
Defines 11 Canonical Roles, 5 Canonical Scopes, and SQL Query Scope Filters.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from sqlalchemy import Select, and_, or_
from app.core.errors import ForbiddenException
from app.core.logging import logger

class CanonicalRole(str, Enum):
    ADMIN_HQ = "admin_hq"
    TECHNICIAN = "technician"
    FARMER = "farmer"
    PACKHOUSE_LEAD = "packhouse_lead"
    QA_QC = "qa_qc"
    WAREHOUSE_KEEPER = "warehouse_keeper"
    LOGISTICS_DRIVER = "logistics_driver"
    EXPORT_OFFICER = "export_officer"
    AUDITOR_INSPECTOR = "auditor_inspector"
    BUYER_PARTNER = "buyer_partner"
    SYSTEM_WORKER = "system_worker"

class DataScope(str, Enum):
    OWN = "OWN"                     # Only records created by / assigned directly to actor
    ASSIGNED = "ASSIGNED"           # Specific plots, warehouses, vehicles assigned to actor
    COOPERATIVE = "COOPERATIVE"     # Whole cooperative tenant scope
    ORGANIZATION = "ORGANIZATION"   # Whole organization / packhouse / enterprise tenant scope
    ALL = "ALL"                     # Global ecosystem scope (Only admin_hq / auditor read)

@dataclass
class Principal:
    """Authenticated Actor Context passed to Application Services."""
    user_id: str
    username: str
    organization_id: Optional[str]
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    data_scope: DataScope = DataScope.OWN
    assigned_resources: Dict[str, List[str]] = field(default_factory=dict)
    is_active: bool = True

    def has_role(self, *role_codes: str) -> bool:
        if CanonicalRole.ADMIN_HQ.value in self.roles:
            return True
        return any(r in self.roles for r in role_codes)

    def has_permission(self, permission_code: str) -> bool:
        """Check if principal possesses permission (or has wildcard / admin_hq)."""
        if CanonicalRole.ADMIN_HQ.value in self.roles:
            return True
        if "*:*" in self.permissions or "*:all" in self.permissions:
            return True
        if permission_code in self.permissions:
            return True
            
        # Check wildcard resource e.g. "harvest:*" matches "harvest:read"
        if ":" in permission_code:
            res, act = permission_code.split(":", 1)
            if f"{res}:*" in self.permissions or f"{res}:all" in self.permissions:
                return True
                
        return False

    def require_permission(self, permission_code: str) -> None:
        """Raise ForbiddenException if permission is not possessed."""
        if not self.has_permission(permission_code):
            logger.warning(
                f"Permission denied for user {self.user_id}: required '{permission_code}'"
            )
            raise ForbiddenException(
                message_key="errors.auth.permissionDenied",
                code="PERMISSION_DENIED"
            )

def enforce_data_scope(
    query: Select,
    principal: Principal,
    model: Any,
    org_column: str = "organization_id",
    owner_column: str = "created_by",
    id_column: str = "id",
    resource_type: Optional[str] = None
) -> Select:
    """
    Apply Data Scope SQL filter to an SQLAlchemy Select query.
    Protects against multi-tenant tampering and cross-tenant data leakage.
    """
    # 1. Global Ecosystem Scope
    if principal.data_scope == DataScope.ALL:
        return query

    # 2. Organization / Cooperative Scope
    if principal.data_scope in (DataScope.ORGANIZATION, DataScope.COOPERATIVE):
        if not principal.organization_id:
            # If user has no active organization, return empty result
            return query.filter(False)
        if hasattr(model, org_column):
            return query.filter(getattr(model, org_column) == principal.organization_id)
        return query

    # 3. Own Data Scope
    if principal.data_scope == DataScope.OWN:
        conditions = []
        if hasattr(model, owner_column):
            conditions.append(getattr(model, owner_column) == principal.user_id)
        if hasattr(model, "user_id"):
            conditions.append(getattr(model, "user_id") == principal.user_id)
        if hasattr(model, "requested_by_user_id"):
            conditions.append(getattr(model, "requested_by_user_id") == principal.user_id)
            
        if conditions:
            return query.filter(or_(*conditions))
        elif hasattr(model, org_column) and principal.organization_id:
            return query.filter(getattr(model, org_column) == principal.organization_id)
        return query

    # 4. Assigned Resource Scope
    if principal.data_scope == DataScope.ASSIGNED:
        if resource_type and resource_type in principal.assigned_resources:
            allowed_ids = principal.assigned_resources[resource_type]
            if hasattr(model, id_column):
                return query.filter(getattr(model, id_column).in_(allowed_ids))
        elif hasattr(model, org_column) and principal.organization_id:
            return query.filter(getattr(model, org_column) == principal.organization_id)
            
    return query
