# ============================================================
# ROUTER: Continentes / Países / Puertos desde una sola tabla
# Tabla: continentes_paises_puertos
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

from database import get_db, sql

router = APIRouter(prefix="/cpp", tags=["Continentes / Países / Puertos"])


class PortPayload(BaseModel):
    continente: str
    pais: str
    puerto: str


class PortUpdatePayload(BaseModel):
    continente: str | None = None
    pais: str | None = None
    puerto: str | None = None


def _ensure_cpp_schema(cur):
    cur.execute("""
        ALTER TABLE continentes_paises_puertos
        ADD COLUMN IF NOT EXISTS id BIGSERIAL;
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cpp_location_lookup
        ON continentes_paises_puertos(continente, pais, puerto);
    """)


def _norm_sql(column: str) -> str:
    return f"LOWER(translate(TRIM({column}), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))"


def _norm_text(value: str) -> str:
    return str(value or "").strip()


def _clean_payload(data: dict) -> dict:
    cleaned = {k: _norm_text(v) for k, v in (data or {}).items()}
    missing = [label for key, label in (("continente", "continente"), ("pais", "país"), ("puerto", "puerto")) if not cleaned.get(key)]
    if missing:
        raise HTTPException(status_code=400, detail="Falta " + ", ".join(missing))
    return cleaned


def _port_exists(cur, data: dict, exclude_id: int | None = None) -> bool:
    params = {
        "continente": data["continente"],
        "pais": data["pais"],
        "puerto": data["puerto"],
        "exclude_id": exclude_id or 0,
    }
    cur.execute(f"""
        SELECT id
        FROM continentes_paises_puertos
        WHERE {_norm_sql("continente")} = {_norm_sql("%(continente)s")}
          AND {_norm_sql("pais")} = {_norm_sql("%(pais)s")}
          AND {_norm_sql("puerto")} = {_norm_sql("%(puerto)s")}
          AND (%(exclude_id)s = 0 OR id <> %(exclude_id)s)
        LIMIT 1;
    """, params)
    return cur.fetchone() is not None

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


@router.get("/ports")
def list_ports(
    continente: str | None = Query(None),
    pais: str | None = Query(None),
    puerto: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    conn=Depends(get_db),
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_cpp_schema(cur)
    conn.commit()

    filters = [
        "continente IS NOT NULL",
        "TRIM(continente) <> ''",
        "pais IS NOT NULL",
        "TRIM(pais) <> ''",
        "puerto IS NOT NULL",
        "TRIM(puerto) <> ''",
    ]
    params: dict[str, object] = {
        "limit": int(page_size),
        "offset": (int(page) - 1) * int(page_size),
    }
    if _norm_text(continente):
        filters.append(f"{_norm_sql('continente')} = {_norm_sql('%(continente)s')}")
        params["continente"] = _norm_text(continente)
    if _norm_text(pais):
        filters.append(f"{_norm_sql('pais')} = {_norm_sql('%(pais)s')}")
        params["pais"] = _norm_text(pais)
    if _norm_text(puerto):
        filters.append(f"{_norm_sql('puerto')} = {_norm_sql('%(puerto)s')}")
        params["puerto"] = _norm_text(puerto)
    if _norm_text(q):
        filters.append("(continente ILIKE %(q)s OR pais ILIKE %(q)s OR puerto ILIKE %(q)s)")
        params["q"] = f"%{_norm_text(q)}%"

    where_sql = " AND ".join(filters)
    cur.execute(f"SELECT COUNT(*) AS total FROM continentes_paises_puertos WHERE {where_sql}", params)
    total = int((cur.fetchone() or {}).get("total") or 0)
    cur.execute(f"""
        SELECT id, TRIM(continente) AS continente, TRIM(pais) AS pais, TRIM(puerto) AS puerto
        FROM continentes_paises_puertos
        WHERE {where_sql}
        ORDER BY continente, pais, puerto
        LIMIT %(limit)s OFFSET %(offset)s;
    """, params)
    rows = cur.fetchall() or []
    cur.close()
    return {"total": total, "data": rows, "page": page, "page_size": page_size}


@router.get("/ports/{port_id}")
def get_port(port_id: int, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_cpp_schema(cur)
    conn.commit()
    cur.execute("""
        SELECT id, TRIM(continente) AS continente, TRIM(pais) AS pais, TRIM(puerto) AS puerto
        FROM continentes_paises_puertos
        WHERE id = %s;
    """, (port_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    return row


@router.post("/ports")
def create_port(payload: PortPayload, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_cpp_schema(cur)
    data = _clean_payload(payload.dict())
    if _port_exists(cur, data):
        cur.close()
        raise HTTPException(status_code=409, detail="Ese continente, país y puerto ya existe")
    cur.execute("""
        INSERT INTO continentes_paises_puertos (continente, pais, puerto)
        VALUES (%(continente)s, %(pais)s, %(puerto)s)
        RETURNING id, TRIM(continente) AS continente, TRIM(pais) AS pais, TRIM(puerto) AS puerto;
    """, data)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return {"status": "OK", "data": row}


@router.put("/ports/{port_id}")
def update_port(port_id: int, payload: PortUpdatePayload, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_cpp_schema(cur)
    cur.execute("""
        SELECT id, continente, pais, puerto
        FROM continentes_paises_puertos
        WHERE id = %s;
    """, (port_id,))
    current = cur.fetchone()
    if not current:
        cur.close()
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    data = {
        "continente": _norm_text(payload.continente) or current["continente"],
        "pais": _norm_text(payload.pais) or current["pais"],
        "puerto": _norm_text(payload.puerto) or current["puerto"],
    }
    data = _clean_payload(data)
    if _port_exists(cur, data, exclude_id=port_id):
        cur.close()
        raise HTTPException(status_code=409, detail="Ese continente, país y puerto ya existe")
    data["id"] = port_id
    cur.execute("""
        UPDATE continentes_paises_puertos
        SET continente = %(continente)s,
            pais = %(pais)s,
            puerto = %(puerto)s
        WHERE id = %(id)s
        RETURNING id, TRIM(continente) AS continente, TRIM(pais) AS pais, TRIM(puerto) AS puerto;
    """, data)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return {"status": "OK", "data": row}


@router.delete("/ports/{port_id}")
def delete_port(port_id: int, conn=Depends(get_db)):
    cur = conn.cursor()
    _ensure_cpp_schema(cur)
    cur.execute("DELETE FROM continentes_paises_puertos WHERE id = %s", (port_id,))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close()
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    conn.commit()
    cur.close()
    return {"status": "OK"}

