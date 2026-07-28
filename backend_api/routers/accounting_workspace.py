from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel, Field

from database import get_db
from routers.accounting import _ensure_accounting_professional_schema
from routers.accounting_tax import _ensure_schema as _ensure_tax_schema
from services.accounting_bank_rules import backfill_missing_bank_accounts
from services.finance_audit import audit_event, ensure_finance_audit_schema, row_to_dict


router = APIRouter(prefix="/accounting/workspace", tags=["Accountant Workspace"])
_SCHEMA_READY = False


CLOSE_ITEMS = (
    (10, "SOURCE_SYNC", "Sincronizar todos los módulos operativos", "Integridad", True),
    (20, "ENTRY_WORKFLOW", "Revisar y contabilizar todos los asientos", "Contabilidad", True),
    (30, "BANK_RECONCILIATION", "Completar conciliaciones bancarias", "Tesorería", True),
    (40, "AR_REVIEW", "Revisar cuentas por cobrar, disputas y deterioro", "Auxiliares", True),
    (50, "AP_REVIEW", "Revisar cuentas por pagar y documentos pendientes", "Auxiliares", True),
    (60, "AUX_RECONCILIATION", "Conciliar auxiliares contra cuentas de control", "Contabilidad", True),
    (70, "TAX_REVIEW", "Conciliar IVA, XML, CAByS y respuestas de Hacienda", "Fiscal", True),
    (80, "FX_REVALUATION", "Revisar tipo de cambio y partidas en moneda extranjera", "Contabilidad", True),
    (90, "FINANCIAL_STATEMENTS", "Revisar balance, resultados y variaciones", "Reportes", True),
    (100, "MANAGEMENT_APPROVAL", "Obtener aprobación final del cierre", "Aprobación", True),
)


def _valid_period(period: str):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period or ""):
        raise HTTPException(400, "El periodo debe usar el formato YYYY-MM")


def _ensure_schema(conn):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    _ensure_accounting_professional_schema(conn)
    _ensure_tax_schema(conn)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_close_checklist (
                id BIGSERIAL PRIMARY KEY,
                company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
                period VARCHAR(7) NOT NULL,
                item_code VARCHAR(40) NOT NULL,
                title TEXT NOT NULL,
                category VARCHAR(30) NOT NULL,
                sequence INTEGER NOT NULL,
                mandatory BOOLEAN NOT NULL DEFAULT TRUE,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                notes TEXT,
                evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
                completed_by TEXT,
                completed_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(company_code,period,item_code),
                CHECK(status IN ('PENDING','IN_PROGRESS','COMPLETE','NOT_APPLICABLE'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_workspace_preferences (
                user_key TEXT PRIMARY KEY,
                default_period_mode VARCHAR(20) NOT NULL DEFAULT 'CURRENT',
                compact_view BOOLEAN NOT NULL DEFAULT FALSE,
                favorite_actions JSONB NOT NULL DEFAULT '["MANUAL_ENTRY","TAX_CENTER","AUXILIARIES","MONTHLY_REPORT"]'::jsonb,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_monthly_close_runs (
                id BIGSERIAL PRIMARY KEY,
                company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
                period VARCHAR(7) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                closed_by TEXT,
                closed_at TIMESTAMPTZ,
                notes TEXT,
                checklist_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
                validation_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
                summary JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(company_code, period),
                CHECK(status IN ('DRAFT','READY','CLOSED','REOPENED'))
            )
        """)
        ensure_finance_audit_schema(cur)
    conn.commit()
    _SCHEMA_READY = True


def _seed_checklist(cur, period, company="MSL-CR"):
    for sequence, code, title, category, mandatory in CLOSE_ITEMS:
        cur.execute("""
            INSERT INTO accounting_close_checklist(company_code,period,item_code,title,category,sequence,mandatory)
            VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(company_code,period,item_code) DO NOTHING
        """, (company, period, code, title, category, sequence, mandatory))


def _scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    if not row:
        return 0
    return next(iter(row.values())) or 0


def _period_bounds(period: str):
    year, month = (int(value) for value in period.split("-"))
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _work_items(cur, period, period_start=None, period_end=None):
    backfill_missing_bank_accounts(cur)
    items = []

    workflow = {}
    cur.execute("""SELECT workflow_status,COUNT(*) count FROM accounting_entries
                   WHERE period=%s GROUP BY workflow_status""", (period,))
    for row in cur.fetchall():
        workflow[row["workflow_status"]] = int(row["count"])
    for status, priority, label in (("DRAFT", "HIGH", "Asientos en borrador"),
                                    ("IN_REVIEW", "HIGH", "Asientos esperando revisión"),
                                    ("APPROVED", "MEDIUM", "Asientos aprobados sin contabilizar")):
        count = workflow.get(status, 0)
        if count:
            items.append({"code": f"ENTRIES_{status}", "area": "ACCOUNTING", "priority": priority,
                          "title": label, "count": count, "action": "LEDGER"})

    overdue_ar_sql = """SELECT COUNT(*) count FROM collections
        WHERE COALESCE(saldo_pendiente,0)>0 AND fecha_vencimiento<CURRENT_DATE"""
    overdue_ar_params = []
    if period_start and period_end:
        overdue_ar_sql += " AND COALESCE(fecha_emision, fecha_vencimiento) >= %s AND COALESCE(fecha_emision, fecha_vencimiento) < %s"
        overdue_ar_params.extend([period_start, period_end])
    overdue_ar = int(_scalar(cur, overdue_ar_sql, tuple(overdue_ar_params)))
    if overdue_ar:
        items.append({"code":"OVERDUE_AR","area":"COLLECTIONS","priority":"HIGH","title":"Facturas de clientes vencidas",
                      "count":overdue_ar,"action":"AUXILIARIES_CUSTOMER"})
    disputes = int(_scalar(cur, "SELECT COUNT(*) count FROM collections WHERE disputada=TRUE AND COALESCE(saldo_pendiente,0)>0"))
    if disputes:
        items.append({"code":"DISPUTED_AR","area":"COLLECTIONS","priority":"HIGH","title":"Cuentas por cobrar en disputa",
                      "count":disputes,"action":"AUXILIARIES_CUSTOMER"})
    overdue_ap_sql = """SELECT COUNT(*) count FROM payment_obligations
        WHERE active=TRUE AND record_type='OBLIGATION' AND COALESCE(balance,0)>0 AND due_date<CURRENT_DATE"""
    overdue_ap_params = []
    if period_start and period_end:
        overdue_ap_sql += " AND COALESCE(issue_date, due_date) >= %s AND COALESCE(issue_date, due_date) < %s"
        overdue_ap_params.extend([period_start, period_end])
    overdue_ap = int(_scalar(cur, overdue_ap_sql, tuple(overdue_ap_params)))
    if overdue_ap:
        items.append({"code":"OVERDUE_AP","area":"PAYABLES","priority":"HIGH","title":"Obligaciones de pago vencidas",
                      "count":overdue_ap,"action":"AUXILIARIES_SUPPLIER"})

    cur.execute("""SELECT
      COUNT(*) FILTER(WHERE xml_path IS NULL) missing_xml,
      COUNT(*) FILTER(WHERE hacienda_status='PENDING') pending_hacienda,
      COUNT(*) FILTER(WHERE electronic_key IS NOT NULL AND EXISTS(
        SELECT 1 FROM tax_electronic_documents x WHERE x.direction=d.direction AND x.electronic_key=d.electronic_key AND x.id<>d.id)) duplicate_keys
      FROM tax_electronic_documents d WHERE TO_CHAR(issue_datetime,'YYYY-MM')=%s""", (period,))
    tax = cur.fetchone() or {}
    for code, key, title, priority in (("TAX_XML", "missing_xml", "Documentos fiscales sin XML", "HIGH"),
                                      ("TAX_HACIENDA", "pending_hacienda", "Respuestas de Hacienda pendientes", "HIGH"),
                                      ("TAX_DUPLICATE", "duplicate_keys", "Documentos con clave electrónica repetida", "CRITICAL")):
        count = int(tax.get(key) or 0)
        if count:
            items.append({"code":code,"area":"TAX","priority":priority,"title":title,"count":count,"action":"TAX_CENTER"})

    rank = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}
    return sorted(items, key=lambda item: (rank[item["priority"]], -item["count"], item["title"]))


@router.get("/dashboard")
def accountant_dashboard(period: str, conn=Depends(get_db)):
    _valid_period(period)
    _ensure_schema(conn)
    period_start, period_end = _period_bounds(period)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        work_items = _work_items(cur, period, period_start, period_end)
        cur.execute("""SELECT COALESCE(SUM(l.debit),0) debit,COALESCE(SUM(l.credit),0) credit,
          COUNT(DISTINCT e.id) entries FROM accounting_entries e
          LEFT JOIN accounting_lines l ON l.entry_id=e.id
          WHERE e.period=%s AND e.workflow_status='POSTED'""", (period,))
        ledger = cur.fetchone()
        cur.execute("""SELECT COALESCE(SUM(saldo_pendiente),0) open_ar,
          COALESCE(SUM(saldo_pendiente) FILTER(WHERE fecha_vencimiento<CURRENT_DATE),0) overdue_ar,
          COUNT(*) open_ar_count,
          COUNT(*) FILTER(WHERE fecha_vencimiento<CURRENT_DATE) overdue_ar_count
          FROM collections
          WHERE COALESCE(saldo_pendiente,0)>0
            AND COALESCE(fecha_emision, fecha_vencimiento) >= %s
            AND COALESCE(fecha_emision, fecha_vencimiento) < %s""", (period_start, period_end))
        ar = cur.fetchone()
        cur.execute("""SELECT COALESCE(SUM(balance),0) open_ap,
          COALESCE(SUM(balance) FILTER(WHERE due_date<CURRENT_DATE),0) overdue_ap,
          COUNT(*) open_ap_count,
          COUNT(*) FILTER(WHERE due_date<CURRENT_DATE) overdue_ap_count
          FROM payment_obligations
          WHERE active=TRUE
            AND record_type='OBLIGATION'
            AND COALESCE(balance,0)>0
            AND COALESCE(issue_date, due_date) >= %s
            AND COALESCE(issue_date, due_date) < %s""", (period_start, period_end))
        ap = cur.fetchone()
        cur.execute("""SELECT status,closed_by,closed_at,reopened_by,reopened_at FROM accounting_period_controls
          WHERE company_code='MSL-CR' AND period=%s""", (period,))
        period_control = cur.fetchone() or {"status":"OPEN"}
        cur.execute("""SELECT id,entry_date,description,origin,workflow_status,created_by,updated_at
          FROM accounting_entries WHERE period=%s ORDER BY updated_at DESC NULLS LAST,id DESC LIMIT 12""", (period,))
        recent = cur.fetchall()

    deductions = sum(min(item["count"], 10) * ({"CRITICAL":5,"HIGH":2,"MEDIUM":1,"LOW":0.5}[item["priority"]]) for item in work_items)
    health = max(0, round(100 - deductions))
    return {"period":period,"health_score":health,"period_control":period_control,"work_items":work_items,
            "kpi_scope": {"from": period_start.isoformat(), "to": (period_end - timedelta(days=1)).isoformat()},
            "kpis":{"posted_entries":int(ledger["entries"] or 0),"debit":float(ledger["debit"] or 0),
                    "credit":float(ledger["credit"] or 0),"open_ar":float(ar["open_ar"] or 0),
                    "open_ar_count":int(ar["open_ar_count"] or 0),
                    "overdue_ar_count":int(ar["overdue_ar_count"] or 0),
                    "overdue_ar":float(ar["overdue_ar"] or 0),"open_ap":float(ap["open_ap"] or 0),
                    "open_ap_count":int(ap["open_ap_count"] or 0),
                    "overdue_ap_count":int(ap["overdue_ap_count"] or 0),
                    "overdue_ap":float(ap["overdue_ap"] or 0)},"recent_entries":recent}


def _automatic_checks(cur, period):
    nonposted = int(_scalar(cur, "SELECT COUNT(*) count FROM accounting_entries WHERE period=%s AND workflow_status<>'POSTED'", (period,)))
    tax_issues = int(_scalar(cur, """SELECT COUNT(*) count FROM tax_electronic_documents d WHERE TO_CHAR(issue_datetime,'YYYY-MM')=%s AND
      (xml_path IS NULL OR hacienda_status='PENDING' OR NOT EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id)
       OR EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id AND COALESCE(l.cabys_code,'')=''))""", (period,)))
    unbalanced = int(_scalar(cur, """SELECT COUNT(*) count FROM (SELECT e.id FROM accounting_entries e JOIN accounting_lines l ON l.entry_id=e.id
      WHERE e.period=%s GROUP BY e.id HAVING ABS(SUM(l.debit)-SUM(l.credit))>0.01) q""", (period,)))
    fx_open = int(_scalar(cur, """SELECT COUNT(*) count FROM accounting_auxiliary_documents
      WHERE status='OPEN' AND currency_code<>'CRC'"""))
    return {"SOURCE_SYNC":{"ready":True,"detail":"Use Sincronizar ERP antes de completar."},
            "ENTRY_WORKFLOW":{"ready":nonposted==0,"detail":f"{nonposted} asientos sin contabilizar"},
            "BANK_RECONCILIATION":{"ready":False,"detail":"Confirmación manual requerida; no hay movimientos bancarios normalizados."},
            "AR_REVIEW":{"ready":True,"detail":"Confirme disputas, vencimientos y deterioro."},
            "AP_REVIEW":{"ready":True,"detail":"Confirme vencimientos, soportes y pagos."},
            "AUX_RECONCILIATION":{"ready":unbalanced==0,"detail":f"{unbalanced} asientos descuadrados"},
            "TAX_REVIEW":{"ready":tax_issues==0,"detail":f"{tax_issues} documentos fiscales con incidencias"},
            "FX_REVALUATION":{"ready":fx_open==0,"detail":f"{fx_open} documentos abiertos en moneda extranjera"},
            "FINANCIAL_STATEMENTS":{"ready":True,"detail":"Revisión profesional y analítica requerida."},
            "MANAGEMENT_APPROVAL":{"ready":False,"detail":"Aprobación explícita requerida."}}


def _json_default(value):
    return __import__("json").dumps(value, default=str)


def _validation_alert_summary(cur, period):
    backfill_missing_bank_accounts(cur)
    critical = []
    warnings = []

    cur.execute("""
        SELECT e.id, e.origin, e.description,
               ROUND((COALESCE(SUM(l.debit),0)-COALESCE(SUM(l.credit),0))::numeric,2) AS difference
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.period=%s
        GROUP BY e.id, e.origin, e.description
        HAVING ROUND((COALESCE(SUM(l.debit),0)-COALESCE(SUM(l.credit),0))::numeric,2) <> 0
        ORDER BY ABS(ROUND((COALESCE(SUM(l.debit),0)-COALESCE(SUM(l.credit),0))::numeric,2)) DESC
        LIMIT 50
    """, (period,))
    for row in cur.fetchall():
        critical.append({
            "code": "UNBALANCED_ENTRY",
            "title": "Asiento descuadrado",
            "entity_id": row["id"],
            "message": f"Asiento {row['id']} tiene diferencia {row['difference']}.",
            "metadata": row,
        })

    cur.execute("""
        SELECT e.id, e.origin, e.description
        FROM accounting_entries e
        LEFT JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.period=%s
        GROUP BY e.id, e.origin, e.description
        HAVING COUNT(l.id)=0
        ORDER BY e.id DESC
        LIMIT 50
    """, (period,))
    for row in cur.fetchall():
        critical.append({
            "code": "ENTRY_WITHOUT_LINES",
            "title": "Asiento sin lineas",
            "entity_id": row["id"],
            "message": f"Asiento {row['id']} no tiene lineas contables.",
            "metadata": row,
        })

    cur.execute("""
        SELECT l.id, l.entry_id, l.account_code, l.account_name, l.debit, l.credit
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id=l.entry_id
        WHERE e.period=%s
          AND (
                (COALESCE(l.debit,0)>0 AND COALESCE(l.credit,0)>0)
             OR (COALESCE(l.debit,0)=0 AND COALESCE(l.credit,0)=0)
          )
        ORDER BY l.id DESC
        LIMIT 50
    """, (period,))
    for row in cur.fetchall():
        critical.append({
            "code": "INVALID_LINE_AMOUNT",
            "title": "Linea con monto invalido",
            "entity_id": row["id"],
            "message": f"Linea {row['id']} del asiento {row['entry_id']} tiene monto invalido.",
            "metadata": row,
        })

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM accounting_entries
        WHERE period=%s AND workflow_status <> 'POSTED'
    """, (period,))
    non_posted = int((cur.fetchone() or {}).get("count") or 0)
    if non_posted:
        critical.append({
            "code": "NON_POSTED_ENTRIES",
            "title": "Asientos sin contabilizar",
            "entity_id": period,
            "message": f"{non_posted} asientos del periodo no estan POSTED.",
            "metadata": {"count": non_posted},
        })

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM cash_app
        WHERE tipo_aplicacion='PAGO'
          AND fecha_pago IS NOT NULL
          AND TO_CHAR(fecha_pago::date,'YYYY-MM')=%s
          AND (bank_account_code IS NULL OR BTRIM(bank_account_code)='')
    """, (period,))
    missing_cash_bank = int((cur.fetchone() or {}).get("count") or 0)
    if missing_cash_bank:
        warnings.append({
            "code": "COLLECTION_PAYMENT_WITHOUT_BANK_ACCOUNT",
            "title": "Pagos Collections sin banco especifico",
            "message": f"{missing_cash_bank} pagos de Collections no tienen banco contable especifico.",
            "metadata": {"count": missing_cash_bank},
        })

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM payment_obligations
        WHERE active=TRUE
          AND status IN ('PAID','PARTIAL')
          AND last_payment_date IS NOT NULL
          AND TO_CHAR(last_payment_date::date,'YYYY-MM')=%s
          AND (payment_bank_account_code IS NULL OR BTRIM(payment_bank_account_code)='')
    """, (period,))
    missing_itp_bank = int((cur.fetchone() or {}).get("count") or 0)
    if missing_itp_bank:
        warnings.append({
            "code": "ITP_PAYMENT_WITHOUT_BANK_ACCOUNT",
            "title": "Pagos ITP sin banco especifico",
            "message": f"{missing_itp_bank} pagos ITP no tienen banco contable especifico.",
            "metadata": {"count": missing_itp_bank},
        })

    return {
        "counts": {
            "critical": len(critical),
            "warning": len(warnings),
            "info": 0,
        },
        "critical": critical,
        "warnings": warnings,
    }


def _close_snapshot(cur, period):
    _seed_checklist(cur, period)
    checks = _automatic_checks(cur, period)
    cur.execute("""
        SELECT * FROM accounting_close_checklist
        WHERE company_code='MSL-CR' AND period=%s
        ORDER BY sequence
    """, (period,))
    checklist = []
    for row in cur.fetchall():
        checklist.append({
            **row,
            "automatic_check": checks.get(row["item_code"], {"ready": False, "detail": "Revision manual"}),
        })

    blockers = [
        item for item in checklist
        if item["mandatory"] and item["status"] not in {"COMPLETE", "NOT_APPLICABLE"}
    ]
    validation = _validation_alert_summary(cur, period)
    cur.execute("""
        SELECT COALESCE(SUM(l.debit),0) debit, COALESCE(SUM(l.credit),0) credit,
               COUNT(DISTINCT e.id) entries
        FROM accounting_entries e
        LEFT JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.period=%s
    """, (period,))
    totals = cur.fetchone() or {}
    debit = float(totals.get("debit") or 0)
    credit = float(totals.get("credit") or 0)
    summary = {
        "entries": int(totals.get("entries") or 0),
        "debit": debit,
        "credit": credit,
        "difference": round(debit - credit, 2),
        "completed": len(checklist) - len(blockers),
        "total": len(checklist),
        "mandatory_blockers": len(blockers),
        "critical_alerts": validation["counts"]["critical"],
        "warning_alerts": validation["counts"]["warning"],
    }
    return checklist, validation, summary, blockers


@router.get("/close-checklist")
def close_checklist(period: str, conn=Depends(get_db)):
    _valid_period(period); _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _seed_checklist(cur, period); conn.commit()
        checks = _automatic_checks(cur, period)
        cur.execute("SELECT * FROM accounting_close_checklist WHERE company_code='MSL-CR' AND period=%s ORDER BY sequence", (period,))
        rows = cur.fetchall()
        cur.execute("SELECT status FROM accounting_period_controls WHERE company_code='MSL-CR' AND period=%s", (period,))
        control = cur.fetchone() or {"status":"OPEN"}
    data=[]
    for row in rows:
        data.append({**row,"automatic_check":checks.get(row["item_code"],{"ready":False,"detail":"Revisión manual"})})
    blockers=[item for item in data if item["mandatory"] and item["status"] not in {"COMPLETE","NOT_APPLICABLE"}]
    return {"period":period,"period_status":control["status"],"ready_to_close":not blockers,
            "completed":len(data)-len(blockers),"total":len(data),"data":data}


@router.get("/guided-close")
def guided_monthly_close(period: str, conn=Depends(get_db)):
    _valid_period(period)
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        checklist, validation, summary, blockers = _close_snapshot(cur, period)
        status = "READY" if not blockers and validation["counts"]["critical"] == 0 else "DRAFT"
        cur.execute("""
            INSERT INTO accounting_monthly_close_runs(
                company_code, period, status, checklist_snapshot, validation_snapshot, summary
            )
            VALUES('MSL-CR', %s, %s, %s, %s, %s)
            ON CONFLICT(company_code, period) DO UPDATE SET
                status=CASE
                    WHEN accounting_monthly_close_runs.status='CLOSED' THEN 'CLOSED'
                    ELSE EXCLUDED.status
                END,
                checklist_snapshot=EXCLUDED.checklist_snapshot,
                validation_snapshot=EXCLUDED.validation_snapshot,
                summary=EXCLUDED.summary,
                updated_at=NOW()
            RETURNING *
        """, (
            period,
            status,
            Json(checklist, dumps=_json_default),
            Json(validation, dumps=_json_default),
            Json(summary),
        ))
        run = cur.fetchone()
        cur.execute("""
            SELECT status, closed_by, closed_at
            FROM accounting_period_controls
            WHERE company_code='MSL-CR' AND period=%s
        """, (period,))
        control = cur.fetchone() or {"status": "OPEN", "closed_by": None, "closed_at": None}
    conn.commit()
    return {
        "period": period,
        "ready_to_close": not blockers and validation["counts"]["critical"] == 0,
        "period_control": control,
        "run": run,
        "summary": summary,
        "checklist": checklist,
        "validation": validation,
        "blockers": blockers,
    }


class GuidedClosePayload(BaseModel):
    user: str
    notes: str | None = None


@router.post("/guided-close/{period}/close")
def close_guided_month(period: str, payload: GuidedClosePayload, conn=Depends(get_db)):
    _valid_period(period)
    _ensure_schema(conn)
    user = (payload.user or "unknown").strip() or "unknown"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        checklist, validation, summary, blockers = _close_snapshot(cur, period)
        if blockers:
            raise HTTPException(409, f"El checklist obligatorio tiene {len(blockers)} pasos pendientes.")
        if validation["counts"]["critical"]:
            raise HTTPException(409, f"Existen {validation['counts']['critical']} alertas criticas antes del cierre.")
        cur.execute("""
            SELECT *
            FROM accounting_period_controls
            WHERE company_code='MSL-CR' AND period=%s
            FOR UPDATE
        """, (period,))
        before = cur.fetchone()
        if before and before.get("status") == "CLOSED":
            raise HTTPException(409, f"El periodo {period} ya esta cerrado.")
        cur.execute("""
            INSERT INTO accounting_period_controls(company_code, period, status, closed_by, closed_at)
            VALUES('MSL-CR', %s, 'CLOSED', %s, NOW())
            ON CONFLICT(company_code, period) DO UPDATE SET
                status='CLOSED',
                closed_by=EXCLUDED.closed_by,
                closed_at=NOW(),
                updated_at=NOW()
            RETURNING *
        """, (period, user))
        control = cur.fetchone()
        cur.execute("""
            INSERT INTO accounting_monthly_close_runs(
                company_code, period, status, closed_by, closed_at, notes,
                checklist_snapshot, validation_snapshot, summary
            )
            VALUES('MSL-CR', %s, 'CLOSED', %s, NOW(), %s, %s, %s, %s)
            ON CONFLICT(company_code, period) DO UPDATE SET
                status='CLOSED',
                closed_by=EXCLUDED.closed_by,
                closed_at=NOW(),
                notes=EXCLUDED.notes,
                checklist_snapshot=EXCLUDED.checklist_snapshot,
                validation_snapshot=EXCLUDED.validation_snapshot,
                summary=EXCLUDED.summary,
                updated_at=NOW()
            RETURNING *
        """, (
            period,
            user,
            payload.notes,
            Json(checklist, dumps=_json_default),
            Json(validation, dumps=_json_default),
            Json(summary),
        ))
        run = cur.fetchone()
        audit_event(
            cur,
            module="accounting",
            action="MONTHLY_PERIOD_CLOSED",
            entity_type="accounting_period",
            entity_id=period,
            performed_by=user,
            performed_role="",
            before=row_to_dict(before),
            after={"period_control": row_to_dict(control), "close_run": row_to_dict(run)},
            metadata={"summary": summary, "notes": payload.notes or ""},
        )
    conn.commit()
    return {
        "status": "ok",
        "period": period,
        "period_control": control,
        "run": run,
        "summary": summary,
    }


class ChecklistUpdate(BaseModel):
    status: str
    user: str
    notes: str | None = None
    evidence: dict = Field(default_factory=dict)


@router.put("/close-checklist/{period}/{item_code}")
def update_checklist(period: str, item_code: str, payload: ChecklistUpdate, conn=Depends(get_db)):
    _valid_period(period); _ensure_schema(conn)
    status=payload.status.upper()
    if status not in {"PENDING","IN_PROGRESS","COMPLETE","NOT_APPLICABLE"}: raise HTTPException(400,"Estado inválido")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if status == "COMPLETE" and item_code in {"ENTRY_WORKFLOW","AUX_RECONCILIATION","TAX_REVIEW","FX_REVALUATION"}:
            validation = _automatic_checks(cur, period).get(item_code, {})
            if not validation.get("ready"):
                raise HTTPException(409, f"El control automático aún presenta incidencias: {validation.get('detail','revisión pendiente')}")
        _seed_checklist(cur,period)
        cur.execute("""UPDATE accounting_close_checklist SET status=%s,notes=%s,evidence=%s,
          completed_by=CASE WHEN %s IN ('COMPLETE','NOT_APPLICABLE') THEN %s ELSE NULL END,
          completed_at=CASE WHEN %s IN ('COMPLETE','NOT_APPLICABLE') THEN NOW() ELSE NULL END,updated_at=NOW()
          WHERE company_code='MSL-CR' AND period=%s AND item_code=%s RETURNING *""",
                    (status,payload.notes,Json(payload.evidence),status,payload.user,status,period,item_code))
        row=cur.fetchone()
        if not row: raise HTTPException(404,"Paso de cierre no encontrado")
    conn.commit(); return {"message":"Checklist actualizado","item":row}


@router.get("/search")
def global_search(q: str = Query(..., min_length=2), limit: int = Query(30, ge=5, le=100), conn=Depends(get_db)):
    _ensure_schema(conn); pattern=f"%{q.strip()}%"; results=[]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id::text reference,'ENTRY' result_type,description title,
          CONCAT(period,' · ',origin,' · ',workflow_status) subtitle,updated_at sort_date
          FROM accounting_entries WHERE id::text ILIKE %s OR description ILIKE %s OR COALESCE(origin,'') ILIKE %s
          ORDER BY updated_at DESC NULLS LAST LIMIT %s""", (pattern,pattern,pattern,limit))
        results.extend(cur.fetchall())
        cur.execute("""SELECT account_code reference,'ACCOUNT' result_type,account_name title,
          CONCAT(account_type,' · ',CASE WHEN active THEN 'Activa' ELSE 'Inactiva' END) subtitle,updated_at sort_date
          FROM accounting_accounts WHERE account_code ILIKE %s OR account_name ILIKE %s LIMIT %s""", (pattern,pattern,limit))
        results.extend(cur.fetchall())
        cur.execute("""SELECT entity_code reference,'AUXILIARY' result_type,entity_name title,
          CONCAT(entity_type,' · ',COALESCE(identification,'')) subtitle,updated_at sort_date
          FROM accounting_auxiliary_entities WHERE entity_code ILIKE %s OR entity_name ILIKE %s OR COALESCE(identification,'') ILIKE %s LIMIT %s""",
                    (pattern,pattern,pattern,limit))
        results.extend(cur.fetchall())
        cur.execute("""SELECT id::text reference,'TAX_DOCUMENT' result_type,
          COALESCE(document_number,electronic_key,'Documento fiscal') title,
          CONCAT(direction,' · ',COALESCE(issuer_name,receiver_name,''),' · ',hacienda_status) subtitle,updated_at sort_date
          FROM tax_electronic_documents WHERE COALESCE(document_number,'') ILIKE %s OR COALESCE(electronic_key,'') ILIKE %s
          OR COALESCE(issuer_name,'') ILIKE %s OR COALESCE(receiver_name,'') ILIKE %s LIMIT %s""", (pattern,pattern,pattern,pattern,limit))
        results.extend(cur.fetchall())
    results.sort(key=lambda x: x.get("sort_date") or datetime.min, reverse=True)
    return {"query":q,"data":results[:limit],"count":min(len(results),limit)}


class PreferenceUpdate(BaseModel):
    default_period_mode: str = "CURRENT"
    compact_view: bool = False
    favorite_actions: list[str] = Field(default_factory=list)


@router.get("/preferences/{user_key}")
def get_preferences(user_key: str, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""INSERT INTO accounting_workspace_preferences(user_key) VALUES(%s) ON CONFLICT(user_key) DO NOTHING""",(user_key,))
        conn.commit(); cur.execute("SELECT * FROM accounting_workspace_preferences WHERE user_key=%s",(user_key,)); row=cur.fetchone()
    return row


@router.put("/preferences/{user_key}")
def update_preferences(user_key: str, payload: PreferenceUpdate, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""INSERT INTO accounting_workspace_preferences(user_key,default_period_mode,compact_view,favorite_actions)
          VALUES(%s,%s,%s,%s) ON CONFLICT(user_key) DO UPDATE SET default_period_mode=EXCLUDED.default_period_mode,
          compact_view=EXCLUDED.compact_view,favorite_actions=EXCLUDED.favorite_actions,updated_at=NOW() RETURNING *""",
                    (user_key,payload.default_period_mode,payload.compact_view,Json(payload.favorite_actions)))
        row=cur.fetchone()
    conn.commit(); return row
