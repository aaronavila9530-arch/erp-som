from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from datetime import date
import os
from fastapi.responses import FileResponse

from database import get_db
from security.auth import get_current_user
from security.rbac import require_permission



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
            usuario
        FROM empleados
        WHERE estado = 'Activo'
          AND usuario IS NOT NULL
        ORDER BY nombre, apellidos
    """)

    return {
        "total": cur.rowcount,
        "data": cur.fetchall()
    }

from fastapi import Query, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import date

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
            horas_contratadas
        FROM empleados
        WHERE usuario = %s
          AND estado = 'Activo'
        LIMIT 1
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    # ⬇️ A PARTIR DE AQUÍ TU LÓGICA SIGUE EXACTAMENTE IGUAL

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
# 3️⃣ POSTEAR PLANILLA (CONFIRMACIÓN)
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

    # --------------------------------------------------------
    # CONSTRUIR PDF PATH EN LÍNEA (NO RUTA LOCAL)
    # --------------------------------------------------------
    usuario = payload["usuario"]
    year = payload["year"]
    month = payload["month"]

    pdf_filename = f"COLILLA_{usuario}_{year}_{month}.pdf"

    # Ruta lógica / URL servida por FastAPI
    pdf_path_online = f"/hr/payroll/files/{year}/{month}/{pdf_filename}"

    # --------------------------------------------------------
    # INSERT / UPDATE
    # --------------------------------------------------------
    cur.execute("""
        INSERT INTO payroll_runs (
            usuario,
            year,
            month,
            salario_neto,
            pdf_path,
            generado_por
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (usuario, year, month)
        DO UPDATE SET
            salario_neto = EXCLUDED.salario_neto,
            pdf_path = EXCLUDED.pdf_path,
            generado_por = EXCLUDED.generado_por
    """, (
        usuario,
        year,
        month,
        payload["salario_neto"],
        pdf_path_online,
        user["usuario"]
    ))

    conn.commit()

    return {
        "status": "OK",
        "message": "Planilla registrada correctamente",
        "pdf_path": pdf_path_online
    }


# ============================================================
# DESCARGAR / VER COLILLA PDF
# GET /hr/payroll/files/{year}/{month}/{filename}
# ============================================================

@router.get(
    "/files/{year}/{month}/{filename}",
    dependencies=[Depends(require_permission("hhrr", "payroll"))]
)
def get_payroll_pdf(
    year: int,
    month: int,
    filename: str
):
    """
    Retorna el PDF de la colilla de pago.
    """

    # Ruta física en el backend
    file_path = os.path.join(
        "storage",
        "payroll",
        str(year),
        f"{int(month):02d}",
        filename
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Archivo de colilla no encontrado"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


# ============================================================
# LISTAR COLILLAS DE PAGO (PAGINADO + FILTROS)
# GET /hr/payroll/payslips
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
    """
    Reglas de acceso:
    - employee → SOLO sus colillas
    - admin / master → TODAS

    Filtros opcionales:
    - year  (desde creado_en)
    - month (desde creado_en)
    """

    offset = (page - 1) * page_size
    conditions = []
    params = {}

    # =========================================================
    # SEGURIDAD POR ROL
    # =========================================================
    rol = (current_user.get("rol") or "").lower()
    usuario = current_user.get("usuario")

    if rol not in ("admin", "master"):
        conditions.append("usuario = %(usuario)s")
        params["usuario"] = usuario

    # =========================================================
    # FILTRO AÑO
    # =========================================================
    if year is not None:
        conditions.append("EXTRACT(YEAR FROM creado_en) = %(year)s")
        params["year"] = year

    # =========================================================
    # FILTRO MES
    # =========================================================
    if month is not None:
        conditions.append("EXTRACT(MONTH FROM creado_en) = %(month)s")
        params["month"] = month

    # =========================================================
    # WHERE DINÁMICO
    # =========================================================
    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =========================================================
    # QUERY PRINCIPAL
    # =========================================================
    cur.execute(
        f"""
        SELECT
            id,
            usuario,
            year,
            month,
            salario_neto,
            pdf_path,
            generado_por,
            creado_en
        FROM payroll_runs
        {where_sql}
        ORDER BY creado_en DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {
            **params,
            "limit": page_size,
            "offset": offset
        }
    )

    rows = cur.fetchall()

    # =========================================================
    # TOTAL
    # =========================================================
    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM payroll_runs
        {where_sql}
        """,
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
# DESCARGAR COLILLA PDF
# GET /hr/payroll/files/{year}/{month}/{filename}
# ============================================================
@router.get(
    "/files/{year}/{month}/{filename}",
    dependencies=[Depends(require_permission("hhrr", "payroll"))]
)
def get_payroll_pdf(
    year: int,
    month: int,
    filename: str
):
    """
    Descarga segura de colilla de pago (PDF).
    """

    file_path = os.path.join(
        "storage",
        "payroll",
        str(year),
        f"{int(month):02d}",
        filename
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Archivo de colilla no encontrado"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )