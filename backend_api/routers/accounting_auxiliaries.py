from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor

from database import get_db


router = APIRouter(prefix="/accounting/auxiliaries", tags=["Accounting Auxiliaries"])

ENTITY_TYPES = {"CUSTOMER", "SUPPLIER", "BANK", "EMPLOYEE", "TAX", "ASSET", "ADVANCE", "LOAN"}


def _decimal(value, field="amount"):
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(400, f"Invalid {field}")


def _ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_auxiliary_settings (
                entity_type VARCHAR(20) PRIMARY KEY,
                control_account_code VARCHAR(50),
                updated_by TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CHECK (entity_type IN ('CUSTOMER','SUPPLIER','BANK','EMPLOYEE','TAX','ASSET','ADVANCE','LOAN'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_auxiliary_entities (
                id BIGSERIAL PRIMARY KEY,
                entity_type VARCHAR(20) NOT NULL,
                entity_code VARCHAR(100) NOT NULL,
                entity_name TEXT NOT NULL,
                identification TEXT,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                control_account_code VARCHAR(50),
                source_table VARCHAR(80),
                source_id TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_by TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(entity_type, entity_code),
                CHECK (entity_type IN ('CUSTOMER','SUPPLIER','BANK','EMPLOYEE','TAX','ASSET','ADVANCE','LOAN'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_auxiliary_documents (
                id BIGSERIAL PRIMARY KEY,
                entity_id BIGINT NOT NULL REFERENCES accounting_auxiliary_entities(id),
                document_type VARCHAR(40) NOT NULL,
                document_number TEXT NOT NULL,
                issue_date DATE,
                due_date DATE,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                original_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                open_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                reference TEXT,
                source_table VARCHAR(80),
                source_id TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_by TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(source_table, source_id, document_type)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aux_entities_type ON accounting_auxiliary_entities(entity_type, active)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aux_documents_entity ON accounting_auxiliary_documents(entity_id, status, due_date)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_auxiliary_transactions (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES accounting_auxiliary_documents(id),
                transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
                transaction_type VARCHAR(30) NOT NULL,
                effect VARCHAR(10) NOT NULL,
                amount NUMERIC(18,2) NOT NULL,
                reference TEXT,
                accounting_entry_id INTEGER REFERENCES accounting_entries(id),
                created_by TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CHECK (effect IN ('INCREASE','REDUCE')),
                CHECK (amount > 0)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aux_transactions_document ON accounting_auxiliary_transactions(document_id,transaction_date)")
        cur.execute("""
            INSERT INTO accounting_auxiliary_settings(entity_type,control_account_code,updated_by)
            SELECT defaults.entity_type,defaults.account_code,'SYSTEM_DEFAULT'
            FROM (VALUES
                ('CUSTOMER','1.1.04.01'),('SUPPLIER','2.1.01.01'),('BANK','1.1.02'),
                ('EMPLOYEE','2.1.01.02'),('TAX','2.1.02.03'),('LOAN','2.2.04')
            ) AS defaults(entity_type,account_code)
            JOIN accounting_accounts a ON a.account_code=defaults.account_code AND a.active=TRUE
            ON CONFLICT(entity_type) DO NOTHING
        """)
    conn.commit()


def _upsert_entity(cur, entity_type, code, name, identification=None, currency="CRC", source_table=None, source_id=None, metadata=None):
    cur.execute("""
        INSERT INTO accounting_auxiliary_entities (
            entity_type, entity_code, entity_name, identification, currency_code,
            source_table, source_id, metadata, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'SYSTEM_SYNC')
        ON CONFLICT(entity_type,entity_code) DO UPDATE SET
            entity_name=EXCLUDED.entity_name,
            identification=COALESCE(EXCLUDED.identification,accounting_auxiliary_entities.identification),
            source_table=COALESCE(EXCLUDED.source_table,accounting_auxiliary_entities.source_table),
            source_id=COALESCE(EXCLUDED.source_id,accounting_auxiliary_entities.source_id),
            metadata=accounting_auxiliary_entities.metadata || EXCLUDED.metadata,
            updated_at=NOW()
        RETURNING id
    """, (entity_type, str(code), name or str(code), identification, currency or "CRC",
          source_table, str(source_id) if source_id is not None else None, Json(metadata or {})))
    return cur.fetchone()["id"]


def _upsert_document(cur, entity_id, document_type, number, issue_date, due_date, currency,
                     original_amount, open_amount, status, source_table, source_id, reference=None, metadata=None):
    cur.execute("""
        INSERT INTO accounting_auxiliary_documents (
            entity_id, document_type, document_number, issue_date, due_date,
            currency_code, original_amount, open_amount, status, reference,
            source_table, source_id, metadata, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'SYSTEM_SYNC')
        ON CONFLICT(source_table,source_id,document_type) DO UPDATE SET
            entity_id=EXCLUDED.entity_id, document_number=EXCLUDED.document_number,
            issue_date=EXCLUDED.issue_date, due_date=EXCLUDED.due_date,
            currency_code=EXCLUDED.currency_code, original_amount=EXCLUDED.original_amount,
            open_amount=EXCLUDED.open_amount, status=EXCLUDED.status,
            reference=EXCLUDED.reference, metadata=accounting_auxiliary_documents.metadata || EXCLUDED.metadata,
            updated_at=NOW()
    """, (entity_id, document_type, str(number), issue_date, due_date, currency or "CRC",
          _decimal(original_amount), _decimal(open_amount), status, reference,
          source_table, str(source_id), Json(metadata or {})))


@router.post("/sync")
def sync_auxiliaries(conn=Depends(get_db)):
    _ensure_schema(conn)
    counts = {key: 0 for key in ENTITY_TYPES}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM cliente")
            for row in cur.fetchall():
                _upsert_entity(cur, "CUSTOMER", row["codigo"], row.get("nombrejuridico") or row.get("nombrecomercial"),
                               row.get("cedulajuridicavat"), source_table="cliente", source_id=row["id"],
                               metadata={"email": row.get("correo"), "phone": row.get("telefono")})
                counts["CUSTOMER"] += 1

            cur.execute("SELECT * FROM proveedor")
            for row in cur.fetchall():
                _upsert_entity(cur, "SUPPLIER", row["codigo"], row.get("nombre") or row.get("nombrecomercial"),
                               row.get("cedula_vat"), source_table="proveedor", source_id=row["id"],
                               metadata={"iban": row.get("cuenta_iban"), "bank": row.get("banco")})
                counts["SUPPLIER"] += 1

            cur.execute("SELECT * FROM empleados")
            for row in cur.fetchall():
                name = " ".join(filter(None, [row.get("nombre"), row.get("apellidos")]))
                _upsert_entity(cur, "EMPLOYEE", row["codigo"], name, row.get("cedula_id"), row.get("moneda") or "CRC",
                               "empleados", row["id"], {"iban": row.get("cuenta_iban"), "bank": row.get("banco")})
                counts["EMPLOYEE"] += 1

            # Bulk synchronization avoids one database round trip per operational document.
            cur.execute("""
                INSERT INTO accounting_auxiliary_entities (
                    entity_type,entity_code,entity_name,currency_code,source_table,created_by
                )
                SELECT DISTINCT 'CUSTOMER',codigo_cliente,COALESCE(nombre_cliente,codigo_cliente),
                       COALESCE(moneda,'CRC'),'cliente','SYSTEM_SYNC'
                FROM collections WHERE codigo_cliente IS NOT NULL
                ON CONFLICT(entity_type,entity_code) DO UPDATE SET
                    entity_name=EXCLUDED.entity_name,updated_at=NOW()
            """)
            cur.execute("""
                INSERT INTO accounting_auxiliary_documents (
                    entity_id,document_type,document_number,issue_date,due_date,currency_code,
                    original_amount,open_amount,status,source_table,source_id,metadata,created_by
                )
                SELECT e.id,'RECEIVABLE',COALESCE(c.numero_documento,c.id::text),c.fecha_emision,c.fecha_vencimiento,
                       COALESCE(c.moneda,'CRC'),COALESCE(c.total,0),COALESCE(c.saldo_pendiente,c.total,0),
                       CASE WHEN COALESCE(c.saldo_pendiente,c.total,0)=0 THEN 'CLOSED' ELSE 'OPEN' END,
                       'collections',c.id::text,
                       jsonb_build_object('vessel',c.buque_contenedor,'operation',c.operacion),'SYSTEM_SYNC'
                FROM collections c JOIN accounting_auxiliary_entities e
                  ON e.entity_type='CUSTOMER' AND e.entity_code=c.codigo_cliente
                ON CONFLICT(source_table,source_id,document_type) DO UPDATE SET
                    entity_id=EXCLUDED.entity_id,document_number=EXCLUDED.document_number,
                    issue_date=EXCLUDED.issue_date,due_date=EXCLUDED.due_date,currency_code=EXCLUDED.currency_code,
                    original_amount=EXCLUDED.original_amount,open_amount=EXCLUDED.open_amount,
                    status=EXCLUDED.status,metadata=EXCLUDED.metadata,updated_at=NOW()
            """)
            cur.execute("""
                INSERT INTO accounting_auxiliary_entities (
                    entity_type,entity_code,entity_name,currency_code,source_table,created_by
                )
                SELECT DISTINCT
                    CASE WHEN UPPER(COALESCE(payee_type,'')) IN ('EMPLOYEE','EMPLEADO') THEN 'EMPLOYEE' ELSE 'SUPPLIER' END,
                    COALESCE(payee_id::text,payee_name,'PAYEE-'||id::text),
                    COALESCE(payee_name,payee_id::text,'PAYEE-'||id::text),COALESCE(currency,'CRC'),
                    COALESCE(origin,'payment_obligations'),'SYSTEM_SYNC'
                FROM payment_obligations
                ON CONFLICT(entity_type,entity_code) DO UPDATE SET
                    entity_name=EXCLUDED.entity_name,updated_at=NOW()
            """)
            cur.execute("""
                INSERT INTO accounting_auxiliary_documents (
                    entity_id,document_type,document_number,issue_date,due_date,currency_code,
                    original_amount,open_amount,status,source_table,source_id,metadata,created_by
                )
                SELECT e.id,'PAYABLE',COALESCE(p.reference,p.id::text),p.issue_date,p.due_date,
                       COALESCE(p.currency,'CRC'),COALESCE(p.total,0),COALESCE(p.balance,p.total,0),
                       CASE WHEN COALESCE(p.balance,p.total,0)=0 THEN 'CLOSED' ELSE 'OPEN' END,
                       'payment_obligations',p.id::text,
                       jsonb_build_object('vessel',p.vessel,'operation',p.operation),'SYSTEM_SYNC'
                FROM payment_obligations p JOIN accounting_auxiliary_entities e ON
                  e.entity_type=CASE WHEN UPPER(COALESCE(p.payee_type,'')) IN ('EMPLOYEE','EMPLEADO') THEN 'EMPLOYEE' ELSE 'SUPPLIER' END
                  AND e.entity_code=COALESCE(p.payee_id::text,p.payee_name,'PAYEE-'||p.id::text)
                ON CONFLICT(source_table,source_id,document_type) DO UPDATE SET
                    entity_id=EXCLUDED.entity_id,document_number=EXCLUDED.document_number,
                    issue_date=EXCLUDED.issue_date,due_date=EXCLUDED.due_date,currency_code=EXCLUDED.currency_code,
                    original_amount=EXCLUDED.original_amount,open_amount=EXCLUDED.open_amount,
                    status=EXCLUDED.status,metadata=EXCLUDED.metadata,updated_at=NOW()
            """)

            cur.execute("""
                SELECT DISTINCT banco FROM (
                    SELECT banco FROM cash_app WHERE banco IS NOT NULL AND BTRIM(banco)<>''
                    UNION SELECT banco FROM proveedor WHERE banco IS NOT NULL AND BTRIM(banco)<>''
                    UNION SELECT banco FROM empleados WHERE banco IS NOT NULL AND BTRIM(banco)<>''
                ) banks
            """)
            for row in cur.fetchall():
                _upsert_entity(cur, "BANK", row["banco"], row["banco"], source_table="derived_banks")
                counts["BANK"] += 1
        conn.commit()
        return {"status": "ok", "synced": counts}
    except Exception:
        conn.rollback()
        raise


@router.get("/settings")
def list_settings(conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t.entity_type, s.control_account_code, a.account_name
            FROM (SELECT UNNEST(ARRAY['CUSTOMER','SUPPLIER','BANK','EMPLOYEE','TAX','ASSET','ADVANCE','LOAN']) entity_type) t
            LEFT JOIN accounting_auxiliary_settings s ON s.entity_type=t.entity_type
            LEFT JOIN accounting_accounts a ON a.account_code=s.control_account_code
            ORDER BY t.entity_type
        """)
        return {"data": cur.fetchall()}


@router.put("/settings/{entity_type}")
def update_setting(entity_type: str, payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    entity_type = entity_type.upper()
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(400, "Invalid auxiliary type")
    account = str(payload.get("control_account_code") or "").strip()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT account_code FROM accounting_accounts WHERE account_code=%s AND active=TRUE", (account,))
        if account and not cur.fetchone():
            raise HTTPException(400, "Control account does not exist")
        cur.execute("""
            INSERT INTO accounting_auxiliary_settings(entity_type,control_account_code,updated_by)
            VALUES (%s,%s,%s) ON CONFLICT(entity_type) DO UPDATE SET
                control_account_code=EXCLUDED.control_account_code,
                updated_by=EXCLUDED.updated_by, updated_at=NOW()
            RETURNING *
        """, (entity_type, account or None, payload.get("user") or "unknown"))
        row = cur.fetchone()
    conn.commit()
    return {"status": "ok", "setting": row}


@router.get("/entities")
def list_entities(entity_type: str | None = Query(None), search: str | None = Query(None), conn=Depends(get_db)):
    _ensure_schema(conn)
    conditions, params = ["e.active=TRUE"], []
    if entity_type:
        conditions.append("e.entity_type=%s"); params.append(entity_type.upper())
    if search:
        conditions.append("(e.entity_code ILIKE %s OR e.entity_name ILIKE %s)"); params.extend([f"%{search}%", f"%{search}%"])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT e.*, COALESCE(e.control_account_code,s.control_account_code) effective_control_account,
                   COUNT(d.id) document_count,
                   COALESCE(SUM(d.open_amount) FILTER (WHERE d.status='OPEN'),0) open_balance
            FROM accounting_auxiliary_entities e
            LEFT JOIN accounting_auxiliary_settings s ON s.entity_type=e.entity_type
            LEFT JOIN accounting_auxiliary_documents d ON d.entity_id=e.id
            WHERE {' AND '.join(conditions)}
            GROUP BY e.id,s.control_account_code
            ORDER BY e.entity_type,e.entity_name
        """, params)
        return {"data": cur.fetchall()}


@router.post("/entities")
def create_entity(payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    entity_type = str(payload.get("entity_type") or "").upper()
    code, name = str(payload.get("entity_code") or "").strip(), str(payload.get("entity_name") or "").strip()
    if entity_type not in ENTITY_TYPES or not code or not name:
        raise HTTPException(400, "Valid entity_type, entity_code and entity_name are required")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        entity_id = _upsert_entity(cur, entity_type, code, name, payload.get("identification"),
                                   payload.get("currency_code") or "CRC", metadata=payload.get("metadata"))
        cur.execute("""
            UPDATE accounting_auxiliary_entities SET control_account_code=%s, created_by=%s,
                source_table=COALESCE(source_table,'MANUAL'), updated_at=NOW() WHERE id=%s RETURNING *
        """, (payload.get("control_account_code"), payload.get("user") or "unknown", entity_id))
        row = cur.fetchone()
    conn.commit()
    return {"status": "ok", "entity": row}


@router.get("/entities/{entity_id}/documents")
def list_entity_documents(entity_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT *, CASE
                WHEN status='OPEN' AND due_date < CURRENT_DATE THEN CURRENT_DATE-due_date
                ELSE 0 END AS days_overdue
            FROM accounting_auxiliary_documents WHERE entity_id=%s
            ORDER BY status, due_date NULLS LAST, issue_date DESC
        """, (entity_id,))
        return {"data": cur.fetchall()}


@router.post("/entities/{entity_id}/documents")
def create_entity_document(entity_id: int, payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    amount, open_amount = _decimal(payload.get("original_amount")), _decimal(payload.get("open_amount", payload.get("original_amount")))
    if amount < 0 or open_amount < 0 or open_amount > amount:
        raise HTTPException(400, "Document amounts are invalid")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM accounting_auxiliary_entities WHERE id=%s AND active=TRUE", (entity_id,))
        if not cur.fetchone(): raise HTTPException(404, "Auxiliary entity not found")
        source_id = f"manual-{entity_id}-{datetime.utcnow().timestamp()}"
        _upsert_document(cur, entity_id, str(payload.get("document_type") or "OTHER").upper(),
                         payload.get("document_number") or source_id, payload.get("issue_date"), payload.get("due_date"),
                         payload.get("currency_code") or "CRC", amount, open_amount,
                         "CLOSED" if open_amount == 0 else "OPEN", "MANUAL", source_id,
                         payload.get("reference"), payload.get("metadata"))
    conn.commit()
    return {"status": "ok"}


@router.post("/documents/{document_id}/transactions")
def apply_document_transaction(document_id: int, payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    amount = _decimal(payload.get("amount"))
    effect = str(payload.get("effect") or "REDUCE").upper()
    if amount <= 0 or effect not in ("INCREASE", "REDUCE"):
        raise HTTPException(400, "A positive amount and valid effect are required")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM accounting_auxiliary_documents WHERE id=%s FOR UPDATE", (document_id,))
            document = cur.fetchone()
            if not document: raise HTTPException(404, "Auxiliary document not found")
            current = Decimal(document["open_amount"] or 0)
            next_balance = current + amount if effect == "INCREASE" else current - amount
            if next_balance < 0:
                raise HTTPException(409, "The transaction exceeds the open balance")
            cur.execute("""
                INSERT INTO accounting_auxiliary_transactions (
                    document_id,transaction_date,transaction_type,effect,amount,reference,
                    accounting_entry_id,created_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *
            """, (document_id, payload.get("transaction_date") or date.today(),
                  str(payload.get("transaction_type") or "PAYMENT").upper(), effect, amount,
                  payload.get("reference"), payload.get("accounting_entry_id"), payload.get("user") or "unknown"))
            transaction = cur.fetchone()
            cur.execute("""
                UPDATE accounting_auxiliary_documents SET open_amount=%s,
                    status=CASE WHEN %s=0 THEN 'CLOSED' ELSE 'OPEN' END,updated_at=NOW()
                WHERE id=%s RETURNING *
            """, (next_balance, next_balance, document_id))
            updated = cur.fetchone()
        conn.commit()
        return {"status": "ok", "transaction": transaction, "document": updated}
    except HTTPException:
        conn.rollback(); raise
    except Exception:
        conn.rollback(); raise


@router.get("/documents/{document_id}/transactions")
def list_document_transactions(document_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM accounting_auxiliary_transactions WHERE document_id=%s ORDER BY transaction_date,id", (document_id,))
        return {"data": cur.fetchall()}


@router.get("/aging")
def auxiliary_aging(entity_type: str, as_of: date | None = Query(None), conn=Depends(get_db)):
    _ensure_schema(conn)
    cutoff = as_of or date.today()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT e.id entity_id,e.entity_code,e.entity_name,d.currency_code,
                SUM(CASE WHEN d.due_date IS NULL OR d.due_date >= %s THEN d.open_amount ELSE 0 END) current,
                SUM(CASE WHEN %s-d.due_date BETWEEN 1 AND 30 THEN d.open_amount ELSE 0 END) days_1_30,
                SUM(CASE WHEN %s-d.due_date BETWEEN 31 AND 60 THEN d.open_amount ELSE 0 END) days_31_60,
                SUM(CASE WHEN %s-d.due_date BETWEEN 61 AND 90 THEN d.open_amount ELSE 0 END) days_61_90,
                SUM(CASE WHEN %s-d.due_date > 90 THEN d.open_amount ELSE 0 END) over_90,
                SUM(d.open_amount) total
            FROM accounting_auxiliary_entities e
            JOIN accounting_auxiliary_documents d ON d.entity_id=e.id AND d.status='OPEN'
            WHERE e.entity_type=%s AND e.active=TRUE
            GROUP BY e.id,e.entity_code,e.entity_name,d.currency_code ORDER BY e.entity_name
        """, (cutoff, cutoff, cutoff, cutoff, cutoff, entity_type.upper()))
        return {"data": cur.fetchall(), "as_of": cutoff}


@router.get("/reconciliation")
def reconcile_auxiliaries(period: str | None = Query(None), conn=Depends(get_db)):
    _ensure_schema(conn)
    results = []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for entity_type in sorted(ENTITY_TYPES):
            cur.execute("SELECT control_account_code FROM accounting_auxiliary_settings WHERE entity_type=%s", (entity_type,))
            setting = cur.fetchone(); account = setting.get("control_account_code") if setting else None
            cur.execute("""
                SELECT COALESCE(SUM(d.open_amount),0) balance,
                       COUNT(DISTINCT d.currency_code) currency_count,
                       COUNT(*) FILTER (WHERE d.currency_code <> 'CRC') foreign_currency_count,
                       STRING_AGG(DISTINCT d.currency_code, ', ' ORDER BY d.currency_code) currencies
                FROM accounting_auxiliary_documents d
                JOIN accounting_auxiliary_entities e ON e.id=d.entity_id
                WHERE e.entity_type=%s AND e.active=TRUE AND d.status='OPEN'
            """, (entity_type,))
            auxiliary_row = cur.fetchone()
            auxiliary = auxiliary_row["balance"]
            ledger = Decimal("0")
            if account:
                params = [account]; period_clause = ""
                if period: period_clause="AND en.period<=%s"; params.append(period)
                cur.execute(f"""
                    SELECT COALESCE(SUM(l.debit-l.credit),0) balance
                    FROM accounting_lines l JOIN accounting_entries en ON en.id=l.entry_id
                    WHERE l.account_code=%s AND en.workflow_status='POSTED' {period_clause}
                """, params)
                ledger = cur.fetchone()["balance"]
                cur.execute("SELECT normal_balance FROM accounting_accounts WHERE account_code=%s", (account,))
                acc = cur.fetchone()
                if acc and acc.get("normal_balance") == "CREDIT": ledger = -ledger
            fx_required = int(auxiliary_row["currency_count"] or 0) > 1 or int(auxiliary_row["foreign_currency_count"] or 0) > 0
            difference = None if fx_required else Decimal(auxiliary)-Decimal(ledger)
            status = "UNMAPPED" if not account else (
                "FX_REQUIRED" if fx_required else ("OK" if difference == 0 else "DIFFERENCE")
            )
            results.append({"entity_type": entity_type, "control_account_code": account,
                            "auxiliary_balance": auxiliary, "ledger_balance": ledger,
                            "difference": difference, "currencies": auxiliary_row["currencies"],
                            "status": status})
    return {"data": results, "period": period}
