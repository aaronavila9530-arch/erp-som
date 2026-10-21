from psycopg2.extras import Json


def _json_dumps(value):
    import json
    return json.dumps(value, default=str)


def ensure_finance_audit_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS finance_audit_log (
            id BIGSERIAL PRIMARY KEY,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            performed_by TEXT,
            performed_role TEXT,
            reason TEXT,
            before_snapshot JSONB,
            after_snapshot JSONB,
            metadata JSONB,
            ip_address TEXT,
            workstation TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("ALTER TABLE finance_audit_log ADD COLUMN IF NOT EXISTS ip_address TEXT")
    cur.execute("ALTER TABLE finance_audit_log ADD COLUMN IF NOT EXISTS workstation TEXT")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_finance_audit_module_entity
        ON finance_audit_log(module, entity_type, entity_id, created_at DESC)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_finance_audit_user
        ON finance_audit_log(performed_by, created_at DESC)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_finance_audit_created
        ON finance_audit_log(created_at DESC)
    """)


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_dicts(rows):
    return [dict(row) for row in (rows or [])]


def audit_event(
    cur,
    module,
    action,
    entity_type=None,
    entity_id=None,
    performed_by=None,
    performed_role=None,
    reason=None,
    before=None,
    after=None,
    metadata=None,
    ip_address=None,
    workstation=None,
):
    ensure_finance_audit_schema(cur)
    if not workstation:
        try:
            import socket
            workstation = socket.gethostname()
        except Exception:
            workstation = None
    cur.execute("""
        INSERT INTO finance_audit_log (
            module, action, entity_type, entity_id, performed_by, performed_role,
            reason, before_snapshot, after_snapshot, metadata, ip_address, workstation
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        str(module or "").strip() or "finance",
        str(action or "").strip() or "UNKNOWN",
        entity_type,
        str(entity_id) if entity_id is not None else None,
        performed_by,
        performed_role,
        reason,
        Json(before, dumps=_json_dumps) if before is not None else None,
        Json(after, dumps=_json_dumps) if after is not None else None,
        Json(metadata, dumps=_json_dumps) if metadata is not None else None,
        ip_address,
        workstation,
    ))


def actor_from_headers(x_user=None, x_role=None, x_user_role=None):
    user = str(x_user or "unknown").strip() or "unknown"
    role = str(x_role or x_user_role or "").strip().lower() or None
    return user, role
