from decimal import Decimal
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from database import get_db
from routers.accounting import _ensure_accounting_professional_schema


router = APIRouter(prefix="/accounting/ai", tags=["Accounting AI"])


class AccountingAIRequest(BaseModel):
    period: str | None = None
    period_from: str | None = None
    period_to: str | None = None
    origin: str | None = None
    question: str | None = None
    language: str = "ES"


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _rows(rows):
    return [dict(row) for row in rows or []]


def _period_ok(value):
    return not value or re.match(r"^\d{4}-\d{2}$", value)


def _build_filters(payload: AccountingAIRequest):
    for value in (payload.period, payload.period_from, payload.period_to):
        if not _period_ok(value):
            raise HTTPException(400, "Periods must use YYYY-MM")
    conditions = []
    params = []
    if payload.period:
        conditions.append("e.period = %s")
        params.append(payload.period)
    if payload.period_from:
        conditions.append("e.period >= %s")
        params.append(payload.period_from)
    if payload.period_to:
        conditions.append("e.period <= %s")
        params.append(payload.period_to)
    if payload.origin and payload.origin != "TODOS":
        conditions.append("e.origin = %s")
        params.append(payload.origin)
    return ("WHERE " + " AND ".join(conditions) if conditions else "", params)


def _money(value):
    return float(value or 0)


def _collect_context(conn, payload: AccountingAIRequest):
    _ensure_accounting_professional_schema(conn)
    where, params = _build_filters(payload)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT
                COALESCE(SUM(l.debit), 0) AS total_debit,
                COALESCE(SUM(l.credit), 0) AS total_credit,
                ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2) AS difference,
                COUNT(DISTINCT e.id) AS entry_count,
                COUNT(l.id) AS line_count,
                MIN(e.entry_date) AS first_date,
                MAX(e.entry_date) AS last_date
            FROM accounting_entries e
            LEFT JOIN accounting_lines l ON l.entry_id = e.id
            {where}
            """,
            params,
        )
        totals = dict(cur.fetchone() or {})

        cur.execute(
            f"""
            SELECT
                l.account_code,
                l.account_name,
                COALESCE(SUM(l.debit), 0) AS debit,
                COALESCE(SUM(l.credit), 0) AS credit,
                ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2) AS balance
            FROM accounting_entries e
            JOIN accounting_lines l ON l.entry_id = e.id
            {where}
            GROUP BY l.account_code, l.account_name
            ORDER BY ABS(ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2)) DESC
            LIMIT 20
            """,
            params,
        )
        accounts = _rows(cur.fetchall())

        cur.execute(
            f"""
            SELECT
                COALESCE(e.origin, 'MANUAL') AS origin,
                COUNT(DISTINCT e.id) AS entry_count,
                COALESCE(SUM(l.debit), 0) AS debit,
                COALESCE(SUM(l.credit), 0) AS credit,
                ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2) AS difference
            FROM accounting_entries e
            LEFT JOIN accounting_lines l ON l.entry_id = e.id
            {where}
            GROUP BY COALESCE(e.origin, 'MANUAL')
            ORDER BY ABS(ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2)) DESC
            """,
            params,
        )
        origins = _rows(cur.fetchall())

        cur.execute(
            f"""
            SELECT COALESCE(e.workflow_status, 'POSTED') AS workflow_status, COUNT(*) AS count
            FROM accounting_entries e
            {where}
            GROUP BY COALESCE(e.workflow_status, 'POSTED')
            ORDER BY workflow_status
            """,
            params,
        )
        statuses = _rows(cur.fetchall())

        cur.execute(
            f"""
            SELECT e.id, e.period, e.entry_date, e.origin, e.origin_id, e.description,
                   COALESCE(SUM(l.debit), 0) AS total_debit,
                   COALESCE(SUM(l.credit), 0) AS total_credit,
                   ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2) AS difference
            FROM accounting_entries e
            JOIN accounting_lines l ON l.entry_id = e.id
            {where}
            GROUP BY e.id, e.period, e.entry_date, e.origin, e.origin_id, e.description
            HAVING ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2) <> 0
            ORDER BY ABS(ROUND((COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0))::numeric, 2)) DESC
            LIMIT 25
            """,
            params,
        )
        unbalanced = _rows(cur.fetchall())

        cur.execute(
            f"""
            SELECT l.id, l.entry_id, e.period, e.origin, l.account_code, l.account_name, l.debit, l.credit
            FROM accounting_lines l
            JOIN accounting_entries e ON e.id = l.entry_id
            {where}
              {"AND" if where else "WHERE"} (
                    (COALESCE(l.debit, 0) > 0 AND COALESCE(l.credit, 0) > 0)
                 OR (COALESCE(l.debit, 0) = 0 AND COALESCE(l.credit, 0) = 0)
              )
            ORDER BY l.id DESC
            LIMIT 25
            """,
            params,
        )
        invalid_lines = _rows(cur.fetchall())

        cur.execute(
            f"""
            SELECT e.origin, e.origin_id, COUNT(*) AS count
            FROM accounting_entries e
            {where}
              {"AND" if where else "WHERE"} e.origin_id IS NOT NULL
            GROUP BY e.origin, e.origin_id
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 25
            """,
            params,
        )
        duplicates = _rows(cur.fetchall())

    return {
        "filters": {
            "period": payload.period,
            "period_from": payload.period_from,
            "period_to": payload.period_to,
            "origin": payload.origin,
        },
        "totals": totals,
        "top_accounts": accounts,
        "by_origin": origins,
        "workflow_status": statuses,
        "exceptions": {
            "unbalanced_entries": unbalanced,
            "invalid_lines": invalid_lines,
            "duplicate_origin_entries": duplicates,
        },
    }


def _fallback_analysis(context, language):
    es = str(language or "ES").upper().startswith("ES")
    totals = context.get("totals") or {}
    debit = _money(totals.get("total_debit"))
    credit = _money(totals.get("total_credit"))
    diff = _money(totals.get("difference"))
    accounts = context.get("top_accounts") or []
    origins = context.get("by_origin") or []
    exceptions = context.get("exceptions") or {}

    if es:
        lines = [
            "Resumen ejecutivo",
            f"El rango analizado contiene {int(totals.get('entry_count') or 0)} asientos y {int(totals.get('line_count') or 0)} lineas. Total Debe: {debit:,.2f}; Total Haber: {credit:,.2f}; diferencia neta: {diff:,.2f}.",
            "",
            "Explicacion de diferencias",
        ]
        if round(diff, 2) == 0:
            lines.append("La partida doble esta cuadrada en el total del periodo. La revision debe enfocarse en clasificacion de cuentas, IVA, bancos y duplicidades de origen.")
        else:
            lines.append("Existe una diferencia entre Debe y Haber. Priorice los asientos descuadrados, lineas sin monto o lineas con Debe y Haber simultaneamente.")
        lines.extend(["", "Cuentas con mayor impacto"])
        for row in accounts[:8]:
            lines.append(f"- {row.get('account_code')} {row.get('account_name')}: Debe { _money(row.get('debit')):,.2f}, Haber { _money(row.get('credit')):,.2f}, saldo { _money(row.get('balance')):,.2f}.")
        lines.extend(["", "Origenes a revisar"])
        for row in origins[:8]:
            lines.append(f"- {row.get('origin')}: {int(row.get('entry_count') or 0)} asientos, diferencia { _money(row.get('difference')):,.2f}.")
        lines.extend(["", "Sugerencias"])
        if exceptions.get("unbalanced_entries"):
            lines.append("- Abrir los asientos descuadrados y comparar el documento fuente contra las lineas contables.")
        if exceptions.get("duplicate_origin_entries"):
            lines.append("- Revisar origenes duplicados antes de cierre para evitar doble reconocimiento.")
        if exceptions.get("invalid_lines"):
            lines.append("- Corregir lineas con Debe/Haber simultaneo o sin monto.")
        lines.append("- Confirmar que ITP y Collections usen el banco contable correcto para que el auxiliar bancario cuadre.")
        lines.append("- Documentar cualquier ajuste manual con razon y usuario responsable.")
        return "\n".join(lines)

    return (
        "Executive summary\n"
        f"The selected scope includes {int(totals.get('entry_count') or 0)} entries and "
        f"{int(totals.get('line_count') or 0)} lines. Debit: {debit:,.2f}; Credit: {credit:,.2f}; "
        f"net variance: {diff:,.2f}.\n\n"
        "Suggested review\n"
        "- Start with unbalanced entries, invalid lines and duplicate source entries.\n"
        "- Confirm ITP and Collections payments use the correct bank account.\n"
        "- Document manual adjustments with reason and responsible user."
    )


def _ai_analysis(context, question, language):
    from ai.maritime_ai import _get_openai_client

    client = _get_openai_client()
    prompt = f"""
You are PORTIA, the senior accounting controller assistant for ERP-SOM, a Costa Rican maritime ERP.
Use only the data below. Do not invent invoices, entries, laws, or balances.
Do not post, modify, delete, or approve accounting entries. Give suggestions and explain differences.
Language: {"Spanish" if str(language).upper().startswith("ES") else "English"}.
Be concrete: mention exact accounts, origins, entry ids when the context includes them, and explain why the variance may exist.
If the ledger is balanced, still identify classification, bank, duplicate-source, IVA and closing risks.
Every correction suggestion must be auditable: say what to review, what evidence to compare, and who should approve.

User question:
{question or "Explain accounting differences and suggest what to review before closing."}

Accounting context JSON:
{json.dumps(context, ensure_ascii=False, default=_json_default)}

Return an executive but practical answer with these headings:
1. Resumen ejecutivo / Executive summary
2. Explicacion de diferencias / Variance explanation
3. Posibles causas / Likely causes
4. Cuentas y asientos a revisar / Accounts and entries to review
5. Sugerencias de correccion / Correction suggestions
6. Proximos pasos de control / Control next steps
"""
    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=1800,
    )
    return response.output_text.strip()


@router.post("/analyze")
def analyze_accounting(payload: AccountingAIRequest, conn=Depends(get_db)):
    context = _collect_context(conn, payload)
    mode = "ai"
    try:
        analysis = _ai_analysis(context, payload.question, payload.language)
    except Exception as exc:
        mode = "fallback"
        analysis = _fallback_analysis(context, payload.language)
        context["ai_error"] = str(exc)
    return {
        "status": "ok",
        "mode": mode,
        "analysis": analysis,
        "context": context,
    }
