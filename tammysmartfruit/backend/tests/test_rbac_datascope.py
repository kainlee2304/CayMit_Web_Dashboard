"""
RBAC and DataScope Engine Test Suite
Tests Permission evaluation, Wildcards, and SQL Query Data Scope Enforcement.
"""

import uuid
import pytest
from sqlalchemy import select
from app.core.rbac import Principal, DataScope, CanonicalRole, enforce_data_scope
from app.core.errors import ForbiddenException
from app.modules.organization.models import Organization

def test_principal_has_permission():
    admin = Principal(
        user_id="user-1",
        username="admin",
        organization_id=None,
        roles=["admin_hq"],
        permissions=set()
    )
    # Admin HQ has wildcard access
    assert admin.has_permission("any:permission") is True
    assert admin.has_role("admin_hq") is True

    farmer = Principal(
        user_id="user-2",
        username="farmer",
        organization_id="org-1",
        roles=["farmer"],
        permissions={"harvest:create", "plot:read"}
    )
    assert farmer.has_permission("harvest:create") is True
    assert farmer.has_permission("plot:read") is True
    assert farmer.has_permission("qc:approve") is False

    with pytest.raises(ForbiddenException):
        farmer.require_permission("qc:approve")

def test_enforce_data_scope_filtering():
    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # 1. Scope ALL (Admin HQ)
    admin_principal = Principal(user_id=user_id, username="admin", organization_id=None, data_scope=DataScope.ALL)
    base_query = select(Organization)
    scoped_query = enforce_data_scope(base_query, admin_principal, Organization)
    # No where clause added for ALL
    assert "WHERE" not in str(scoped_query)

    # 2. Scope ORGANIZATION
    org_principal = Principal(user_id=user_id, username="worker", organization_id=org_id, data_scope=DataScope.ORGANIZATION)
    scoped_query_org = enforce_data_scope(base_query, org_principal, Organization, org_column="id")
    assert "WHERE" in str(scoped_query_org)
