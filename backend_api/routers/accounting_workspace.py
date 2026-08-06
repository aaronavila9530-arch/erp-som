from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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


def _company_code(value: str | None = None, header_value: str | None = None) -> str:
    code = str(value or header_value or "MSL-CR").strip().upper()
    return code or "MSL-CR"


def _ensure_schema(conn):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    _ensure_accounting_professional_schema(conn)
    _ensure_tax_schema(conn)
    try:
        from routers.bank_reconciliation import _ensure_professional_schema as _ensure_bank_reconciliation_schema
        _ensure_bank_reconciliation_schema(conn)
    except Exception:
        pass
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


def _latest_fx_rate(cur):
    cur.execute("""
        SELECT rate, rate_date
        FROM exchange_rate
        WHERE rate_date <= CURRENT_DATE
        ORDER BY rate_date DESC
        LIMIT 1
    """)
    row = cur.fetchone() or {}
    rate = Decimal(str(row.get("rate") or 1))
    if rate <= 0:
        rate = Decimal("1")
    return rate, row.get("rate_date")


def _crc_amount_sql(amount_field: str, currency_field: str):
    return f"""
        CASE
            WHEN UPPER(TRIM(COALESCE({currency_field}, 'CRC'))) IN ('USD', 'US$', '$', 'DOLLAR', 'DOLAR', 'DOLARES', 'DOLARES US')
            THEN COALESCE({amount_field}, 0) * %s
            ELSE COALESCE({amount_field}, 0)
        END
    """


def _iva_account_codes(cur):
    cur.execute("SELECT setting_key,setting_value FROM tax_settings WHERE setting_key IN ('IVA_DEBIT_ACCOUNT','IVA_CREDIT_ACCOUNT')")
    settings = {r["setting_key"]: r["setting_value"] for r in cur.fetchall()}
    debit_codes = list(dict.fromkeys([settings.get("IVA_DEBIT_ACCOUNT", "2108"), "2.1.02.03", "2108"]))
    credit_codes = list(dict.fromkeys([settings.get("IVA_CREDIT_ACCOUNT", "1131"), "1.1.13.99", "1131"]))
    return debit_codes, credit_codes


def _tax_amount_crc_sql(amount_field: str = "tax_amount"):
    return f"""
        CASE
            WHEN UPPER(COALESCE(currency_code,'CRC')) IN ('CRC','COLON','COLONES')
            THEN COALESCE({amount_field},0)
            ELSE COALESCE({amount_field},0) * COALESCE(NULLIF(exchange_rate,0),1)
        END
    """


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
def accountant_dashboard(
    period: str,
    company_code: str | None = None,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _valid_period(period)
    _ensure_schema(conn)
    company = _company_code(company_code, x_company_code)
    period_start, period_end = _period_bounds(period)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        work_items = _work_items(cur, period, period_start, period_end) if company == "MSL-CR" else []
        fx_rate, fx_date = _latest_fx_rate(cur)
        cur.execute("""SELECT COALESCE(SUM(l.debit),0) debit,COALESCE(SUM(l.credit),0) credit,
          COUNT(DISTINCT e.id) entries FROM accounting_entries e
          LEFT JOIN accounting_lines l ON l.entry_id=e.id
          WHERE e.company_code=%s AND e.period=%s AND e.workflow_status='POSTED'""", (company, period))
        ledger = cur.fetchone()
        if company == "MSL-CR":
            ar_amount = _crc_amount_sql("saldo_pendiente", "moneda")
            cur.execute(f"""SELECT COALESCE(SUM({ar_amount}),0) open_ar,
              COALESCE(SUM({ar_amount}) FILTER(WHERE fecha_vencimiento<CURRENT_DATE),0) overdue_ar,
              COUNT(*) open_ar_count,
              COUNT(*) FILTER(WHERE fecha_vencimiento<CURRENT_DATE) overdue_ar_count
              FROM collections
              WHERE COALESCE(saldo_pendiente,0)>0""", (fx_rate, fx_rate))
            ar = cur.fetchone()
            ap_amount = _crc_amount_sql("balance", "currency")
            cur.execute(f"""SELECT COALESCE(SUM({ap_amount}),0) open_ap,
              COALESCE(SUM({ap_amount}) FILTER(WHERE due_date<CURRENT_DATE),0) overdue_ap,
              COUNT(*) open_ap_count,
              COUNT(*) FILTER(WHERE due_date<CURRENT_DATE) overdue_ap_count
              FROM payment_obligations
              WHERE active=TRUE
                AND record_type='OBLIGATION'
                AND COALESCE(balance,0)>0""", (fx_rate, fx_rate))
            ap = cur.fetchone()
        else:
            ar = {"open_ar": 0, "overdue_ar": 0, "open_ar_count": 0, "overdue_ar_count": 0}
            ap = {"open_ap": 0, "overdue_ap": 0, "open_ap_count": 0, "overdue_ap_count": 0}
        cur.execute("""SELECT status,closed_by,closed_at,reopened_by,reopened_at FROM accounting_period_controls
          WHERE company_code=%s AND period=%s""", (company, period))
        period_control = cur.fetchone() or {"status":"OPEN"}
        cur.execute("""SELECT id,entry_date,description,origin,workflow_status,created_by,updated_at
          FROM accounting_entries WHERE company_code=%s AND period=%s ORDER BY updated_at DESC NULLS LAST,id DESC LIMIT 12""", (company, period))
        recent = cur.fetchall()

    deductions = sum(min(item["count"], 10) * ({"CRITICAL":5,"HIGH":2,"MEDIUM":1,"LOW":0.5}[item["priority"]]) for item in work_items)
    health = max(0, round(100 - deductions))
    return {"period":period,"health_score":health,"period_control":period_control,"work_items":work_items,
            "kpi_scope": {
                "as_of": date.today().isoformat(),
                "currency": "CRC",
                "fx_rate": float(fx_rate),
                "fx_date": fx_date.isoformat() if fx_date else None,
                "note": "Saldos abiertos actuales convertidos a CRC.",
            },
            "kpis":{"posted_entries":int(ledger["entries"] or 0),"debit":float(ledger["debit"] or 0),
                    "credit":float(ledger["credit"] or 0),"open_ar":float(ar["open_ar"] or 0),
                    "open_ar_count":int(ar["open_ar_count"] or 0),
                    "overdue_ar_count":int(ar["overdue_ar_count"] or 0),
                    "overdue_ar":float(ar["overdue_ar"] or 0),"open_ap":float(ap["open_ap"] or 0),
                    "open_ap_count":int(ap["open_ap_count"] or 0),
                    "overdue_ap_count":int(ap["overdue_ap_count"] or 0),
                    "overdue_ap":float(ap["overdue_ap"] or 0)},"recent_entries":recent}


def _robust_close_controls(cur, period):
    controls = {
        "unbalanced_entries": 0,
        "entries_without_lines": 0,
        "invalid_lines": 0,
        "non_posted_entries": 0,
        "tax_quality_issues": 0,
        "iva_difference_count": 0,
        "bank_open_items": 0,
        "bank_unclosed_statements": 0,
        "auxiliary_differences": 0,
        "auxiliary_unmapped": 0,
    }
    cur.execute("""SELECT COUNT(*) count FROM (SELECT e.id FROM accounting_entries e JOIN accounting_lines l ON l.entry_id=e.id
      WHERE e.period=%s GROUP BY e.id HAVING ABS(SUM(l.debit)-SUM(l.credit))>0.01) q""", (period,))
    controls["unbalanced_entries"] = int((cur.fetchone() or {}).get("count") or 0)
    cur.execute("""SELECT e.id FROM accounting_entries e LEFT JOIN accounting_lines l ON l.entry_id=e.id
      WHERE e.period=%s GROUP BY e.id HAVING COUNT(l.id)=0""", (period,))
    controls["entries_without_lines"] = len(cur.fetchall())
    cur.execute("""SELECT COUNT(*) count FROM accounting_lines l JOIN accounting_entries e ON e.id=l.entry_id
      WHERE e.period=%s AND ((COALESCE(l.debit,0)>0 AND COALESCE(l.credit,0)>0)
      OR (COALESCE(l.debit,0)=0 AND COALESCE(l.credit,0)=0))""", (period,))
    controls["invalid_lines"] = int((cur.fetchone() or {}).get("count") or 0)
    cur.execute("SELECT COUNT(*) count FROM accounting_entries WHERE period=%s AND workflow_status <> 'POSTED'", (period,))
    controls["non_posted_entries"] = int((cur.fetchone() or {}).get("count") or 0)
    cur.execute("""SELECT COUNT(*) count FROM tax_electronic_documents d WHERE TO_CHAR(issue_datetime,'YYYY-MM')=%s AND
      (xml_path IS NULL OR hacienda_status='PENDING' OR NOT EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id)
       OR EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id AND COALESCE(l.cabys_code,'')=''))""", (period,))
    controls["tax_quality_issues"] = int((cur.fetchone() or {}).get("count") or 0)
    start_date, end_date = _period_bounds(period)
    iva_debit_codes, iva_credit_codes = _iva_account_codes(cur)
    cur.execute(f"""SELECT direction,COALESCE(SUM({_tax_amount_crc_sql()}),0) tax
      FROM tax_electronic_documents
      WHERE issue_datetime >= %s
        AND issue_datetime < %s
        AND COALESCE(issue_datetime::date, CURRENT_DATE) <= CURRENT_DATE
      GROUP BY direction""", (start_date, end_date))
    tax = {r["direction"]: Decimal(str(r["tax"] or 0)) for r in cur.fetchall()}
    cur.execute("""SELECT account_code,COALESCE(SUM(debit),0) debit,COALESCE(SUM(credit),0) credit
      FROM accounting_lines l JOIN accounting_entries e ON e.id=l.entry_id
      WHERE e.entry_date >= %s AND e.entry_date < %s AND e.workflow_status='POSTED'
      AND (account_code = ANY(%s) OR account_code = ANY(%s))
      GROUP BY account_code""", (start_date, end_date, iva_debit_codes, iva_credit_codes))
    gl = {r["account_code"]: r for r in cur.fetchall()}
    fiscal_debit = tax.get("SALE", Decimal("0"))
    fiscal_credit = tax.get("PURCHASE", Decimal("0"))
    gl_debit = sum(
        Decimal(str((gl.get(code) or {}).get("credit") or 0)) - Decimal(str((gl.get(code) or {}).get("debit") or 0))
        for code in iva_debit_codes
    )
    gl_credit = sum(
        Decimal(str((gl.get(code) or {}).get("debit") or 0)) - Decimal(str((gl.get(code) or {}).get("credit") or 0))
        for code in iva_credit_codes
    )
    controls["iva_difference_count"] = sum(
        1 for diff in (
            fiscal_debit - gl_debit,
            fiscal_credit - gl_credit,
            (fiscal_debit - fiscal_credit) - (gl_debit - gl_credit),
        ) if abs(diff) > Decimal("0.01")
    )
    cur.execute("""SELECT COUNT(*) count FROM bank_reconciliation_statement_lines l
      JOIN bank_reconciliation_statements s ON s.id=l.statement_id
      WHERE s.statement_period=%s AND l.match_status='OPEN'""", (period,))
    controls["bank_open_items"] = int((cur.fetchone() or {}).get("count") or 0)
    cur.execute("""SELECT COUNT(*) count FROM bank_reconciliation_statements
      WHERE statement_period=%s AND status <> 'CLOSED'""", (period,))
    controls["bank_unclosed_statements"] = int((cur.fetchone() or {}).get("count") or 0)
    try:
        from routers.accounting_auxiliaries import reconcile_auxiliaries
        data = reconcile_auxiliaries(period=period, conn=cur.connection).get("data", [])
        controls["auxiliary_differences"] = sum(1 for row in data if row.get("status") in {"DIFFERENCE", "FX_REQUIRED"})
        controls["auxiliary_unmapped"] = sum(
            1 for row in data
            if row.get("status") == "UNMAPPED" and Decimal(str(row.get("auxiliary_balance") or 0)) != 0
        )
    except Exception:
        controls["auxiliary_differences"] = 1
    return controls


def _automatic_checks(cur, period):
    controls = _robust_close_controls(cur, period)
    bank_blockers = controls["bank_open_items"] + controls["bank_unclosed_statements"]
    aux_blockers = controls["auxiliary_differences"] + controls["auxiliary_unmapped"]
    tax_blockers = controls["tax_quality_issues"] + controls["iva_difference_count"]
    entry_blockers = controls["non_posted_entries"] + controls["unbalanced_entries"] + controls["entries_without_lines"] + controls["invalid_lines"]
    _, period_end = _period_bounds(period)
    fx_open = int(_scalar(cur, """SELECT COUNT(*) count FROM accounting_auxiliary_documents
      WHERE status='OPEN'
        AND UPPER(COALESCE(currency_code,'CRC'))<>'CRC'
        AND COALESCE(issue_date,due_date,CURRENT_DATE)<%s""", (period_end,)))
    return {
        "SOURCE_SYNC": {"ready": True, "detail": "Primero pulse Sincronizar ERP; valida que facturas, bancos, pagos, XML y planillas esten actualizados."},
        "ENTRY_WORKFLOW": {"ready": entry_blockers == 0, "detail": "Listo" if entry_blockers == 0 else f"Resolver {entry_blockers} asientos borrador, descuadrados, sin lineas o invalidos."},
        "BANK_RECONCILIATION": {"ready": bank_blockers == 0, "detail": "Listo" if bank_blockers == 0 else f"Cerrar bancos: {controls['bank_open_items']} partidas abiertas y {controls['bank_unclosed_statements']} extractos sin cierre."},
        "AR_REVIEW": {"ready": True, "detail": "Revise clientes vencidos, disputas y posibilidad real de cobro."},
        "AP_REVIEW": {"ready": True, "detail": "Revise proveedores vencidos, soportes y pagos pendientes."},
        "AUX_RECONCILIATION": {"ready": aux_blockers == 0, "detail": "Listo" if aux_blockers == 0 else f"Cuadrar {aux_blockers} diferencias/sin mapeo entre auxiliares y mayor."},
        "TAX_REVIEW": {"ready": tax_blockers == 0, "detail": "Listo" if tax_blockers == 0 else f"Revisar {controls['tax_quality_issues']} documentos fiscales y {controls['iva_difference_count']} diferencias de IVA."},
        "FX_REVALUATION": {"ready": fx_open == 0, "detail": "Listo" if fx_open == 0 else f"Revaluar {fx_open} documentos abiertos en USD."},
        "FINANCIAL_STATEMENTS": {"ready": True, "detail": "Genere y revise balance, resultados, flujo y variaciones antes de aprobar."},
        "MANAGEMENT_APPROVAL": {"ready": False, "detail": "Debe aprobar Gerencia/Finance para bloquear el periodo."},
    }

def _json_default(value):
    return __import__("json").dumps(value, default=str)


def _validation_alert_summary(cur, period):
    backfill_missing_bank_accounts(cur)
    critical = []
    warnings = []
    robust = _robust_close_controls(cur, period)

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

    robust_messages = (
        ("TAX_XML_PENDING", "XML/calidad fiscal pendiente", "tax_quality_issues", "documentos fiscales con XML, Hacienda, lineas o CAByS pendiente"),
        ("IVA_NOT_REVIEWED", "IVA sin revisar o descuadrado", "iva_difference_count", "diferencias entre IVA documental y contable"),
        ("BANK_RECON_OPEN_ITEMS", "Bancos sin conciliar", "bank_open_items", "partidas abiertas en extractos bancarios"),
        ("BANK_RECON_NOT_CLOSED", "Conciliacion bancaria sin cierre", "bank_unclosed_statements", "extractos bancarios sin cierre"),
        ("AUXILIARY_DIFFERENCE", "Auxiliares descuadrados", "auxiliary_differences", "auxiliares no conciliados contra mayor"),
        ("AUXILIARY_UNMAPPED", "Auxiliares sin mapeo", "auxiliary_unmapped", "auxiliares con saldo sin cuenta de control"),
    )
    for code, title, key, detail in robust_messages:
        count = int(robust.get(key) or 0)
        if count:
            critical.append({
                "code": code,
                "title": title,
                "entity_id": period,
                "message": f"{count} {detail}.",
                "metadata": {"count": count, "period": period},
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


def _mitigate_reviewed_validation_alerts(validation, checklist):
    reviewed_codes = {
        item["item_code"]
        for item in checklist
        if item.get("status") in {"COMPLETE", "NOT_APPLICABLE"}
    }
    alert_to_checklist = {
        "TAX_XML_PENDING": "TAX_REVIEW",
        "IVA_NOT_REVIEWED": "TAX_REVIEW",
        "AUXILIARY_DIFFERENCE": "AUX_RECONCILIATION",
        "AUXILIARY_UNMAPPED": "AUX_RECONCILIATION",
    }
    remaining_critical = []
    mitigated = []
    for alert in validation.get("critical", []):
        checklist_code = alert_to_checklist.get(alert.get("code"))
        if checklist_code and checklist_code in reviewed_codes:
            mitigated.append({
                **alert,
                "level": "warning",
                "mitigated_by_checklist": checklist_code,
                "message": f"{alert.get('message', '')} Revision completada en checklist de cierre.",
            })
        else:
            remaining_critical.append(alert)
    warnings = [*validation.get("warnings", []), *mitigated]
    return {
        **validation,
        "critical": remaining_critical,
        "warnings": warnings,
        "counts": {
            "critical": len(remaining_critical),
            "warning": len(warnings),
            "info": validation.get("counts", {}).get("info", 0),
        },
    }


def _checklist_item_blocks_close(item):
    status = item.get("status")
    if status in {"COMPLETE", "NOT_APPLICABLE"}:
        return False
    if item.get("mandatory"):
        return True
    return False


def _close_snapshot(cur, period, company="MSL-CR"):
    _seed_checklist(cur, period, company)
    checks = _automatic_checks(cur, period) if company == "MSL-CR" else {}
    cur.execute("""
        SELECT * FROM accounting_close_checklist
        WHERE company_code=%s AND period=%s
        ORDER BY sequence
    """, (company, period))
    checklist = []
    for row in cur.fetchall():
        checklist.append({
            **row,
            "automatic_check": checks.get(row["item_code"], {"ready": False, "detail": "Revision manual"}),
        })

    blockers = [item for item in checklist if item["mandatory"] and _checklist_item_blocks_close(item)]
    validation = _validation_alert_summary(cur, period) if company == "MSL-CR" else {
        "counts": {"critical": 0, "warning": 0, "info": 0},
        "critical": [],
        "warnings": [],
    }
    if company == "MSL-CR":
        validation = _mitigate_reviewed_validation_alerts(validation, checklist)
    cur.execute("""
        SELECT COALESCE(SUM(l.debit),0) debit, COALESCE(SUM(l.credit),0) credit,
               COUNT(DISTINCT e.id) entries
        FROM accounting_entries e
        LEFT JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.company_code=%s AND e.period=%s
    """, (company, period))
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
def close_checklist(
    period: str,
    company_code: str | None = None,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _valid_period(period); _ensure_schema(conn)
    company = _company_code(company_code, x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _seed_checklist(cur, period, company); conn.commit()
        checks = _automatic_checks(cur, period) if company == "MSL-CR" else {}
        cur.execute("SELECT * FROM accounting_close_checklist WHERE company_code=%s AND period=%s ORDER BY sequence", (company, period))
        rows = cur.fetchall()
        cur.execute("SELECT status FROM accounting_period_controls WHERE company_code=%s AND period=%s", (company, period))
        control = cur.fetchone() or {"status":"OPEN"}
    data=[]
    for row in rows:
        data.append({**row,"automatic_check":checks.get(row["item_code"],{"ready":False,"detail":"Revisión manual"})})
    blockers=[item for item in data if item["mandatory"] and item["status"] not in {"COMPLETE","NOT_APPLICABLE"}]
    return {"period":period,"period_status":control["status"],"ready_to_close":not blockers,
            "completed":len(data)-len(blockers),"total":len(data),"data":data}


@router.get("/guided-close")
def guided_monthly_close(
    period: str,
    company_code: str | None = None,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _valid_period(period)
    _ensure_schema(conn)
    company = _company_code(company_code, x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        checklist, validation, summary, blockers = _close_snapshot(cur, period, company)
        status = "READY" if not blockers and validation["counts"]["critical"] == 0 else "DRAFT"
        cur.execute("""
            INSERT INTO accounting_monthly_close_runs(
                company_code, period, status, checklist_snapshot, validation_snapshot, summary
            )
            VALUES(%s, %s, %s, %s, %s, %s)
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
            company,
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
            WHERE company_code=%s AND period=%s
        """, (company, period))
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
def close_guided_month(
    period: str,
    payload: GuidedClosePayload,
    company_code: str | None = None,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _valid_period(period)
    _ensure_schema(conn)
    company = _company_code(company_code, x_company_code)
    user = (payload.user or "unknown").strip() or "unknown"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        checklist, validation, summary, blockers = _close_snapshot(cur, period, company)
        if blockers:
            raise HTTPException(409, f"El checklist obligatorio tiene {len(blockers)} pasos pendientes.")
        if validation["counts"]["critical"]:
            raise HTTPException(409, f"Existen {validation['counts']['critical']} alertas criticas antes del cierre.")
        cur.execute("""
            SELECT *
            FROM accounting_period_controls
            WHERE company_code=%s AND period=%s
            FOR UPDATE
        """, (company, period))
        before = cur.fetchone()
        if before and before.get("status") == "CLOSED":
            raise HTTPException(409, f"El periodo {period} ya esta cerrado.")
        cur.execute("""
            INSERT INTO accounting_period_controls(company_code, period, status, closed_by, closed_at)
            VALUES(%s, %s, 'CLOSED', %s, NOW())
            ON CONFLICT(company_code, period) DO UPDATE SET
                status='CLOSED',
                closed_by=EXCLUDED.closed_by,
                closed_at=NOW(),
                updated_at=NOW()
            RETURNING *
        """, (company, period, user))
        control = cur.fetchone()
        cur.execute("""
            INSERT INTO accounting_monthly_close_runs(
                company_code, period, status, closed_by, closed_at, notes,
                checklist_snapshot, validation_snapshot, summary
            )
            VALUES(%s, %s, 'CLOSED', %s, NOW(), %s, %s, %s, %s)
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
            company,
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
def update_checklist(
    period: str,
    item_code: str,
    payload: ChecklistUpdate,
    company_code: str | None = None,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _valid_period(period); _ensure_schema(conn)
    company = _company_code(company_code, x_company_code)
    status=payload.status.upper()
    if status not in {"PENDING","IN_PROGRESS","COMPLETE","NOT_APPLICABLE"}: raise HTTPException(400,"Estado inválido")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if company == "MSL-CR" and status == "COMPLETE" and item_code in {"ENTRY_WORKFLOW"}:
            validation = _automatic_checks(cur, period).get(item_code, {})
            if not validation.get("ready"):
                raise HTTPException(409, f"El control automático aún presenta incidencias: {validation.get('detail','revisión pendiente')}")
        _seed_checklist(cur, period, company)
        cur.execute("""UPDATE accounting_close_checklist SET status=%s,notes=%s,evidence=%s,
          completed_by=CASE WHEN %s IN ('COMPLETE','NOT_APPLICABLE') THEN %s ELSE NULL END,
          completed_at=CASE WHEN %s IN ('COMPLETE','NOT_APPLICABLE') THEN NOW() ELSE NULL END,updated_at=NOW()
          WHERE company_code=%s AND period=%s AND item_code=%s RETURNING *""",
                    (status,payload.notes,Json(payload.evidence),status,payload.user,status,company,period,item_code))
        row=cur.fetchone()
        if not row: raise HTTPException(404,"Paso de cierre no encontrado")
    conn.commit(); return {"message":"Checklist actualizado","item":row}


@router.get("/search")
def global_search(q: str = Query("", min_length=0), limit: int = Query(30, ge=5, le=100), conn=Depends(get_db)):
    _ensure_schema(conn); term=(q or "").strip(); pattern=f"%{term}%"; results=[]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if len(term) < 2:
            cur.execute("""SELECT id::text reference,'ENTRY' result_type,description title,
              CONCAT(period,' · ',origin,' · ',workflow_status) subtitle,updated_at sort_date
              FROM accounting_entries
              ORDER BY updated_at DESC NULLS LAST, id DESC LIMIT %s""", (limit,))
            rows = cur.fetchall()
            return {"query": q, "data": rows, "count": len(rows)}
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
