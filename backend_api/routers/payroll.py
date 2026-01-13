from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

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
def listar_empleados_payroll(
    conn=Depends(get_db)
):
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

# ============================================================
# 2️⃣ PREVIEW / CÁLCULO PAYROLL (NO GUARDA)
# ============================================================

@router.get(
    "/calculate",
    dependencies=[Depends(require_permission("hhrr", "payroll"))]
)
def calcular_payroll(
    usuario: str,
    year: int,
    month: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            nombre,
            apellidos,
            salario,
            horas_contratadas
        FROM empleados
        WHERE usuario = %s
          AND estado = 'Activo'
        LIMIT 1
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    cur.execute("""
        SELECT COALESCE(SUM(duracion_horas), 0) AS total
        FROM hr_ot_log
        WHERE usuario = %s
          AND estado = 'APROBADO'
          AND EXTRACT(YEAR FROM fecha_inicio) = %s
          AND EXTRACT(MONTH FROM fecha_inicio) = %s
    """, (usuario, year, month))

    horas_trabajadas = float(cur.fetchone()["total"] or 0)

    horas_normales = min(horas_trabajadas, emp["horas_contratadas"])
    horas_ot = max(horas_trabajadas - emp["horas_contratadas"], 0)

    salario_base = float(emp["salario"])

    deducciones = sum(
        salario_base * tasa
        for tasa in DEDUCCIONES_TRABAJADOR.values()
    )

    renta = calcular_renta(salario_base)

    salario_neto = round(
        salario_base - deducciones - renta, 2
    )

    cargas = sum(
        salario_base * tasa
        for tasa in CARGAS_PATRONALES.values()
    )

    return {
        "usuario": usuario,
        "nombre": emp["nombre"],
        "apellidos": emp["apellidos"],
        "year": year,
        "month": month,
        "horas_contratadas": emp["horas_contratadas"],
        "horas_trabajadas": round(horas_trabajadas, 2),
        "horas_ot": round(horas_ot, 2),
        "salario_base": round(salario_base, 2),
        "deducciones_trabajador": round(deducciones, 2),
        "impuesto_renta": renta,
        "salario_neto": salario_neto,
        "cargas_patronales": round(cargas, 2),
        "costo_total_empresa": round(salario_base + cargas, 2)
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

    cur.execute("""
        INSERT INTO payroll_runs (
            usuario,
            year,
            month,
            salario_neto,
            generado_por
        )
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (usuario, year, month)
        DO NOTHING
    """, (
        payload["usuario"],
        payload["year"],
        payload["month"],
        payload["salario_neto"],
        user["usuario"]
    ))

    conn.commit()

    return {"status": "OK", "message": "Planilla confirmada"}
