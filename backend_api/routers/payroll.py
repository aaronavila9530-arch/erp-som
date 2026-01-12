from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import date

from database import get_db
from security.auth import get_current_user
from security.rbac import require_permission

router = APIRouter(
    prefix="/hr/payroll",
    tags=["HHRR - PAYROLL"]
)

# ============================================================
# CONSTANTES COSTA RICA 2026
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
# PAYROLL ENDPOINT (BLINDADO)
# ============================================================

@router.get(
    "",
    dependencies=[Depends(require_permission("hhrr", "payroll"))]
)
def calcular_payroll(
    year: int,
    month: int,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    # 🔒 BLINDAJE DURO POR ROL
    if user["rol"] not in ("admin", "master"):
        raise HTTPException(
            status_code=403,
            detail="Acceso restringido a ADMIN / MASTER"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # 1. EMPLEADOS ACTIVOS
    # --------------------------------------------------------
    cur.execute("""
        SELECT
            e.id,
            e.nombre,
            e.apellidos,
            e.salario,
            e.horas_contratadas
        FROM empleados e
        WHERE e.activo = true
    """)
    empleados = cur.fetchall()

    payroll = []

    for emp in empleados:

        # ----------------------------------------------------
        # 2. MAPEAR EMPLEADO → USUARIO
        # ----------------------------------------------------
        cur.execute("""
            SELECT usuario
            FROM usuarios
            WHERE lower(nombre) = lower(%s)
              AND lower(apellido) = lower(%s)
            LIMIT 1
        """, (emp["nombre"], emp["apellidos"]))

        u = cur.fetchone()
        if not u:
            continue

        usuario = u["usuario"]

        # ----------------------------------------------------
        # 3. HORAS APROBADAS DEL MES
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # 4. DEDUCCIONES TRABAJADOR
        # ----------------------------------------------------
        deducciones = sum(
            salario_base * tasa
            for tasa in DEDUCCIONES_TRABAJADOR.values()
        )

        # ----------------------------------------------------
        # 5. IMPUESTO RENTA
        # ----------------------------------------------------
        renta = calcular_renta(salario_base)

        salario_neto = round(
            salario_base - deducciones - renta, 2
        )

        # ----------------------------------------------------
        # 6. CARGAS PATRONALES
        # ----------------------------------------------------
        cargas = sum(
            salario_base * tasa
            for tasa in CARGAS_PATRONALES.values()
        )

        payroll.append({
            "usuario": usuario,
            "nombre": emp["nombre"],
            "apellidos": emp["apellidos"],
            "horas_contratadas": emp["horas_contratadas"],
            "horas_trabajadas": round(horas_trabajadas, 2),
            "horas_ot": round(horas_ot, 2),
            "salario_base": round(salario_base, 2),
            "deducciones_trabajador": round(deducciones, 2),
            "impuesto_renta": renta,
            "salario_neto": salario_neto,
            "cargas_patronales": round(cargas, 2),
            "costo_total_empresa": round(salario_base + cargas, 2)
        })

    return {
        "year": year,
        "month": month,
        "total_empleados": len(payroll),
        "data": payroll
    }
