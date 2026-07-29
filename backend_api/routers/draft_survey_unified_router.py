from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, Optional
from database import get_db

import psycopg2
from psycopg2 import sql


router = APIRouter(prefix="/draft-survey", tags=["Draft Survey (Unified)"])


# =========================================================
# INTERNAL HELPERS
# =========================================================
def _row_to_dict(cur, row) -> Dict[str, Any]:
    if row is None:
        return {}
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _get_table_columns(conn, table_name: str) -> set:
    """
    Lee columnas desde information_schema para blindar updates
    (evita que un key raro rompa o intente tocar columnas inexistentes).
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table_name,)
    )
    cols = {r[0] for r in cur.fetchall()}
    cur.close()
    return cols


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Acepta 2 formatos:

      A) Payload realmente seccionado:
         {
           "general": {...},
           "draft": {...},
           "ballast": {...},
           "word": {...}
         }

      B) Payload flat (como viene del form):
         {
           "vessel_mv": "...",
           "initial_surveyors": "...",
           "init_date": "...",
           "word_mt": "...",
           "ballast": {...},
           "fresh_water": {...}
         }

    REGLA CRÍTICA:
    - NO asumir que viene seccionado solo porque exista la key "ballast".
    - El form flat también manda "ballast" y "fresh_water" como bloques extra.
    - Solo se trata como seccionado si viene al menos una de estas keys:
        "general", "draft", "word"
      con valor dict real.
    """

    if not isinstance(payload, dict):
        return {
            "general": {},
            "draft": {},
            "ballast": {},
            "word": {}
        }

    # =====================================================
    # 1) DETECCIÓN CORRECTA DE PAYLOAD SECCIONADO
    # =====================================================
    # OJO:
    # "ballast" por sí solo NO basta, porque el payload flat también lo trae.
    is_sectioned = any(
        key in payload and isinstance(payload.get(key), dict)
        for key in ("general", "draft", "word")
    )

    if is_sectioned:
        return {
            "general": payload.get("general") or {},
            "draft": payload.get("draft") or {},
            "ballast": payload.get("ballast") or {},
            "word": payload.get("word") or {},
        }

    # =====================================================
    # 2) PAYLOAD FLAT -> AUTO-RUTEO
    # =====================================================
    general: Dict[str, Any] = {}
    draft: Dict[str, Any] = {}
    ballast: Dict[str, Any] = {}
    word: Dict[str, Any] = {}

    # Estos bloques NO deben forzar modo seccionado
    special_blocks = {"ballast", "fresh_water"}

    ballast_keywords = [
        "FPT", "WBT", "APT", "SLOP", "FW P", "FW S", "FW DIST",
        "FW_P", "FW_S", "FW_DIST", "SLOP_TANK"
    ]

    # Campos típicos del draft_survey
    draft_common_prefixes = ("init_", "final_")
    draft_common_fields = {
        "status",
        "cargo",
        "port_from",
        "port_to",
        "loading",
        "unloading",
        "year",
        "month",
        "continent",
        "country",
        "port",
        "client",
        "draft_report_number",
        "general_id",
        "trim_tables_available",
        "trim_tables_yes",
        "trim_tables_no",
        "msl_surveyor"
    }

    for k, v in payload.items():

        # -------------------------------------------------
        # IGNORAR BLOQUES COMPLEJOS QUE NO DEBEN CAER
        # EN general/draft por error
        # -------------------------------------------------
        if k in special_blocks and isinstance(v, dict):
            continue

        # -------------------------------------------------
        # WORD REPORT
        # -------------------------------------------------
        if isinstance(k, str) and k.startswith("word_"):
            word[k] = v
            continue

        # -------------------------------------------------
        # BALLAST (solo si viene por columnas flat)
        # -------------------------------------------------
        if isinstance(k, str) and any(tank in k for tank in ballast_keywords):
            ballast[k] = v
            continue

        # -------------------------------------------------
        # DRAFT SURVEY
        # -------------------------------------------------
        if isinstance(k, str) and (k.startswith(draft_common_prefixes) or k in draft_common_fields):
            draft[k] = v
            continue

        # -------------------------------------------------
        # FALLBACK -> GENERAL_DRAFT_SURVEY
        # -------------------------------------------------
        general[k] = v

    return {
        "general": general,
        "draft": draft,
        "ballast": ballast,
        "word": word
    }


def _update_by_report_number(
    conn,
    table_name: str,
    draft_report_number: str,
    data: Dict[str, Any],
    exclude_columns: Optional[set] = None
) -> Dict[str, Any]:
    """
    Update dinámico (solo columnas existentes, ignora None/"" si querés mantener silencio).
    Devuelve: {"updated": bool, "rowcount": int}
    """
    exclude_columns = exclude_columns or set()

    if not data:
        return {"updated": False, "rowcount": 0}

    cols = _get_table_columns(conn, table_name)

    # Nunca tocar estas
    hard_exclude = {"id", "created_at"}
    cols_allowed = cols - hard_exclude - set(exclude_columns)

    # Filtrar keys válidos
    set_items = []
    values = []
    for k, v in data.items():
        if k not in cols_allowed:
            continue

        # Si querés permitir vacíos explícitos, quita este if:
        if v in [None, ""]:
            continue

        set_items.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
        values.append(v)

    if not set_items:
        return {"updated": False, "rowcount": 0}

    # updated_at si existe
    if "updated_at" in cols_allowed:
        set_items.append(sql.SQL("{} = NOW()").format(sql.Identifier("updated_at")))

    q = sql.SQL("UPDATE {t} SET {sets} WHERE draft_report_number = %s").format(
        t=sql.Identifier(table_name),
        sets=sql.SQL(", ").join(set_items)
    )

    values.append(draft_report_number)

    cur = conn.cursor()
    cur.execute(q, values)
    rowcount = cur.rowcount
    cur.close()

    return {"updated": rowcount > 0, "rowcount": rowcount}


# =========================================================
# GET — UNIFICADO (4 TABLAS)  ✅ CORREGIDO
# =========================================================
@router.get("/unified/{draft_report_number}")
def get_draft_survey_unified(draft_report_number: str, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        # 1) draft_survey
        cur.execute(
            "SELECT * FROM draft_survey WHERE draft_report_number = %s LIMIT 1",
            (draft_report_number,)
        )
        draft_row = cur.fetchone()
        draft = _row_to_dict(cur, draft_row)

        # 2) ballast
        cur.execute(
            "SELECT * FROM draft_survey_ballast WHERE draft_report_number = %s LIMIT 1",
            (draft_report_number,)
        )
        ballast_row = cur.fetchone()
        ballast = _row_to_dict(cur, ballast_row)

        if not ballast and draft and draft.get("id") is not None:
            cur.execute(
                "SELECT * FROM draft_survey_ballast WHERE draft_survey_id = %s LIMIT 1",
                (draft.get("id"),)
            )
            ballast_row = cur.fetchone()
            ballast = _row_to_dict(cur, ballast_row)

        # 3) word
        cur.execute(
            "SELECT * FROM draft_survey_word_report WHERE draft_report_number = %s LIMIT 1",
            (draft_report_number,)
        )
        word_row = cur.fetchone()
        word = _row_to_dict(cur, word_row)

        if not word and draft and draft.get("id") is not None:
            cur.execute(
                "SELECT * FROM draft_survey_word_report WHERE draft_survey_id = %s LIMIT 1",
                (draft.get("id"),)
            )
            word_row = cur.fetchone()
            word = _row_to_dict(cur, word_row)

        # 4) general
        cur.execute(
            "SELECT * FROM general_draft_survey WHERE draft_report_number = %s LIMIT 1",
            (draft_report_number,)
        )
        general_row = cur.fetchone()
        general = _row_to_dict(cur, general_row)

        if not any([draft, ballast, word, general]):
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró Draft Survey para draft_report_number={draft_report_number}"
            )

        # 🔥 MERGE TOTAL (PLANO)
        unified = {}

        if general:
            unified.update(general)

        if draft:
            unified.update(draft)

        if ballast:
            unified.update(ballast)

        if word:
            unified.update(word)

        return {
            "success": True,
            "draft_report_number": draft_report_number,
            "data": unified
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =========================================================
# PUT — UNIFICADO (4 TABLAS)  ✅
# - Si viene seccionado -> usa secciones
# - Si viene flat -> auto-rutea keys
# =========================================================
@router.put("/unified/{draft_report_number}")
def update_draft_survey_unified(
    draft_report_number: str,
    payload: Dict[str, Any],
    conn=Depends(get_db)
):
    try:
        sections = _normalize_payload(payload)

        # 0) Verificar que exista al menos en draft_survey o general (para no “update fantasma”)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                (SELECT 1 FROM draft_survey WHERE draft_report_number = %s LIMIT 1) AS has_draft,
                (SELECT 1 FROM general_draft_survey WHERE draft_report_number = %s LIMIT 1) AS has_general
            """,
            (draft_report_number, draft_report_number)
        )
        exists = cur.fetchone()
        cur.close()

        has_draft = bool(exists and exists[0])
        has_general = bool(exists and exists[1])

        if not (has_draft or has_general):
            raise HTTPException(
                status_code=404,
                detail=f"No existe registro base para draft_report_number={draft_report_number}"
            )

        # 1) Update por tabla
        results = {}

        # general_draft_survey
        results["general_draft_survey"] = _update_by_report_number(
            conn=conn,
            table_name="general_draft_survey",
            draft_report_number=draft_report_number,
            data=sections.get("general") or {},
        )

        # draft_survey
        results["draft_survey"] = _update_by_report_number(
            conn=conn,
            table_name="draft_survey",
            draft_report_number=draft_report_number,
            data=sections.get("draft") or {},
        )

        # draft_survey_ballast
        results["draft_survey_ballast"] = _update_by_report_number(
            conn=conn,
            table_name="draft_survey_ballast",
            draft_report_number=draft_report_number,
            data=sections.get("ballast") or {},
        )

        # draft_survey_word_report
        results["draft_survey_word_report"] = _update_by_report_number(
            conn=conn,
            table_name="draft_survey_word_report",
            draft_report_number=draft_report_number,
            data=sections.get("word") or {},
        )

        # 2) Commit
        try:
            conn.commit()
        except Exception:
            pass

        # 3) Resumen (incluye si alguna tabla no tenía fila)
        #    Nota: si una tabla NO tiene fila para ese draft_report_number, rowcount será 0.
        return {
            "success": True,
            "draft_report_number": draft_report_number,
            "results": results
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))



# =========================================================
# GET HEADERS (LIST) — 1 LINE PER draft_report_number
# GET /draft-survey/headers
# =========================================================
@router.get("/headers")
def get_draft_survey_headers(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
              draft_report_number,
              MAX(status)    AS status,
              MAX(year)      AS year,
              MAX(month)     AS month,
              MAX(continent) AS continent,
              MAX(country)   AS country,
              MAX(port)      AS port,
              MAX(client)    AS client
            FROM (
              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM draft_survey_word_report

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM draft_survey_ballast

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM draft_survey

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM general_draft_survey
            ) t
            GROUP BY draft_report_number
            ORDER BY draft_report_number DESC
        """)

        rows = cur.fetchall() or []

        return {
            "success": True,
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Headers fetch error: {e}"
        )
    finally:
        try:
            cur.close()
        except Exception:
            pass


