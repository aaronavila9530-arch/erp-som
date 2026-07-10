from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header
)
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import date
import os
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import get_db
from rbac_service import has_permission


router = APIRouter(
    prefix="/accounting",
    tags=["Accounting"]
)

# ============================================================
# RBAC GUARD
# ============================================================
def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(
                status_code=403,
                detail="No autorizado"
            )
    return checker


def _accounting_entry_stats(conn):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) AS total_entries,
            MAX(period) AS latest_period
        FROM accounting_entries
    """)
    stats = cur.fetchone() or {}

    cur.execute("""
        SELECT period, COUNT(*) AS count
        FROM accounting_entries
        GROUP BY period
        ORDER BY period DESC
        LIMIT 12
    """)
    periods = cur.fetchall()

    return {
        "total_entries": int(stats.get("total_entries") or 0),
        "latest_period": stats.get("latest_period"),
        "period_counts": [
            {"period": row["period"], "count": int(row["count"] or 0)}
            for row in periods
        ]
    }


def _report_title(report: str | None):
    titles = {
        "ASIENTOS": "Asientos contables",
        "MAYOR": "Mayor general",
        "BC": "Balance de comprobacion",
        "ESF": "Estado de situacion financiera",
        "ER": "Estado de resultados",
        "FC": "Flujo de caja"
    }
    key = (report or "ASIENTOS").upper()
    return titles.get(key, key)


def _fetch_accounting_report_lines(
    conn,
    period: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    origin: str | None = None,
    account_code: str | None = None
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    conditions = []
    params = []

    if period:
        conditions.append("e.period = %s")
        params.append(period)

    if period_from:
        conditions.append("e.period >= %s")
        params.append(period_from)

    if period_to:
        conditions.append("e.period <= %s")
        params.append(period_to)

    if origin and origin != "TODOS":
        conditions.append("e.origin = %s")
        params.append(origin)

    if account_code and account_code != "TODOS":
        conditions.append("l.account_code = %s")
        params.append(account_code)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cur.execute(f"""
        SELECT
            e.entry_date,
            e.id AS entry_id,
            e.period,
            e.origin,
            e.origin_id,
            e.description AS entry_description,
            l.account_code,
            l.account_name,
            l.line_description,
            l.debit,
            l.credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        {where_clause}
        ORDER BY e.period DESC, e.entry_date DESC, e.id DESC, l.id ASC
    """, params)

    return cur.fetchall()


def _report_filename(extension: str, report: str | None, period: str | None, period_from: str | None, period_to: str | None):
    scope = period or (f"{period_from or 'inicio'}_{period_to or 'fin'}" if period_from or period_to else "todos")
    safe_report = (report or "ASIENTOS").lower().replace(" ", "_")
    return f"accounting_{safe_report}_{scope}.{extension}"


@router.get("/periods")
def get_accounting_periods(conn=Depends(get_db)):
    """
    Devuelve solamente los periodos que realmente tienen movimientos contables.
    Evita mostrar meses futuros o meses sin data en Accounting.
    """
    current_period = date.today().strftime("%Y-%m")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT period, COUNT(*) AS count
        FROM accounting_entries
        WHERE period IS NOT NULL
          AND period ~ '^[0-9]{4}-[0-9]{2}$'
          AND period >= '2025-01'
          AND period <= %s
        GROUP BY period
        HAVING COUNT(*) > 0
        ORDER BY period ASC
    """, (current_period,))
    rows = cur.fetchall()
    return {
        "data": [row["period"] for row in rows],
        "period_counts": [
            {"period": row["period"], "count": int(row["count"] or 0)}
            for row in rows
        ]
    }


@router.post("/manual-entry")
def create_manual_entry(payload: dict, conn=Depends(get_db)):
    """
    payload:
    {
        entry_date,
        description,
        lines: [
            {account_code, account_name, debit, credit, line_description}
        ]
    }
    """

    lines = payload.get("lines", [])
    if not lines:
        raise HTTPException(400, "No accounting lines provided")

    total_debit = sum(l.get("debit", 0) for l in lines)
    total_credit = sum(l.get("credit", 0) for l in lines)

    if round(total_debit, 2) != round(total_credit, 2):
        raise HTTPException(400, "Entry does not balance")

    entry_date = date.fromisoformat(payload["entry_date"])
    period = entry_date.strftime("%Y-%m")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO accounting_entries
        (entry_date, period, description, origin)
        VALUES (%s, %s, %s, 'MANUAL')
        RETURNING id
    """, (
        entry_date,
        period,
        payload.get("description")
    ))

    entry_id = cur.fetchone()["id"]

    for l in lines:
        cur.execute("""
            INSERT INTO accounting_lines
            (entry_id, account_code, account_name, debit, credit, line_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            entry_id,
            l["account_code"],
            l["account_name"],
            l.get("debit", 0),
            l.get("credit", 0),
            l.get("line_description")
        ))

    conn.commit()
    return {"status": "ok", "entry_id": entry_id}



@router.post("/reverse/{entry_id}")
def reverse_entry(entry_id: int, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1️⃣ Validar asiento original
    cur.execute("""
        SELECT *
        FROM accounting_entries
        WHERE id = %s
          AND COALESCE(reversed, FALSE) = FALSE
    """, (entry_id,))
    entry = cur.fetchone()

    if not entry:
        raise HTTPException(
            status_code=400,
            detail="El asiento no existe o ya fue revertido"
        )

    # 2️⃣ Traer líneas originales
    cur.execute("""
        SELECT *
        FROM accounting_lines
        WHERE entry_id = %s
    """, (entry_id,))
    lines = cur.fetchall()

    if not lines:
        raise HTTPException(400, "El asiento no tiene líneas")

    # 3️⃣ Crear asiento de reverso (NO marcado como reversed)
    cur.execute("""
        INSERT INTO accounting_entries
        (entry_date, period, description, origin, origin_id, reversed)
        VALUES (CURRENT_DATE, %s, %s, 'REVERSAL', %s, FALSE)
        RETURNING id
    """, (
        entry["period"],
        f"Asiento de reversa del asiento {entry_id}",
        entry_id
    ))
    reversal_id = cur.fetchone()["id"]

    # 4️⃣ Insertar líneas INVERTIDAS
    for l in lines:
        cur.execute("""
            INSERT INTO accounting_lines
            (entry_id, account_code, account_name, debit, credit, line_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            reversal_id,
            l["account_code"],
            l["account_name"],
            l["credit"],   # 👈 INVERTIDO
            l["debit"],    # 👈 INVERTIDO
            f"Reverso de línea {l['id']}"
        ))

    # 5️⃣ Marcar SOLO el original como revertido
    cur.execute("""
        UPDATE accounting_entries
        SET reversed = TRUE,
            reversal_entry_id = %s
        WHERE id = %s
    """, (reversal_id, entry_id))

    conn.commit()

    return {
        "status": "ok",
        "original_entry_id": entry_id,
        "reversal_entry_id": reversal_id
    }




# ============================================================
# CHART OF ACCOUNTS (Catalogo Contable)
# ============================================================
@router.get("/accounts")
def get_accounting_accounts(conn=Depends(get_db)):
    """
    Devuelve el catálogo contable desde accounting_ledger
    para uso en combobox (UI / Popup de ajustes)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT DISTINCT
            account_code,
            account_name,
            account_type,
            account_level,
            parent_account
        FROM accounting_ledger
        WHERE account_code IS NOT NULL
        ORDER BY account_code
    """

    cur.execute(query)
    rows = cur.fetchall()

    return {
        "data": rows
    }


# ============================================================
# GET SINGLE ACCOUNTING ENTRY (FOR POPUP EDIT)
# ============================================================
@router.get("/entry/{entry_id}")
def get_accounting_entry(
    entry_id: int,
    conn=Depends(get_db)
):
    """
    Devuelve un asiento contable completo (cabecera + líneas)
    para edición en popup
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # 1. Traer cabecera
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            id AS entry_id,
            entry_date,
            period,
            description,
            origin,
            origin_id
        FROM accounting_entries
        WHERE id = %s
    """, (entry_id,))

    entry = cur.fetchone()

    if not entry:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")

    # --------------------------------------------------------
    # 2. Traer líneas
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            id AS line_id,
            account_code,
            account_name,
            debit,
            credit,
            line_description
        FROM accounting_lines
        WHERE entry_id = %s
        ORDER BY id
    """, (entry_id,))

    lines = cur.fetchall()

    # --------------------------------------------------------
    # 3. Respuesta final
    # --------------------------------------------------------
    return {
        "entry_id": entry["entry_id"],
        "entry_date": entry["entry_date"],
        "period": entry["period"],
        "description": entry["description"],
        "origin": entry["origin"],
        "origin_id": entry["origin_id"],
        "lines": [
            {
                "line_id": l["line_id"],
                "account_code": l["account_code"],
                "account_name": l["account_name"],
                "debit": float(l["debit"] or 0),
                "credit": float(l["credit"] or 0),
                "line_description": l["line_description"]
            }
            for l in lines
        ]
    }


# ============================================================
# UPDATE ACCOUNTING ENTRY (POPUP EDIT)
# ============================================================
@router.put("/entry/{entry_id}")
def update_accounting_entry(
    entry_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    """
    Actualiza descripción del asiento y líneas contables.
    Valida partida doble.
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    description = payload.get("description")
    lines = payload.get("lines", [])

    if not lines:
        raise HTTPException(status_code=400, detail="No se enviaron líneas")

    # --------------------------------------------------------
    # 1. VALIDACIONES CONTABLES
    # --------------------------------------------------------
    total_debit = 0
    total_credit = 0

    for line in lines:
        debit = float(line.get("debit") or 0)
        credit = float(line.get("credit") or 0)

        if debit > 0 and credit > 0:
            raise HTTPException(
                status_code=400,
                detail="Una línea no puede tener Debe y Haber simultáneamente"
            )

        if debit < 0 or credit < 0:
            raise HTTPException(
                status_code=400,
                detail="Valores negativos no permitidos"
            )

        total_debit += debit
        total_credit += credit

    if round(total_debit, 2) != round(total_credit, 2):
        raise HTTPException(
            status_code=400,
            detail="La partida no está balanceada (Debe ≠ Haber)"
        )

    # --------------------------------------------------------
    # 2. VALIDAR QUE EL ASIENTO EXISTE
    # --------------------------------------------------------
    cur.execute(
        "SELECT id FROM accounting_entries WHERE id = %s",
        (entry_id,)
    )
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Asiento no encontrado")

    # --------------------------------------------------------
    # 3. ACTUALIZAR CABECERA
    # --------------------------------------------------------
    if description is not None:
        cur.execute("""
            UPDATE accounting_entries
            SET description = %s
            WHERE id = %s
        """, (description, entry_id))

    # --------------------------------------------------------
    # 4. ACTUALIZAR LÍNEAS
    # --------------------------------------------------------
    for line in lines:
        line_id = line.get("line_id")

        if not line_id:
            raise HTTPException(
                status_code=400,
                detail="line_id es obligatorio"
            )

        # validar cuenta contable
        cur.execute("""
            SELECT account_name
            FROM accounting_ledger
            WHERE account_code = %s
            LIMIT 1
        """, (line["account_code"],))

        acc = cur.fetchone()
        if not acc:
            raise HTTPException(
                status_code=400,
                detail=f"Cuenta contable inválida: {line['account_code']}"
            )

        cur.execute("""
            UPDATE accounting_lines
            SET
                account_code = %s,
                account_name = %s,
                debit = %s,
                credit = %s,
                line_description = %s
            WHERE id = %s
              AND entry_id = %s
        """, (
            line["account_code"],
            acc["account_name"],
            line.get("debit", 0),
            line.get("credit", 0),
            line.get("line_description"),
            line_id,
            entry_id
        ))

    conn.commit()

    return {
        "status": "ok",
        "message": "Asiento actualizado correctamente"
    }


@router.post("/sync/collections")
def sync_collections(conn=Depends(get_db)):
    from services.accounting_auto import sync_collections_to_accounting

    sync_collections_to_accounting(conn)

    return {
        "status": "ok",
        "message": "Collections sincronizadas con Accounting"
    }



@router.post("/sync/cash-app")
def sync_cash_app(conn=Depends(get_db)):
    try:
        from services.accounting_auto import sync_cash_app_to_accounting
        sync_cash_app_to_accounting(conn)

        return {
            "status": "ok",
            "message": "Cash App sincronizado a Accounting"
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, repr(e))




@router.post("/sync/itp")
def sync_itp(conn=Depends(get_db)):
    try:
        from services.accounting_auto import sync_itp_to_accounting
        sync_itp_to_accounting(conn)

        return {
            "status": "ok",
            "message": "Invoice to Pay sincronizado a Accounting"
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, repr(e))


@router.post("/sync/payroll")
def sync_payroll(conn=Depends(get_db)):
    try:
        from services.accounting_auto import sync_payroll_to_accounting
        sync_payroll_to_accounting(conn)

        return {
            "status": "ok",
            "message": "Payroll sincronizado a Accounting"
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, repr(e))


@router.post("/sync/all")
def sync_all_accounting(conn=Depends(get_db)):
    try:
        from services.accounting_auto import (
            sync_cash_app_to_accounting,
            sync_collections_to_accounting,
            sync_itp_to_accounting,
            sync_payroll_to_accounting
        )

        before = _accounting_entry_stats(conn)

        sync_collections_to_accounting(conn)
        sync_cash_app_to_accounting(conn)
        sync_itp_to_accounting(conn)
        sync_payroll_to_accounting(conn)

        after = _accounting_entry_stats(conn)

        return {
            "status": "ok",
            "message": "Accounting sincronizado correctamente",
            "created": max(0, after["total_entries"] - before["total_entries"]),
            "before": before,
            "after": after,
            "latest_period": after["latest_period"],
            "period_counts": after["period_counts"]
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, repr(e))



@router.get("/ledger")
def get_accounting_ledger(
    period: str | None = None,
    origin: str | None = None,
    account_code: str | None = None,   # ✅ NUEVO FILTRO
    conn=Depends(get_db)
):
    """
    Devuelve asientos contables agrupados por entry_id,
    con sus líneas (debe / haber)

    Filtros soportados:
    - period (YYYY-MM)
    - origin (COLLECTIONS, ITP, CASH_APP, MANUAL, etc.)
    - account_code (1101, 2101, 5101, etc.)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    conditions = []
    params = []

    # -----------------------------
    # VALIDACIONES
    # -----------------------------
    if origin and not period:
        raise HTTPException(
            status_code=400,
            detail="period es obligatorio cuando se filtra por origin"
        )

    # -----------------------------
    # FILTROS
    # -----------------------------
    if period:
        conditions.append("e.period = %s")
        params.append(period)

    if origin:
        conditions.append("e.origin = %s")
        params.append(origin)

    if account_code:
        conditions.append("l.account_code = %s")
        params.append(account_code)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # -----------------------------
    # QUERY PRINCIPAL
    # -----------------------------
    query = f"""
        SELECT
            e.id AS entry_id,
            e.entry_date,
            e.period,
            e.description AS entry_description,
            e.origin,
            e.origin_id,

            l.id AS line_id,
            l.account_code,
            l.account_name,
            l.debit,
            l.credit,
            l.line_description

        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        {where_clause}
        ORDER BY
            e.entry_date DESC,
            e.id DESC,
            l.id ASC
    """

    cur.execute(query, params)
    rows = cur.fetchall()

    # -----------------------------
    # AGRUPAR POR entry_id
    # -----------------------------
    entries = {}

    for row in rows:
        entry_id = row["entry_id"]

        if entry_id not in entries:
            entries[entry_id] = {
                "entry_id": entry_id,
                "entry_date": row["entry_date"],
                "period": row["period"],
                "description": row["entry_description"],
                "origin": row["origin"],
                "origin_id": row["origin_id"],
                "lines": []
            }

        entries[entry_id]["lines"].append({
            "line_id": row["line_id"],
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "debit": float(row["debit"] or 0),
            "credit": float(row["credit"] or 0),
            "line_description": row["line_description"]
        })

    return {
        "data": list(entries.values())
    }




# ============================================================
# IVA (FUENTE ÚNICA: accounting_lines.created_at)
# ============================================================
@router.get("/reports/excel")
def download_accounting_report_excel(
    report: str | None = "ASIENTOS",
    period: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    origin: str | None = None,
    account_code: str | None = None,
    conn=Depends(get_db)
):
    rows = _fetch_accounting_report_lines(conn, period, period_from, period_to, origin, account_code)
    wb = Workbook()
    ws = wb.active
    ws.title = "Accounting"

    title = _report_title(report)
    scope = period or (f"{period_from or 'inicio'} a {period_to or 'fin'}" if period_from or period_to else "Todos")
    ws.merge_cells("A1:J1")
    ws["A1"] = f"{title} - {scope}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")

    headers = ["Fecha", "Asiento", "Periodo", "Origen", "Origen ID", "Cuenta", "Nombre cuenta", "Detalle", "Debe", "Haber"]
    ws.append([])
    ws.append(headers)
    header_fill = PatternFill("solid", fgColor="003A75")
    for cell in ws[3]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    total_debit = 0.0
    total_credit = 0.0
    for row in rows:
        debit = float(row.get("debit") or 0)
        credit = float(row.get("credit") or 0)
        total_debit += debit
        total_credit += credit
        ws.append([
            row.get("entry_date"),
            row.get("entry_id"),
            row.get("period"),
            row.get("origin"),
            row.get("origin_id"),
            row.get("account_code"),
            row.get("account_name"),
            row.get("line_description") or row.get("entry_description"),
            debit,
            credit
        ])

    ws.append(["", "", "", "", "", "", "", "Totales", total_debit, total_credit])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)

    widths = [14, 10, 12, 16, 14, 14, 28, 48, 14, 14]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + idx)].width = width

    for row in ws.iter_rows(min_row=4, min_col=9, max_col=10):
        for cell in row:
            cell.number_format = '#,##0.00'

    tmp_dir = tempfile.mkdtemp(prefix="erp_som_accounting_")
    filename = _report_filename("xlsx", report, period, period_from, period_to)
    path = os.path.join(tmp_dir, filename)
    wb.save(path)

    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/reports/pdf")
def download_accounting_report_pdf(
    report: str | None = "ASIENTOS",
    period: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    origin: str | None = None,
    account_code: str | None = None,
    conn=Depends(get_db)
):
    rows = _fetch_accounting_report_lines(conn, period, period_from, period_to, origin, account_code)
    tmp_dir = tempfile.mkdtemp(prefix="erp_som_accounting_")
    filename = _report_filename("pdf", report, period, period_from, period_to)
    path = os.path.join(tmp_dir, filename)

    title = _report_title(report)
    scope = period or (f"{period_from or 'inicio'} a {period_to or 'fin'}" if period_from or period_to else "Todos")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)

    data = [["Fecha", "Asiento", "Periodo", "Origen", "Cuenta", "Detalle", "Debe", "Haber"]]
    total_debit = 0.0
    total_credit = 0.0
    for row in rows:
        debit = float(row.get("debit") or 0)
        credit = float(row.get("credit") or 0)
        total_debit += debit
        total_credit += credit
        data.append([
            str(row.get("entry_date") or ""),
            str(row.get("entry_id") or ""),
            str(row.get("period") or ""),
            str(row.get("origin") or ""),
            str(row.get("account_code") or ""),
            str(row.get("line_description") or row.get("entry_description") or "")[:80],
            f"{debit:,.2f}",
            f"{credit:,.2f}"
        ])
    data.append(["", "", "", "", "", "Totales", f"{total_debit:,.2f}", f"{total_credit:,.2f}"])

    table = Table(data, repeatRows=1, colWidths=[58, 48, 58, 72, 58, 270, 72, 72])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003A75")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE8")),
        ("ALIGN", (6, 1), (7, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EEF3F8"))
    ]))

    doc.build([
        Paragraph(f"{title} - {scope}", styles["Title"]),
        Spacer(1, 12),
        table
    ])

    return FileResponse(path, filename=filename, media_type="application/pdf")


@router.get("/iva")
def get_accounting_iva(
    period: str,  # 'YYYY-MM'
    conn=Depends(get_db)
):
    """
    IVA ERP-SOM - DEFINITIVO

    - Fuente ÚNICA: accounting_lines
    - Periodo = to_char(created_at,'YYYY-MM')
    - Siempre calcula el mes actual
    - Arrastra saldo a favor SOLO si existe en el mes anterior
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # -------------------------------------------------
        # Helper: IVA por periodo (100% SQL SAFE)
        # -------------------------------------------------
        def iva_por_periodo(p):
            cur.execute("""
                SELECT
                    SUM(
                        CASE
                            WHEN account_code = '2108' -- IVA por pagar
                            THEN COALESCE(credit,0) - COALESCE(debit,0)
                            ELSE 0
                        END
                    ) AS iva_por_pagar,

                    SUM(
                        CASE
                            WHEN account_code = '1131' -- IVA crédito fiscal
                            THEN COALESCE(debit,0) - COALESCE(credit,0)
                            ELSE 0
                        END
                    ) AS iva_credito
                FROM accounting_lines
                WHERE to_char(created_at, 'YYYY-MM') = %s
            """, (p,))

            row = cur.fetchone() or {}
            return (
                float(row.get("iva_por_pagar") or 0),
                float(row.get("iva_credito") or 0)
            )

        # -------------------------------------------------
        # 1️⃣ IVA DEL MES ACTUAL (SIEMPRE)
        # -------------------------------------------------
        iva_por_pagar, iva_credito = iva_por_periodo(period)

        # -------------------------------------------------
        # 2️⃣ PERIODO ANTERIOR
        # -------------------------------------------------
        year, month = map(int, period.split("-"))
        if month == 1:
            prev_period = f"{year-1}-12"
        else:
            prev_period = f"{year}-{month-1:02d}"

        prev_pagar, prev_credito = iva_por_periodo(prev_period)

        # -------------------------------------------------
        # 3️⃣ SALDO A FAVOR (SOLO SI EXISTE)
        # -------------------------------------------------
        if prev_credito > prev_pagar:
            saldo_favor_anterior = prev_credito - prev_pagar
        else:
            saldo_favor_anterior = 0.0

        # -------------------------------------------------
        # 4️⃣ IVA FINAL
        # -------------------------------------------------
        iva_total = iva_por_pagar - iva_credito - saldo_favor_anterior

        return {
            "period": period,
            "iva_por_pagar": round(iva_por_pagar, 2),
            "iva_credito": round(iva_credito, 2),
            "saldo_favor_anterior": round(saldo_favor_anterior, 2),
            "iva_total": round(iva_total, 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e))
