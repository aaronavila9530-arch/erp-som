from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Any, Dict, Optional
from database import get_db
from services.tenanting import company_code

import json
import psycopg2
from psycopg2.extras import Json
from psycopg2 import sql


router = APIRouter(prefix="/draft-survey", tags=["Draft Survey (Unified)"])


def _ensure_draft_company_schema(cur) -> None:
    for table_name in (
        "draft_survey_word_report",
        "draft_survey_ballast",
        "draft_survey",
        "general_draft_survey",
    ):
        cur.execute(
            sql.SQL("""
                ALTER TABLE {table}
                ADD COLUMN IF NOT EXISTS company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR'
            """).format(table=sql.Identifier(table_name))
        )


# =========================================================
# INTERNAL HELPERS
# =========================================================
def _row_to_dict(cur, row) -> Dict[str, Any]:
    if row is None:
        return {}
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _normalize_ballast_json(payload: Dict[str, Any]) -> None:
    ballast_json = payload.get("ballast_json")
    if not ballast_json:
        return

    if isinstance(ballast_json, str):
        try:
            ballast_json = json.loads(ballast_json)
        except Exception:
            return

    if not isinstance(ballast_json, dict):
        return

    if isinstance(ballast_json.get("ballast"), dict):
        payload["ballast"] = ballast_json.get("ballast") or {}
    if isinstance(ballast_json.get("fresh_water"), dict):
        payload["fresh_water"] = ballast_json.get("fresh_water") or {}


def _merge_preserving_values(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for key, value in (source or {}).items():
        current = target.get(key)
        if key in target and current not in (None, "") and value in (None, ""):
            continue
        target[key] = value


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


def _ensure_unified_draft_columns(conn) -> None:
    cur = conn.cursor()
    try:
        for column in ("init_date", "final_date"):
            cur.execute(
                sql.SQL("ALTER TABLE draft_survey ADD COLUMN IF NOT EXISTS {column} TEXT").format(
                    column=sql.Identifier(column)
                )
            )
    finally:
        cur.close()


def _get_table_column_types(conn, table_name: str) -> Dict[str, str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table_name,),
    )
    cols = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()
    return cols


def _normalize_db_value(value: Any, data_type: str) -> Any:
    dtype = (data_type or "").lower()

    if value is None:
        return None

    if dtype in {"json", "jsonb"}:
        return Json(value)

    if dtype in {"integer", "bigint", "smallint"}:
        if value == "":
            return None
        return int(value)

    if dtype in {"boolean"}:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "t", "yes", "y", "si", "sí"}:
            return True
        if text in {"0", "false", "f", "no", "n"}:
            return False
        return None

    if dtype in {"date"} and hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def _normalize_section_for_table(conn, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    column_types = _get_table_column_types(conn, table_name)
    return {
        key: _normalize_db_value(value, column_types.get(key, ""))
        for key, value in (data or {}).items()
        if key in column_types
    }


def _insert_dynamic(conn, table_name: str, data: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cols = _get_table_columns(conn, table_name)
    if not cols:
        return {"inserted": False, "id": None, "saved_fields": 0}

    blocked = {"id", "created_at", "updated_at"}
    allowed = cols - blocked

    insert_fields = {
        key: value
        for key, value in (data or {}).items()
        if key in allowed
    }
    for key, value in (extra or {}).items():
        if key in allowed:
            insert_fields[key] = value

    if "status" in allowed and "status" not in insert_fields:
        insert_fields["status"] = "Pending for review"

    if not insert_fields:
        return {"inserted": False, "id": None, "saved_fields": 0}

    insert_fields = _normalize_section_for_table(conn, table_name, insert_fields)

    fields_sql = [sql.Identifier(field) for field in insert_fields.keys()]
    values = list(insert_fields.values())
    placeholders_sql = [sql.Placeholder()] * len(values)

    if "created_at" in cols:
        fields_sql.append(sql.Identifier("created_at"))
        placeholders_sql.append(sql.SQL("NOW()"))
    if "updated_at" in cols:
        fields_sql.append(sql.Identifier("updated_at"))
        placeholders_sql.append(sql.SQL("NOW()"))

    q = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values}) RETURNING id").format(
        table=sql.Identifier(table_name),
        fields=sql.SQL(", ").join(fields_sql),
        values=sql.SQL(", ").join(placeholders_sql),
    )

    cur = conn.cursor()
    cur.execute(q, values)
    row = cur.fetchone()
    cur.close()
    return {"inserted": True, "id": row[0] if row else None, "saved_fields": len(insert_fields)}


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
    general_common_fields = {
        "vessel_mv",
        "survey_no",
        "call_letters",
        "vessel_previous_names",
        "flag",
        "registry",
        "built_year",
        "by",
        "master",
        "chief_officer",
        "chief_engineer",
        "witness_draughts",
        "witness_sounding",
        "initial_surveyors",
        "final_surveyors",
        "survey_requested_by",
        "on_account_of",
        "attended_also_by",
        "init_ships_location",
        "final_ships_location",
        "length_overall",
        "length_between_pp",
        "extreme_breadth",
        "moulded_breadth",
        "depth_overall_incl_keel_plate",
        "moulded_depth",
        "summer_draught",
        "summer_freeboard",
        "constant_declared",
        "constant_calculated",
        "light_displacement",
        "light_shipweight_plan",
        "summer_displacement",
        "summer_deadweight",
        "net_register_tons",
        "gross_register_tons",
        "hydro_tables_issued",
    }
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
        # GENERAL_DRAFT_SURVEY
        # -------------------------------------------------
        if isinstance(k, str) and k in general_common_fields:
            general[k] = v
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
    data = _normalize_section_for_table(conn, table_name, data)
    for k, v in data.items():
        if k not in cols_allowed:
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


def _add_metadata(section: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(section or {})
    for key in ("year", "month", "continent", "country", "port", "client", "draft_report_number", "status"):
        if key in source and key not in out:
            out[key] = source.get(key)
    return out


def _prepare_sections(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    sections = _normalize_payload(payload)
    source = payload or {}

    for key in ("general", "draft", "ballast", "word"):
        sections[key] = _add_metadata(sections.get(key) or {}, source)

    if isinstance(source.get("ballast"), dict) or isinstance(source.get("fresh_water"), dict):
        sections["ballast"]["ballast_json"] = {
            "ballast": source.get("ballast") or {},
            "fresh_water": source.get("fresh_water") or {},
        }

    return sections


# =========================================================
# POST — UNIFICADO (4 TABLAS)
# =========================================================
@router.post("/unified")
def create_draft_survey_unified(payload: Dict[str, Any], conn=Depends(get_db)):
    payload = payload or {}
    draft_report_number = str(payload.get("draft_report_number") or "").strip()
    if not draft_report_number:
        raise HTTPException(status_code=400, detail="draft_report_number is required")

    _ensure_unified_draft_columns(conn)
    sections = _prepare_sections(payload)

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM general_draft_survey
            WHERE draft_report_number = %s
            LIMIT 1
            """,
            (draft_report_number,),
        )
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=409, detail="draft_report_number already exists")
        cur.close()

        general_result = _insert_dynamic(
            conn,
            "general_draft_survey",
            sections.get("general") or {},
            {"draft_report_number": draft_report_number},
        )
        general_id = general_result.get("id")
        if not general_id:
            raise HTTPException(status_code=500, detail="No se pudo crear general_draft_survey")

        draft_result = _insert_dynamic(
            conn,
            "draft_survey",
            sections.get("draft") or {},
            {
                "general_id": general_id,
                "draft_report_number": draft_report_number,
            },
        )
        draft_id = draft_result.get("id")

        ballast_result = {"inserted": False, "id": None, "saved_fields": 0}
        if sections.get("ballast"):
            ballast_result = _insert_dynamic(
                conn,
                "draft_survey_ballast",
                sections.get("ballast") or {},
                {
                    "draft_survey_id": draft_id,
                    "draft_report_number": draft_report_number,
                },
            )

        word_result = {"inserted": False, "id": None, "saved_fields": 0}
        if sections.get("word"):
            word_result = _insert_dynamic(
                conn,
                "draft_survey_word_report",
                sections.get("word") or {},
                {
                    "draft_survey_id": draft_id,
                    "draft_report_number": draft_report_number,
                },
            )

        conn.commit()
        return {
            "success": True,
            "draft_report_number": draft_report_number,
            "general_id": general_id,
            "draft_id": draft_id,
            "results": {
                "general_draft_survey": general_result,
                "draft_survey": draft_result,
                "draft_survey_ballast": ballast_result,
                "draft_survey_word_report": word_result,
            },
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
            _merge_preserving_values(unified, general)

        if draft:
            _merge_preserving_values(unified, draft)

        if ballast:
            _merge_preserving_values(unified, ballast)
            _normalize_ballast_json(unified)

        if word:
            _merge_preserving_values(unified, word)

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
        _ensure_unified_draft_columns(conn)
        sections = _prepare_sections(payload or {})

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
def get_draft_survey_headers(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        _ensure_draft_company_schema(cur)
        selected_company = company_code(x_company_code)
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
              WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM draft_survey_ballast
              WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM draft_survey
              WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s

              UNION ALL

              SELECT status, year, month, continent, country, port, client, draft_report_number
              FROM general_draft_survey
              WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s
            ) t
            GROUP BY draft_report_number
            ORDER BY draft_report_number DESC
        """, {"company_code": selected_company})

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


@router.get("/unified/{draft_report_number}/ballast")
def get_draft_survey_unified_ballast(draft_report_number: str, conn=Depends(get_db)):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM draft_survey_ballast
            WHERE draft_report_number = %s
            LIMIT 1
            """,
            (draft_report_number,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No ballast encontrado")
        return {"success": True, "draft_report_number": draft_report_number, "data": _row_to_dict(cur, row)}
    finally:
        try:
            cur.close()
        except Exception:
            pass


@router.get("/unified/{draft_report_number}/word")
def get_draft_survey_unified_word(draft_report_number: str, conn=Depends(get_db)):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM draft_survey_word_report
            WHERE draft_report_number = %s
            LIMIT 1
            """,
            (draft_report_number,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No word report encontrado")
        return {"success": True, "draft_report_number": draft_report_number, "data": _row_to_dict(cur, row)}
    finally:
        try:
            cur.close()
        except Exception:
            pass


@router.delete("/unified/{draft_report_number}")
def delete_draft_survey_unified(draft_report_number: str, conn=Depends(get_db)):
    draft_report_number = str(draft_report_number or "").strip()
    if not draft_report_number:
        raise HTTPException(status_code=400, detail="draft_report_number is required")

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM draft_survey WHERE draft_report_number = %s", (draft_report_number,))
        draft_ids = [row[0] for row in cur.fetchall() or []]

        counts = {}
        for table_name in ("draft_survey_word_report", "draft_survey_ballast"):
            cur.execute(
                sql.SQL("DELETE FROM {table} WHERE draft_report_number = %s").format(
                    table=sql.Identifier(table_name)
                ),
                (draft_report_number,),
            )
            counts[table_name] = cur.rowcount

            if draft_ids:
                cur.execute(
                    sql.SQL("DELETE FROM {table} WHERE draft_survey_id = ANY(%s)").format(
                        table=sql.Identifier(table_name)
                    ),
                    (draft_ids,),
                )
                counts[table_name] += cur.rowcount

        cur.execute("DELETE FROM draft_survey WHERE draft_report_number = %s", (draft_report_number,))
        counts["draft_survey"] = cur.rowcount

        cur.execute("DELETE FROM general_draft_survey WHERE draft_report_number = %s", (draft_report_number,))
        counts["general_draft_survey"] = cur.rowcount

        if not any(counts.values()):
            raise HTTPException(status_code=404, detail=f"No existe Draft Survey {draft_report_number}")

        conn.commit()
        return {"success": True, "draft_report_number": draft_report_number, "deleted": counts}
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
    finally:
        try:
            cur.close()
        except Exception:
            pass


