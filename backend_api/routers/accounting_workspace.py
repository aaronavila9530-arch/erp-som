from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel, Field

from database import get_db
from routers.accounting import _ensure_accounting_professional_schema
from routers.accounting_tax import _ensure_schema as _ensure_tax_schema


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


def _work_items(cur, period):
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

    overdue_ar = int(_scalar(cur, """SELECT COUNT(*) count FROM collections
        WHERE COALESCE(saldo_pendiente,0)>0 AND fecha_vencimiento<CURRENT_DATE"""))
    if overdue_ar:
        items.append({"code":"OVERDUE_AR","area":"COLLECTIONS","priority":"HIGH","title":"Facturas de clientes vencidas",
                      "count":overdue_ar,"action":"AUXILIARIES_CUSTOMER"})
    disputes = int(_scalar(cur, "SELECT COUNT(*) count FROM collections WHERE disputada=TRUE AND COALESCE(saldo_pendiente,0)>0"))
    if disputes:
        items.append({"code":"DISPUTED_AR","area":"COLLECTIONS","priority":"HIGH","title":"Cuentas por cobrar en disputa",
                      "count":disputes,"action":"AUXILIARIES_CUSTOMER"})
    overdue_ap = int(_scalar(cur, """SELECT COUNT(*) count FROM payment_obligations
        WHERE active=TRUE AND record_type='OBLIGATION' AND COALESCE(balance,0)>0 AND due_date<CURRENT_DATE"""))
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
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        work_items = _work_items(cur, period)
        cur.execute("""SELECT COALESCE(SUM(l.debit),0) debit,COALESCE(SUM(l.credit),0) credit,
          COUNT(DISTINCT e.id) entries FROM accounting_entries e
          LEFT JOIN accounting_lines l ON l.entry_id=e.id
          WHERE e.period=%s AND e.workflow_status='POSTED'""", (period,))
        ledger = cur.fetchone()
        cur.execute("""SELECT COALESCE(SUM(saldo_pendiente),0) open_ar,
          COALESCE(SUM(saldo_pendiente) FILTER(WHERE fecha_vencimiento<CURRENT_DATE),0) overdue_ar FROM collections""")
        ar = cur.fetchone()
        cur.execute("""SELECT COALESCE(SUM(balance),0) open_ap,
          COALESCE(SUM(balance) FILTER(WHERE due_date<CURRENT_DATE),0) overdue_ap
          FROM payment_obligations WHERE active=TRUE AND record_type='OBLIGATION' AND COALESCE(balance,0)>0""")
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
            "kpis":{"posted_entries":int(ledger["entries"] or 0),"debit":float(ledger["debit"] or 0),
                    "credit":float(ledger["credit"] or 0),"open_ar":float(ar["open_ar"] or 0),
                    "overdue_ar":float(ar["overdue_ar"] or 0),"open_ap":float(ap["open_ap"] or 0),
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
