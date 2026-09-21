"""
Runtime Application Database Role Verification Script
Creates/configures the canonical non-superuser role `tammy_app_user`
and verifies that:
1. SELECT & INSERT on domain_event_history: PASS
2. UPDATE on domain_event_history: FAIL (Revoked + Trigger)
3. DELETE on domain_event_history: FAIL (Revoked + Trigger)
4. SELECT & INSERT on audit_logs: PASS
5. UPDATE on audit_logs: FAIL (Revoked + Trigger)
6. DELETE on audit_logs: FAIL (Revoked + Trigger)
"""

import psycopg2
import uuid
from datetime import datetime, timezone
import json

ADMIN_URL = "postgresql://postgres:password@localhost:5433/tammysmartfruit_clean_test"
APP_URL = "postgresql://tammy_app_user:app_secure_password_2026@localhost:5433/tammysmartfruit_clean_test"

def setup_runtime_role():
    print("[1] Connecting as Admin/Superuser to configure runtime role...")
    admin_conn = psycopg2.connect(ADMIN_URL)
    admin_conn.autocommit = True
    cur = admin_conn.cursor()
    
    # 1. Create role if not exists
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'tammy_app_user';")
    if not cur.fetchone():
        cur.execute("CREATE ROLE tammy_app_user WITH LOGIN PASSWORD 'app_secure_password_2026';")
        print(" -> Created role tammy_app_user.")
    else:
        cur.execute("ALTER ROLE tammy_app_user WITH LOGIN PASSWORD 'app_secure_password_2026';")
        print(" -> Role tammy_app_user already exists, updated password.")

    # 2. Grant permissions
    cur.execute("GRANT CONNECT ON DATABASE tammysmartfruit_clean_test TO tammy_app_user;")
    cur.execute("GRANT USAGE ON SCHEMA public TO tammy_app_user;")
    cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tammy_app_user;")
    cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tammy_app_user;")

    # 3. Explicitly Revoke UPDATE/DELETE/TRUNCATE on Append-Only tables
    cur.execute("REVOKE UPDATE, DELETE, TRUNCATE ON domain_event_history FROM tammy_app_user;")
    cur.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM tammy_app_user;")
    print(" -> Permissions granted & UPDATE/DELETE revoked on domain_event_history and audit_logs.")
    admin_conn.close()

def test_runtime_role_permissions():
    print("\n[2] Connecting as Runtime User (tammy_app_user)...")
    app_conn = psycopg2.connect(APP_URL)
    app_conn.autocommit = False
    cur = app_conn.cursor()

    # Get an existing org and user id for FK references
    cur.execute("SELECT id FROM organizations LIMIT 1;")
    org_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users LIMIT 1;")
    user_id = cur.fetchone()[0]

    test_event_id = str(uuid.uuid4())
    test_history_id = str(uuid.uuid4())
    test_audit_id = str(uuid.uuid4())

    results = {}

    # TEST A: SELECT on domain_event_history
    try:
        cur.execute("SELECT count(*) FROM domain_event_history;")
        _ = cur.fetchone()
        results["domain_event_history: SELECT"] = "PASS"
    except Exception as e:
        results["domain_event_history: SELECT"] = f"FAIL ({e})"
        app_conn.rollback()

    # TEST B: INSERT on domain_event_history
    try:
        cur.execute("""
            INSERT INTO domain_event_history (
                id, event_id, event_type, event_version, aggregate_type, aggregate_id,
                organization_id, actor_id, occurred_at, payload, payload_hash
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            test_history_id, test_event_id, "TestRuntimeRoleEvent", "1.0.0", "TestAgg",
            str(uuid.uuid4()), org_id, user_id, datetime.now(timezone.utc),
            json.dumps({"test": "runtime_role"}), "a" * 64
        ))
        app_conn.commit()
        results["domain_event_history: INSERT"] = "PASS"
    except Exception as e:
        results["domain_event_history: INSERT"] = f"FAIL ({e})"
        app_conn.rollback()

    # TEST C: UPDATE on domain_event_history (MUST FAIL)
    try:
        cur.execute("UPDATE domain_event_history SET event_type = 'HACKED' WHERE id = %s;", (test_history_id,))
        app_conn.commit()
        results["domain_event_history: UPDATE"] = "UNEXPECTED PASS (Vulnerability!)"
    except Exception as e:
        app_conn.rollback()
        results["domain_event_history: UPDATE"] = "PASS (Blocked as expected)"

    # TEST D: DELETE on domain_event_history (MUST FAIL)
    try:
        cur.execute("DELETE FROM domain_event_history WHERE id = %s;", (test_history_id,))
        app_conn.commit()
        results["domain_event_history: DELETE"] = "UNEXPECTED PASS (Vulnerability!)"
    except Exception as e:
        app_conn.rollback()
        results["domain_event_history: DELETE"] = "PASS (Blocked as expected)"

    # TEST E: SELECT on audit_logs
    try:
        cur.execute("SELECT count(*) FROM audit_logs;")
        _ = cur.fetchone()
        results["audit_logs: SELECT"] = "PASS"
    except Exception as e:
        results["audit_logs: SELECT"] = f"FAIL ({e})"
        app_conn.rollback()

    # TEST F: INSERT on audit_logs
    try:
        cur.execute("""
            INSERT INTO audit_logs (
                id, organization_id, actor_id, action, resource_type, resource_id, occurred_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            test_audit_id, org_id, user_id, "TEST_RUNTIME_ACTION", "TEST_RES",
            str(uuid.uuid4()), datetime.now(timezone.utc)
        ))
        app_conn.commit()
        results["audit_logs: INSERT"] = "PASS"
    except Exception as e:
        results["audit_logs: INSERT"] = f"FAIL ({e})"
        app_conn.rollback()

    # TEST G: UPDATE on audit_logs (MUST FAIL)
    try:
        cur.execute("UPDATE audit_logs SET action = 'HACKED' WHERE id = %s;", (test_audit_id,))
        app_conn.commit()
        results["audit_logs: UPDATE"] = "UNEXPECTED PASS (Vulnerability!)"
    except Exception as e:
        app_conn.rollback()
        results["audit_logs: UPDATE"] = "PASS (Blocked as expected)"

    # TEST H: DELETE on audit_logs (MUST FAIL)
    try:
        cur.execute("DELETE FROM audit_logs WHERE id = %s;", (test_audit_id,))
        app_conn.commit()
        results["audit_logs: DELETE"] = "UNEXPECTED PASS (Vulnerability!)"
    except Exception as e:
        app_conn.rollback()
        results["audit_logs: DELETE"] = "PASS (Blocked as expected)"

    app_conn.close()

    print("\n--- RUNTIME ROLE VERIFICATION REPORT ---")
    all_passed = True
    for test_name, status in results.items():
        print(f"  {test_name:35}: {status}")
        if "UNEXPECTED" in status or ("FAIL" in status and "Blocked" not in status):
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] Runtime Application Role (tammy_app_user) fully verified!")
    else:
        print("\n[ERROR] Runtime Application Role verification failed!")
        exit(1)

if __name__ == "__main__":
    setup_runtime_role()
    test_runtime_role_permissions()
