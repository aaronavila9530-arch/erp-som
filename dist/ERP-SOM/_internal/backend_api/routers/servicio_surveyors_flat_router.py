from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

import database


router = APIRouter(
    prefix="/servicios-surveyors",
    tags=["Servicios Surveyors Flat"],
)
_flat_table_checked = False


def _ensure_flat_table():
    global _flat_table_checked
    if _flat_table_checked:
        return

    database.sql("""
        CREATE TABLE IF NOT EXISTS servicio_surveyors_flat (
            servicio_consec INTEGER PRIMARY KEY,
            num_informe TEXT,
            cliente TEXT,
            pais TEXT,
            puerto TEXT,
            operacion TEXT,
            surveyor_1 TEXT,
            honorario_1 NUMERIC(14, 2),
            surveyor_2 TEXT,
            honorario_2 NUMERIC(14, 2),
            surveyor_3 TEXT,
            honorario_3 NUMERIC(14, 2),
            surveyor_4 TEXT,
            honorario_4 NUMERIC(14, 2),
            surveyor_5 TEXT,
            honorario_5 NUMERIC(14, 2),
            surveyor_6 TEXT,
            honorario_6 NUMERIC(14, 2),
            surveyor_7 TEXT,
            honorario_7 NUMERIC(14, 2),
            surveyor_8 TEXT,
            honorario_8 NUMERIC(14, 2),
            surveyor_9 TEXT,
            honorario_9 NUMERIC(14, 2),
            surveyor_10 TEXT,
            honorario_10 NUMERIC(14, 2),
            total_honorarios NUMERIC(14, 2) DEFAULT 0,
            cantidad_surveyors INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    for i in range(1, 11):
        database.sql(f"ALTER TABLE servicio_surveyors_flat ADD COLUMN IF NOT EXISTS surveyor_{i} TEXT")
        database.sql(f"ALTER TABLE servicio_surveyors_flat ADD COLUMN IF NOT EXISTS honorario_{i} NUMERIC(14, 2)")

    for column, definition in (
        ("num_informe", "TEXT"),
        ("cliente", "TEXT"),
        ("pais", "TEXT"),
        ("puerto", "TEXT"),
        ("operacion", "TEXT"),
        ("total_honorarios", "NUMERIC(14, 2) DEFAULT 0"),
        ("cantidad_surveyors", "INTEGER DEFAULT 0"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
        ("updated_at", "TIMESTAMP DEFAULT NOW()"),
    ):
        database.sql(f"ALTER TABLE servicio_surveyors_flat ADD COLUMN IF NOT EXISTS {column} {definition}")

    database.sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_servicio_surveyors_flat_consec
        ON servicio_surveyors_flat (servicio_consec)
    """)
    _flat_table_checked = True


class SurveyorItem(BaseModel):
    surveyor_nombre: str = Field(..., min_length=1)
    honorario: float = Field(ge=0)


class SurveyorsPayload(BaseModel):
    surveyors: List[SurveyorItem]


@router.get("/catalogo/lista")
def get_catalogo():
    try:
        rows = database.sql(
            """
            SELECT codigo, nombre, apellidos
            FROM surveyor
            WHERE COALESCE(TRIM(nombre), '') <> ''
            ORDER BY nombre, apellidos, codigo
            """,
            fetch=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo catalogo surveyors: {str(e)}",
        )

    data = []
    seen = set()
    for codigo, nombre, apellidos in rows:
        display = f"{nombre or ''} {apellidos or ''}".strip()
        if not display:
            continue

        key = display.lower()
        if key in seen:
            continue

        seen.add(key)
        data.append(
            {
                "id": codigo,
                "codigo": codigo,
                "nombre": display,
                "apellidos": "",
            }
        )

    return {"data": data}


@router.get("/{consec}")
def get_surveyors(consec: int):
    try:
        _ensure_flat_table()
        rows = database.sql(
            """
            SELECT
                surveyor_1, honorario_1,
                surveyor_2, honorario_2,
                surveyor_3, honorario_3,
                surveyor_4, honorario_4,
                surveyor_5, honorario_5,
                surveyor_6, honorario_6,
                surveyor_7, honorario_7,
                surveyor_8, honorario_8,
                surveyor_9, honorario_9,
                surveyor_10, honorario_10
            FROM servicio_surveyors_flat
            WHERE servicio_consec = %s
            """,
            (consec,),
            fetch=True,
        )

        if not rows:
            return {"data": []}

        row = rows[0]
        surveyors = []
        for i in range(0, 20, 2):
            nombre = row[i]
            honorario = row[i + 1]
            if not nombre or str(nombre).strip() == "":
                continue

            try:
                honorario_val = float(honorario or 0)
            except Exception:
                honorario_val = 0

            surveyors.append(
                {
                    "surveyor_nombre": str(nombre).strip(),
                    "honorario": honorario_val,
                    "orden": (i // 2) + 1,
                }
            )

        return {"data": surveyors}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo surveyors: {str(e)}",
        )


@router.post("/{consec}")
def create_surveyors(consec: int, payload: SurveyorsPayload):
    return _save(consec, payload)


@router.put("/{consec}")
def update_surveyors(consec: int, payload: SurveyorsPayload):
    return _save(consec, payload)


def _save(consec: int, payload: SurveyorsPayload):
    _ensure_flat_table()
    surveyors = payload.surveyors

    if len(surveyors) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximo 10 surveyors permitidos",
        )

    servicio_rows = database.sql(
        """
        SELECT num_informe, cliente, pais, puerto, operacion
        FROM servicios
        WHERE consec = %s
        """,
        (consec,),
        fetch=True,
    )

    if not servicio_rows:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    num_informe, cliente, pais, puerto, operacion = servicio_rows[0]

    slots = []
    total = 0
    for i in range(10):
        if i < len(surveyors):
            item = surveyors[i]
            nombre = item.surveyor_nombre
            honorario = float(item.honorario or 0)
            slots.append((nombre, honorario))
            total += honorario
        else:
            slots.append((None, None))

    cantidad = len(surveyors)

    database.sql(
        """
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
            cantidad_surveyors = EXCLUDED.cantidad_surveyors,
            updated_at = NOW()
        """,
        (
            consec,
            num_informe,
            cliente,
            pais,
            puerto,
            operacion,
            *[value for pair in slots for value in pair],
            total,
            cantidad,
        ),
    )

    if cantidad == 0:
        resumen = ""
    elif cantidad == 1:
        resumen = surveyors[0].surveyor_nombre
    else:
        resumen = f"Varios ({cantidad})"

    database.sql(
        """
        UPDATE servicios
        SET surveyor = %s,
            honorarios = %s
        WHERE consec = %s
        """,
        (resumen, total, consec),
    )

    return {
        "status": "ok",
        "total": total,
        "cantidad": cantidad,
    }
