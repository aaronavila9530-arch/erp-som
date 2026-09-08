# ============================================================
# ROUTER: Continentes / Países / Puertos desde una sola tabla
# Tabla: continentes_paises_puertos
# ============================================================

from fastapi import APIRouter, Query
from database import sql

router = APIRouter(prefix="/cpp", tags=["Continentes / Países / Puertos"])


def _norm_sql(column: str) -> str:
    return f"LOWER(translate(TRIM({column}), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))"


def _norm_text(value: str) -> str:
    return str(value or "").strip()

# ============================================================
# GET → Lista de continentes (únicos)
# ============================================================
@router.get("/continentes")
def get_continentes_cpp():
    rows = sql("""
        SELECT DISTINCT continente
        FROM continentes_paises_puertos
        WHERE continente IS NOT NULL AND continente <> ''
        ORDER BY continente;
    """, fetch=True)

    return [row[0] for row in rows]


# ============================================================
# GET → Lista de países según continente
# ============================================================
@router.get("/paises")
def get_paises_cpp(continente: str):
    rows = sql(f"""
        SELECT DISTINCT pais
        FROM continentes_paises_puertos
        WHERE {_norm_sql("continente")} = {_norm_sql("%s")}
          AND pais IS NOT NULL AND pais <> ''
        ORDER BY pais;
    """, (_norm_text(continente),), fetch=True)

    return [row[0] for row in rows]


# ============================================================
# GET → Lista de puertos según país
# ============================================================
@router.get("/puertos")
def get_puertos_cpp(
    pais: str,
    continente: str | None = Query(None),
):
    params = []
    filters = [
        "pais = %s",
        "puerto IS NOT NULL",
        "puerto <> ''",
    ]
    params.append(pais)
    if continente and continente.strip():
        filters.append(f"{_norm_sql('continente')} = {_norm_sql('%s')}")
        params.append(_norm_text(continente))

    rows = sql(f"""
        SELECT DISTINCT puerto
        FROM continentes_paises_puertos
        WHERE {_norm_sql("pais")} = {_norm_sql("%s")}
          AND {" AND ".join(filters[1:])}
        ORDER BY puerto;
    """, tuple(params), fetch=True)

    return [row[0] for row in rows]


# ============================================================
# GET → Lista de puertos todos
# ============================================================

@router.get("/puertos_all")
def get_todos_los_puertos():
    rows = sql("""
        SELECT DISTINCT puerto
        FROM continentes_paises_puertos
        WHERE puerto IS NOT NULL AND puerto <> ''
        ORDER BY puerto;
    """, fetch=True)

    return [r[0] for r in rows]

