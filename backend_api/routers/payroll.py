from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from datetime import date
import os
from fastapi.responses import FileResponse

from database import get_db
from security.auth import get_current_user
from security.rbac import require_permission

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)




router = APIRouter(
    prefix="/hr/payroll",
    tags=["HHRR - PAYROLL"]
)

# ============================================================
# CONSTANTES COSTA RICA 2026 (NO TOCAR)
# ============================================================

TRAMOS_RENTA = [
    (918000, 0.00),
    (1347000, 0.10),
    (2364000, 0.15),
    (4727000, 0.20),
    (float("inf"), 0.25)
]

DEDUCCIONES_TRABAJADOR = {
    "SEM": 0.055,
    "IVM": 0.0433,
    "BANCO_POPULAR": 0.01
}

CARGAS_PATRONALES = {
    "SEM": 0.0925,
    "IVM": 0.0558,
    "BP_CC": 0.0025,
    "BP_LPT": 0.0025,
    "FODESAF": 0.05,
    "IMAS": 0.005,
    "INA": 0.015,
    "FCL": 0.015,
    "OPC": 0.02,
    "INS": 0.01
}

# ============================================================
# HELPERS
# ============================================================

def calcular_renta(monto: float) -> float:
    impuesto = 0
    restante = monto
    base_anterior = 0

    for limite, tasa in TRAMOS_RENTA:
        tramo = min(restante, limite - base_anterior)
        if tramo <= 0:
            break
        impuesto += tramo * tasa
        restante -= tramo
        base_anterior = limite

    return round(impuesto, 2)

# ============================================================
# 1️⃣ LISTADO BASE PAYROLL (TABLA FIJA)
# ============================================================

@router.get(
    "/employees",
    dependencies=[Depends(require_permission("hhrr", "employees"))]
)
def listar_empleados_payroll(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            nombre,
            apellidos,
            jornada,
            salario,
            pago,
            estado,
            usuario,
            cedula_id
        FROM empleados
        WHERE estado = 'Activo'
          AND usuario IS NOT NULL
        ORDER BY nombre, apellidos
    """)

    return {
        "total": cur.rowcount,
        "data": cur.fetchall()
    }

# ============================================================
# 2️⃣ PREVIEW / CÁLCULO PAYROLL (NO GUARDA)
# ============================================================

@router.get(
    "/calculate",
    dependencies=[Depends(require_permission("hhrr", "payroll"))]
)
def calcular_payroll(
    usuario: str = Query(...),
    year: int = Query(..., ge=2000),
    month: int = Query(..., ge=1, le=12),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # VALIDAR PERÍODO (SOLO MES EN CURSO)
    # --------------------------------------------------------
    hoy = date.today()
    if year != hoy.year or month != hoy.month:
        raise HTTPException(
            400,
            "Solo se permite generar la planilla del mes en curso"
        )

    # --------------------------------------------------------
    # BLOQUEAR SI YA ESTÁ CERRADA
    # --------------------------------------------------------
    cur.execute("""
        SELECT 1
        FROM payroll_runs
        WHERE usuario = %s
          AND year = %s
          AND month = %s
        LIMIT 1
    """, (usuario, year, month))

    if cur.fetchone():
        raise HTTPException(
            400,
            "La planilla de este período ya fue cerrada"
        )

    # --------------------------------------------------------
    # DATOS DEL EMPLEADO
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            nombre,
            apellidos,
            jornada,
            salario,
            pago,
            horas_contratadas,
            cedula_id
        FROM empleados
        WHERE usuario = %s
          AND estado = 'Activo'
        LIMIT 1
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    # --------------------------------------------------------
    # HORAS APROBADAS (OT LOG)
    # --------------------------------------------------------
    cur.execute("""
        SELECT COALESCE(SUM(duracion_horas), 0) AS total
        FROM hr_ot_log
        WHERE usuario = %s
          AND estado = 'APROBADO'
          AND EXTRACT(YEAR FROM fecha_inicio) = %s
          AND EXTRACT(MONTH FROM fecha_inicio) = %s
    """, (usuario, year, month))

    horas_registradas = float(cur.fetchone()["total"] or 0)

    salario_base = float(emp["salario"])
    jornada = emp["jornada"].upper()

    horas_ot = 0.0
    pago_horas_extra = 0.0
    salario_bruto = salario_base

    # --------------------------------------------------------
    # LÓGICA POR JORNADA
    # --------------------------------------------------------
    if jornada == "COMPLETA" and horas_registradas > 0:

        salario_diario = salario_base / 30
        salario_hora = salario_diario / 8
        base_fraccionada = salario_hora / 12
        valor_hora_extra = (base_fraccionada * 8) * 1.5

        horas_ot = horas_registradas
        pago_horas_extra = round(valor_hora_extra * horas_ot, 2)
        salario_bruto += pago_horas_extra

    elif jornada == "HORAS":

        horas_contratadas = emp["horas_contratadas"] or 0

        if horas_registradas > horas_contratadas:
            horas_ot = round(horas_registradas - horas_contratadas, 2)
        else:
            horas_ot = 0.0

    # --------------------------------------------------------
    # DEDUCCIONES Y RENTA (SOBRE SALARIO BRUTO)
    # --------------------------------------------------------
    deducciones_trabajador = round(
        sum(salario_bruto * tasa for tasa in DEDUCCIONES_TRABAJADOR.values()),
        2
    )

    impuesto_renta = calcular_renta(salario_bruto)

    salario_neto = round(
        salario_bruto - deducciones_trabajador - impuesto_renta,
        2
    )

    cargas_patronales = round(
        sum(salario_bruto * tasa for tasa in CARGAS_PATRONALES.values()),
        2
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------
    return {
        "usuario": usuario,
        "cedula_id": emp["cedula_id"],
        "nombre": emp["nombre"],
        "apellidos": emp["apellidos"],
        "jornada": jornada,
        "pago": emp["pago"],
        "year": year,
        "month": month,
        "salario_base": round(salario_base, 2),
        "horas_registradas": round(horas_registradas, 2),
        "horas_ot": round(horas_ot, 2),
        "pago_horas_extra": pago_horas_extra,
        "salario_bruto": round(salario_bruto, 2),
        "deducciones_trabajador": deducciones_trabajador,
        "impuesto_renta": impuesto_renta,
        "salario_neto": salario_neto,
        "cargas_patronales": cargas_patronales,
        "costo_total_empresa": round(salario_bruto + cargas_patronales, 2)
    }

# ============================================================
# 3️⃣ POSTEAR PLANILLA (CONFIRMACIÓN) — BLINDADO
# ============================================================

@router.put(
    "/post",
    dependencies=[Depends(require_permission("hhrr", "generate"))]
)
def postear_planilla(
    payload: dict,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor()

    usuario = payload["usuario"]
    year = payload["year"]
    month = payload["month"]

    # --------------------------------------------------------
    # PDF PATH LÓGICO (NO ARCHIVO REAL EN BACKEND)
    # --------------------------------------------------------
    pdf_filename = f"COLILLA_{usuario}_{year}_{month}.pdf"
    pdf_path_online = f"/LOCAL_USER_FILE/{pdf_filename}"

    # --------------------------------------------------------
    # INSERT / UPDATE COMPLETO (PAYROLL_RUNS)
    # --------------------------------------------------------
    cur.execute("""
        INSERT INTO payroll_runs (
            usuario,
            year,
            month,
            salario_neto,
            salario_bruto,
            horas_extra,
            monto_horas_extra,
            pdf_path,
            generado_por
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (usuario, year, month)
        DO UPDATE SET
            salario_neto       = EXCLUDED.salario_neto,
            salario_bruto      = EXCLUDED.salario_bruto,
            horas_extra        = EXCLUDED.horas_extra,
            monto_horas_extra  = EXCLUDED.monto_horas_extra,
            pdf_path           = EXCLUDED.pdf_path,
            generado_por       = EXCLUDED.generado_por
    """, (
        usuario,
        year,
        month,
        payload["salario_neto"],
        payload["salario_bruto"],
        payload["horas_ot"],             # horas_extra
        payload["pago_horas_extra"],     # monto_horas_extra
        pdf_path_online,                 # referencia lógica
        user["usuario"]
    ))

    conn.commit()

    return {
        "status": "OK",
        "message": "Planilla registrada correctamente"
    }




# ============================================================
# LISTAR COLILLAS DE PAGO
# ============================================================
@router.get("/payslips")
def listar_payslips(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: int | None = None,
    month: int | None = None,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):

    offset = (page - 1) * page_size
    conditions = []
    params = {}

    rol = (current_user.get("rol") or "").lower()
    usuario = current_user.get("usuario")

    if rol not in ("admin", "master"):
        conditions.append("usuario = %(usuario)s")
        params["usuario"] = usuario

    if year is not None:
        conditions.append("year = %(year)s")
        params["year"] = year

    if month is not None:
        conditions.append("month = %(month)s")
        params["month"] = month

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        f"""
        SELECT
            id,
            usuario,
            year,
            month,
            salario_neto,
            salario_bruto,
            horas_extra,
            monto_horas_extra,
            pdf_path,
            generado_por,
            creado_en
        FROM payroll_runs
        {where_sql}
        ORDER BY year DESC, month DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**params, "limit": page_size, "offset": offset}
    )

    rows = cur.fetchall()

    cur.execute(
        f"SELECT COUNT(*) FROM payroll_runs {where_sql}",
        params
    )

    total = cur.fetchone()["count"]

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": rows
    }



# ============================================================
# 4️⃣ DESCARGAR COLILLA (RECONSTRUCCIÓN ON-DEMAND)
# (NO DEPENDE DE Modulos/  |  GENERA PDF EN MEMORIA)
# ============================================================

from io import BytesIO
from fastapi.responses import StreamingResponse

# ReportLab (backend-only)
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm


def _fmt(valor: float) -> str:
    try:
        return f"{float(valor):,.2f}"
    except Exception:
        return str(valor)


def _generar_colilla_pdf_bytes(data: dict, year: int, month: int) -> bytes:
    """
    Genera el PDF en memoria (bytes) con el mismo formato que tu payroll_pdf.
    No usa filesystem. No depende de Modulos/.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(LETTER),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---------------------------------------------------------
    # HEADER (si existe en backend)
    # Busca backend_api/assets/header.png desde Modulos/HHRR/reports/
    # ---------------------------------------------------------
    assets_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",   # reports -> HHRR
            "..",   # HHRR -> Modulos
            "..",   # Modulos -> raíz del proyecto
            "..",   # raíz -> backend_api
            "assets",
            "header.png"
        )
    )

    if os.path.exists(assets_path):

        # 👉 RESPETA TOP MARGIN DEL DOCUMENTO
        elements.append(Spacer(1, 12))

        header = Image(
            assets_path,
            width=8 * cm,
            height=2.2 * cm,
            hAlign="LEFT"
        )
        elements.append(header)
        elements.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # TÍTULO
    # ---------------------------------------------------------
    title_style = ParagraphStyle(
        "TitleStyle",
        fontSize=13,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    elements.append(
        Paragraph(
            f"<b>Comprobante de Pago</b><br/>"
            f"Periodo: {month}/{year}<br/>"
            f"Empresa: MSL Marine Surveyors and Logistics Group SRL",
            title_style
        )
    )

    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # DATOS DEL EMPLEADO
    # ---------------------------------------------------------
    info_table = Table(
        [
            ["Empleado:", f"{data['nombre']} {data['apellidos']}"],
            ["Cédula:", data.get("cedula_id", "N/D")],
            ["Usuario:", data["usuario"]],
            ["Jornada:", data["jornada"]],
            ["Tipo de pago:", data["pago"]],
            ["Fecha emisión:", date.today().strftime("%d/%m/%Y")]
        ],
        colWidths=[6 * cm, 16 * cm]
    )

    info_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    elements.append(info_table)
    elements.append(Spacer(1, 12))

    # =========================================================
    # RESUMEN DE DEVENGOS
    # =========================================================
    devengos_rows = [
        ["Resumen de Devengos", "Detalle", "Monto"],
        ["Salario Base", "", _fmt(data["salario_base"])],
        ["Horas Extra", f"{data.get('horas_ot', 0)} horas", _fmt(data.get("pago_horas_extra", 0.0))],
        ["Total Devengado", "", _fmt(data["salario_bruto"])]
    ]

    devengos_table = Table(devengos_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    devengos_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ])
    )

    elements.append(devengos_table)
    elements.append(Spacer(1, 12))

    salario_bruto = float(data["salario_bruto"])

    # ---------------------------------------------------------
    # DEDUCCIONES TRABAJADOR
    # ---------------------------------------------------------
    ded_rows = [["Deducción Trabajador", "%", "Monto"]]

    for k, tasa in DEDUCCIONES_TRABAJADOR.items():
        ded_rows.append([
            k,
            f"{tasa * 100:.2f} %",
            _fmt(salario_bruto * tasa)
        ])

    ded_rows.append([
        "Total Deducciones",
        "",
        _fmt(data["deducciones_trabajador"])
    ])

    ded_table = Table(ded_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    ded_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
    ]))

    elements.append(ded_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # RENTA
    # ---------------------------------------------------------
    renta_tramo = 0.0
    for limite, tasa in TRAMOS_RENTA:
        if salario_bruto <= limite:
            renta_tramo = tasa
            break

    renta_table = Table(
        [
            ["Impuesto Renta", "% Aplicado", "Monto"],
            ["Renta", f"{renta_tramo * 100:.2f} %", _fmt(data["impuesto_renta"])]
        ],
        colWidths=[8 * cm, 4 * cm, 6 * cm]
    )

    renta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    elements.append(renta_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # CARGAS PATRONALES (INFORMATIVO)
    # ---------------------------------------------------------
    patronal_rows = [["Carga Patronal", "%", "Monto"]]

    total_patronal = 0.0
    for k, tasa in CARGAS_PATRONALES.items():
        monto = salario_bruto * tasa
        total_patronal += monto
        patronal_rows.append([
            k,
            f"{tasa * 100:.2f} %",
            _fmt(monto)
        ])

    patronal_rows.append([
        "Total Cargas Patronales",
        "",
        _fmt(total_patronal)
    ])

    patronal_table = Table(patronal_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    patronal_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
    ]))

    elements.append(patronal_table)
    elements.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # NETO A PAGAR
    # ---------------------------------------------------------
    neto_style = ParagraphStyle(
        "NetoStyle",
        fontSize=12,
        leading=14,
        alignment=TA_RIGHT
    )

    elements.append(
        Paragraph(
            f"<b>Neto a pagar: {_fmt(data['salario_neto'])}</b>",
            neto_style
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


@router.get(
    "/payslips/{year}/{month}/pdf",
    dependencies=[Depends(require_permission("hhrr", "payslips"))]
)
def descargar_colilla_pdf(
    year: int,
    month: int,
    usuario: str | None = None,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    Reconstruye la colilla PDF en tiempo real a partir de:
    - payroll_runs (datos cerrados)
    - empleados (datos maestros)
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)

    rol = (current_user.get("rol") or "").lower()
    usuario_solicitado = usuario or current_user.get("usuario")

    # --------------------------------------------------------
    # RBAC: EMPLEADO SOLO SU PROPIA COLILLA
    # --------------------------------------------------------
    if rol not in ("admin", "master"):
        if usuario_solicitado != current_user.get("usuario"):
            raise HTTPException(403, "No autorizado")

    # --------------------------------------------------------
    # PAYROLL RUN (FUENTE DE VERDAD)
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            usuario,
            year,
            month,
            salario_neto,
            salario_bruto,
            horas_extra,
            monto_horas_extra
        FROM payroll_runs
        WHERE usuario = %s
          AND year = %s
          AND month = %s
        LIMIT 1
    """, (usuario_solicitado, year, month))

    run = cur.fetchone()
    if not run:
        raise HTTPException(404, "Colilla no encontrada")

    # --------------------------------------------------------
    # DATOS DEL EMPLEADO
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            nombre,
            apellidos,
            cedula_id,
            jornada,
            salario,
            pago
        FROM empleados
        WHERE usuario = %s
        LIMIT 1
    """, (usuario_solicitado,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    # --------------------------------------------------------
    # RECONSTRUCCIÓN DETERMINÍSTICA
    # --------------------------------------------------------
    salario_bruto = float(run["salario_bruto"] or 0)
    monto_horas_extra = float(run["monto_horas_extra"] or 0)
    salario_base = salario_bruto - monto_horas_extra

    deducciones_trabajador = round(
        sum(salario_bruto * tasa for tasa in DEDUCCIONES_TRABAJADOR.values()),
        2
    )

    impuesto_renta = calcular_renta(salario_bruto)

    cargas_patronales = round(
        sum(salario_bruto * tasa for tasa in CARGAS_PATRONALES.values()),
        2
    )

    data = {
        "usuario": run["usuario"],
        "nombre": emp["nombre"],
        "apellidos": emp["apellidos"],
        "cedula_id": emp["cedula_id"],
        "jornada": emp["jornada"],
        "pago": emp["pago"],

        "year": run["year"],
        "month": run["month"],

        "salario_base": round(salario_base, 2),
        "horas_ot": float(run["horas_extra"] or 0),
        "pago_horas_extra": round(monto_horas_extra, 2),
        "salario_bruto": round(salario_bruto, 2),

        "deducciones_trabajador": deducciones_trabajador,
        "impuesto_renta": impuesto_renta,
        "salario_neto": float(run["salario_neto"] or 0),
        "cargas_patronales": cargas_patronales,
        "costo_total_empresa": round(salario_bruto + cargas_patronales, 2)
    }

    # --------------------------------------------------------
    # GENERAR PDF (BYTES) Y RESPONDER
    # --------------------------------------------------------
    pdf_bytes = _generar_colilla_pdf_bytes(data=data, year=year, month=month)

    filename = f"COLILLA_{run['usuario']}_{year}_{month}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
