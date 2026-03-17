from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import psycopg2

# =========================================================
# CONFIG
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

router = APIRouter(
    prefix="/servicios-surveyors",
    tags=["Servicios Surveyors Flat"]
)


# =========================================================
# SCHEMAS
# =========================================================
class SurveyorItem(BaseModel):
    surveyor_nombre: str = Field(..., min_length=1)
    honorario: float = Field(ge=0)


class SurveyorsPayload(BaseModel):
    surveyors: List[SurveyorItem]


# =========================================================
# DB
# =========================================================
def get_conn():
    return psycopg2.connect(DB_URL)


# =========================================================
# GET POR SERVICIO
# =========================================================
@router.get("/{consec}")
def get_surveyors(consec: int):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM servicio_surveyors_flat
        WHERE servicio_consec = %s
    """, (consec,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return {"data": []}

    # reconstruir lista
    surveyors = []

    for i in range(1, 11):
        nombre = row[6 + (i - 1)*2]
        honorario = row[7 + (i - 1)*2]

        if nombre:
            surveyors.append({
                "surveyor_nombre": nombre,
                "honorario": float(honorario or 0),
                "orden": i
            })

    return {"data": surveyors}


# =========================================================
# POST (CREAR)
# =========================================================
@router.post("/{consec}")
def create_surveyors(consec: int, payload: SurveyorsPayload):
    return _save(consec, payload)


# =========================================================
# PUT (REEMPLAZAR)
# =========================================================
@router.put("/{consec}")
def update_surveyors(consec: int, payload: SurveyorsPayload):
    return _save(consec, payload)


# =========================================================
# CORE SAVE
# =========================================================
def _save(consec: int, payload: SurveyorsPayload):

    surveyors = payload.surveyors

    if len(surveyors) > 10:
        raise HTTPException(
            status_code=400,
            detail="Máximo 10 surveyors permitidos"
        )

    conn = get_conn()
    cur = conn.cursor()

    # =====================================================
    # TRAER SERVICIO
    # =====================================================
    cur.execute("""
        SELECT num_informe, cliente, pais, puerto, operacion
        FROM servicios
        WHERE consec = %s
    """, (consec,))

    servicio = cur.fetchone()

    if not servicio:
        raise HTTPException(
            status_code=404,
            detail="Servicio no encontrado"
        )

    num_informe, cliente, pais, puerto, operacion = servicio

    # =====================================================
    # ARMAR SLOTS
    # =====================================================
    slots = []
    total = 0

    for i in range(10):
        if i < len(surveyors):
            s = surveyors[i]

            nombre = s.surveyor_nombre
            honorario = float(s.honorario or 0)

            slots.append((nombre, honorario))
            total += honorario
        else:
            slots.append((None, None))

    cantidad = len(surveyors)

    # =====================================================
    # UPSERT
    # =====================================================
    cur.execute("""
    INSERT INTO servicio_surveyors_flat (
        servicio_consec,
        num_informe,
        cliente,
        pais,
        puerto,
        operacion,

        surveyor_1, honorario_1,
        surveyor_2, honorario_2,
        surveyor_3, honorario_3,
        surveyor_4, honorario_4,
        surveyor_5, honorario_5,
        surveyor_6, honorario_6,
        surveyor_7, honorario_7,
        surveyor_8, honorario_8,
        surveyor_9, honorario_9,
        surveyor_10, honorario_10,

        total_honorarios,
        cantidad_surveyors
    )
    VALUES (
        %s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s
    )
    ON CONFLICT (servicio_consec)
    DO UPDATE SET

        num_informe = EXCLUDED.num_informe,
        cliente = EXCLUDED.cliente,
        pais = EXCLUDED.pais,
        puerto = EXCLUDED.puerto,
        operacion = EXCLUDED.operacion,

        surveyor_1 = EXCLUDED.surveyor_1,
        honorario_1 = EXCLUDED.honorario_1,

        surveyor_2 = EXCLUDED.surveyor_2,
        honorario_2 = EXCLUDED.honorario_2,

        surveyor_3 = EXCLUDED.surveyor_3,
        honorario_3 = EXCLUDED.honorario_3,

        surveyor_4 = EXCLUDED.surveyor_4,
        honorario_4 = EXCLUDED.honorario_4,

        surveyor_5 = EXCLUDED.surveyor_5,
        honorario_5 = EXCLUDED.honorario_5,

        surveyor_6 = EXCLUDED.surveyor_6,
        honorario_6 = EXCLUDED.honorario_6,

        surveyor_7 = EXCLUDED.surveyor_7,
        honorario_7 = EXCLUDED.honorario_7,

        surveyor_8 = EXCLUDED.surveyor_8,
        honorario_8 = EXCLUDED.honorario_8,

        surveyor_9 = EXCLUDED.surveyor_9,
        honorario_9 = EXCLUDED.honorario_9,

        surveyor_10 = EXCLUDED.surveyor_10,
        honorario_10 = EXCLUDED.honorario_10,

        total_honorarios = EXCLUDED.total_honorarios,
        cantidad_surveyors = EXCLUDED.cantidad_surveyors;
    """, (
        consec,
        num_informe,
        cliente,
        pais,
        puerto,
        operacion,
        *[item for pair in slots for item in pair],
        total,
        cantidad
    ))

    # =====================================================
    # UPDATE SERVICIOS
    # =====================================================
    if cantidad == 0:
        resumen = ""
    elif cantidad == 1:
        resumen = surveyors[0].surveyor_nombre
    else:
        resumen = f"Varios ({cantidad})"

    cur.execute("""
        UPDATE servicios
        SET surveyor = %s,
            honorarios = %s
        WHERE consec = %s
    """, (resumen, total, consec))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "status": "ok",
        "total": total,
        "cantidad": cantidad
    }


# =========================================================
# CATÁLOGO SURVEYORS
# =========================================================
@router.get("/catalogo/lista")
def get_catalogo():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, apellidos
        FROM surveyor
        ORDER BY nombre
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = [
        {
            "id": r[0],
            "nombre": f"{r[1]} {r[2] or ''}".strip()
        }
        for r in rows
    ]

    return {"data": data}