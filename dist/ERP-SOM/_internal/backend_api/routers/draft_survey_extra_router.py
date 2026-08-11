from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import Json, RealDictCursor
from database import get_db


router = APIRouter(
    prefix="/draft-survey-extra",
    tags=["Draft Survey Extra"]
)


# =========================================================
# HELPERS
# =========================================================
def clean_value_as_is(value):
    """
    NO normaliza textos.
    NO quita espacios internos.
    NO convierte strings a float.
    SOLO convierte vacíos reales a None.
    """
    if value is None:
        return None

    if isinstance(value, str):
        if value == "":
            return None
        return value

    return value

def _normalize_decimal_string(v):
    """
    Convierte solo strings numéricos reales.
    Soporta coma decimal.
    No toca textos normales.
    """
    if v is None:
        return None

    if isinstance(v, (int, float, bool)):
        return v

    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None

        s2 = s.replace(",", ".")

        try:
            float(s2)
            return s2
        except Exception:
            return v

    return v


def _get_table_column_types(cur, table_name: str):
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
    """, (table_name,))
    return {row[0]: row[1] for row in cur.fetchall()}


def _normalize_value_by_db_type(value, data_type: str):
    dtype = (data_type or "").lower()

    if value is None:
        return None

    if dtype in ("json", "jsonb"):
        return Json(value)

    if dtype in (
        "integer",
        "bigint",
        "smallint",
        "numeric",
        "decimal",
        "real",
        "double precision"
    ):
        return _normalize_decimal_string(value)

    return value


def _normalize_payload_by_db_types(payload: dict, column_types: dict):
    normalized = {}

    for key, value in (payload or {}).items():
        if key in column_types:
            normalized[key] = _normalize_value_by_db_type(value, column_types[key])
        else:
            normalized[key] = value

    return normalized

# ---------------------------------------------------------
# BALLAST HELPERS — BLINDADOS
# ---------------------------------------------------------
def _resolve_draft_survey_real_id(cur, draft_survey_id: str):
    real_id = None

    if str(draft_survey_id).isdigit():

        cur.execute("""
            SELECT id
            FROM draft_survey
            WHERE general_id = %s
            LIMIT 1
        """, (int(draft_survey_id),))
        row = cur.fetchone()

        if not row:
            cur.execute("""
                SELECT id
                FROM draft_survey
                WHERE id = %s
                LIMIT 1
            """, (int(draft_survey_id),))
            row = cur.fetchone()

        if row:
            real_id = row[0]

    if not real_id:
        cur.execute("""
            SELECT id
            FROM draft_survey
            WHERE draft_report_number = %s
            LIMIT 1
        """, (str(draft_survey_id),))
        row = cur.fetchone()

        if row:
            real_id = row[0]

    return real_id


def _get_draft_survey_report_number(cur, real_id):
    if not real_id:
        return None

    cur.execute("""
        SELECT draft_report_number
        FROM draft_survey
        WHERE id = %s
        LIMIT 1
    """, (real_id,))
    row = cur.fetchone()

    if not row:
        return None

    return row[0]


def _get_ballast_columns(cur):
    cur.execute(
        "ALTER TABLE draft_survey_ballast ADD COLUMN IF NOT EXISTS draft_report_number TEXT"
    )
    cur.execute(
        "ALTER TABLE draft_survey_ballast ADD COLUMN IF NOT EXISTS ballast_json JSONB"
    )

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'draft_survey_ballast'
    """)
    return {r[0] for r in cur.fetchall()}


def _clean_ballast_value(v):
    if v is None:
        return None

    if isinstance(v, str):
        vv = v.strip()
        if vv == "":
            return None
        if vv.lower() in ("none", "null"):
            return None
        return vv

    return v


def _normalize_tank_name(name: str) -> str:
    import re

    raw = str(name or "").upper().strip()
    raw = raw.replace("-", " ")
    raw = raw.replace("_", " ")
    raw = re.sub(r"\s+", " ", raw)
    return raw


def _tank_base_key(prefix: str, tank_name: str):
    import re

    n = _normalize_tank_name(tank_name)

    if n == "FPT":
        return f"{prefix}_fpt"

    if n == "APT":
        return f"{prefix}_apt"

    if n in ("SLOP", "SLOP TANK"):
        return f"{prefix}_slop_tank"

    m = re.match(r"^WBT\s*(\d+)\s*([PS])$", n)
    if m:
        tank_no = m.group(1)
        side = m.group(2).lower()
        return f"{prefix}_wbt_{tank_no}{side}"

    return None


def _build_ballast_flat_payload(payload: dict, cols: set):
    payload = payload or {}

    ballast_block = payload.get("ballast")
    fresh_water_block = payload.get("fresh_water")

    # Compatibilidad: si mandan directo {"init":[...], "final":[...]}
    if not isinstance(ballast_block, dict) and any(k in payload for k in ("init", "final")):
        ballast_block = {
            "init": payload.get("init") or [],
            "final": payload.get("final") or []
        }

    if not isinstance(ballast_block, dict):
        ballast_block = {}

    if not isinstance(fresh_water_block, dict):
        fresh_water_block = {}

    flat_payload = {}

    # -----------------------------------------------------
    # LIMPIAR SLOTS DE BALLAST (para evitar basura vieja)
    # -----------------------------------------------------
    for prefix in ("init", "final"):

        for i in range(1, 21):
            for side in ("p", "s"):
                base = f"{prefix}_wbt_{i}{side}"
                for field in ("name", "sounding", "volume", "density"):
                    key = f"{base}_{field}"
                    if key in cols:
                        flat_payload[key] = None

        for tank in ("fpt", "apt", "slop_tank"):
            base = f"{prefix}_{tank}"
            for field in ("name", "sounding", "volume", "density"):
                key = f"{base}_{field}"
                if key in cols:
                    flat_payload[key] = None

    # -----------------------------------------------------
    # LIMPIAR SLOTS DE FRESH WATER
    # -----------------------------------------------------
    for prefix in ("init", "final"):
        for i in range(1, 21):
            for field in ("name", "height", "sounding", "volume", "density", "total"):
                key = f"{prefix}_fw_{i}_{field}"
                if key in cols:
                    flat_payload[key] = None

    # -----------------------------------------------------
    # MAPEAR BALLAST JSON -> COLUMNAS
    # -----------------------------------------------------
    for prefix in ("init", "final"):

        tank_list = ballast_block.get(prefix, [])
        if not isinstance(tank_list, list):
            continue

        for tank in tank_list:
            if not isinstance(tank, dict):
                continue

            tank_name = _clean_ballast_value(tank.get("tank_name"))
            if not tank_name:
                continue

            base = _tank_base_key(prefix, tank_name)
            if not base:
                continue

            mapping = {
                f"{base}_name": tank_name,
                f"{base}_sounding": _normalize_decimal_string(_clean_ballast_value(tank.get("sounding"))),
                f"{base}_volume": _normalize_decimal_string(_clean_ballast_value(tank.get("volume"))),
                f"{base}_density": _normalize_decimal_string(_clean_ballast_value(tank.get("density"))),
            }

            for k, v in mapping.items():
                if k in cols:
                    flat_payload[k] = v

    # -----------------------------------------------------
    # MAPEAR FRESH WATER JSON -> COLUMNAS
    # -----------------------------------------------------
    for prefix in ("init", "final"):

        tank_list = fresh_water_block.get(prefix, [])
        if not isinstance(tank_list, list):
            continue

        for idx, tank in enumerate(tank_list[:20], start=1):
            if not isinstance(tank, dict):
                continue

            base = f"{prefix}_fw_{idx}"

            mapping = {
                f"{base}_name": _clean_ballast_value(tank.get("tank_name")),
                f"{base}_height": _normalize_decimal_string(_clean_ballast_value(tank.get("height"))),
                f"{base}_sounding": _normalize_decimal_string(_clean_ballast_value(tank.get("sounding"))),
                f"{base}_volume": _normalize_decimal_string(_clean_ballast_value(tank.get("volume"))),
                f"{base}_density": _normalize_decimal_string(_clean_ballast_value(tank.get("density"))),
            }

            for k, v in mapping.items():
                if k in cols:
                    flat_payload[k] = v

    # -----------------------------------------------------
    # BACKUP JSON ORIGINAL
    # -----------------------------------------------------
    if "raw_payload" in cols:
        flat_payload["raw_payload"] = payload

    if "ballast_json" in cols:
        flat_payload["ballast_json"] = {
            "ballast": ballast_block,
            "fresh_water": fresh_water_block
        }

    return flat_payload


# ---------------------------------------------------------
# BALLAST — CREATE
# ---------------------------------------------------------
@router.post("/ballast/{draft_survey_id}")
def create_ballast(draft_survey_id: str, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        real_id = _resolve_draft_survey_real_id(cur, draft_survey_id)

        if not real_id:
            raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

        draft_report_number = _get_draft_survey_report_number(cur, real_id)

        cols = _get_ballast_columns(cur)

        if not cols:
            raise HTTPException(500, "No se pudieron leer columnas de draft_survey_ballast")

        fk_col = next(
            (c for c in ("draft_survey_id", "draftsurvey_id") if c in cols),
            None
        )

        if not fk_col:
            raise HTTPException(500, "FK no encontrada en draft_survey_ballast")

        # -----------------------------------------------------
        # VALIDAR QUE NO EXISTA YA
        # -----------------------------------------------------
        cur.execute(f"""
            SELECT id
            FROM draft_survey_ballast
            WHERE {fk_col} = %s
            LIMIT 1
        """, (real_id,))
        existing = cur.fetchone()

        if existing:
            raise HTTPException(409, "Ya existe registro ballast para este draft_survey")

        flat_payload = _build_ballast_flat_payload(payload, cols)

        # FK obligatoria
        flat_payload[fk_col] = real_id

        if "draft_report_number" in cols and draft_report_number:
            flat_payload["draft_report_number"] = draft_report_number

        # -----------------------------------------------------
        # NORMALIZAR SEGÚN TIPOS REALES DE DB
        # -----------------------------------------------------
        ballast_meta = _get_table_column_types(cur, "draft_survey_ballast")
        flat_payload = _normalize_payload_by_db_types(flat_payload, ballast_meta)


        # status opcional
        if "status" in cols:
            flat_payload["status"] = "Pending for review"

        insert_fields = {
            k: v
            for k, v in flat_payload.items()
            if k in cols and k not in ("id", "created_at", "updated_at")
        }

        if not insert_fields:
            raise HTTPException(400, "No hay campos válidos para crear ballast")

        fields = list(insert_fields.keys())
        placeholders = ", ".join(["%s"] * len(fields))
        columns_sql = ", ".join(fields)
        values = [insert_fields[f] for f in fields]

        cur.execute(f"""
            INSERT INTO draft_survey_ballast ({columns_sql})
            VALUES ({placeholders})
            RETURNING id
        """, values)

        ballast_id = cur.fetchone()[0]

        conn.commit()

        print("====== POST BALLAST OK ======")
        print("INPUT:", draft_survey_id)
        print("REAL ID:", real_id)
        print("BALLAST ID:", ballast_id)
        print("FIELDS:", len(insert_fields))
        print("=============================")

        return {
            "success": True,
            "action": "created",
            "ballast_id": ballast_id,
            "draft_survey_id": real_id,
            "saved_fields": len(insert_fields)
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("POST BALLAST ERROR:", str(e))
        raise HTTPException(500, f"Error creando ballast: {str(e)}")

    finally:
        cur.close()


# ---------------------------------------------------------
# BALLAST — UPDATE
# ---------------------------------------------------------
@router.put("/ballast/{draft_survey_id}")
def update_ballast(draft_survey_id: str, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        real_id = _resolve_draft_survey_real_id(cur, draft_survey_id)

        if not real_id:
            raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

        draft_report_number = _get_draft_survey_report_number(cur, real_id)

        cols = _get_ballast_columns(cur)

        if not cols:
            raise HTTPException(500, "No se pudieron leer columnas de draft_survey_ballast")

        fk_col = next(
            (c for c in ("draft_survey_id", "draftsurvey_id") if c in cols),
            None
        )

        if not fk_col:
            raise HTTPException(500, "FK no encontrada en draft_survey_ballast")

        # -----------------------------------------------------
        # BUSCAR EXISTENTE
        # -----------------------------------------------------
        cur.execute(f"""
            SELECT id
            FROM draft_survey_ballast
            WHERE {fk_col} = %s
            LIMIT 1
        """, (real_id,))
        existing = cur.fetchone()

        if not existing:
            flat_payload = _build_ballast_flat_payload(payload, cols)
            flat_payload[fk_col] = real_id

            if "draft_report_number" in cols and draft_report_number:
                flat_payload["draft_report_number"] = draft_report_number

            ballast_meta = _get_table_column_types(cur, "draft_survey_ballast")
            flat_payload = _normalize_payload_by_db_types(flat_payload, ballast_meta)

            if "status" in cols:
                flat_payload["status"] = "Pending for review"

            insert_fields = {
                k: v
                for k, v in flat_payload.items()
                if k in cols and k not in ("id", "created_at", "updated_at")
            }

            if not insert_fields:
                raise HTTPException(400, "No hay campos válidos para crear ballast")

            fields = list(insert_fields.keys())
            placeholders = ", ".join(["%s"] * len(fields))
            columns_sql = ", ".join(fields)
            values = [insert_fields[f] for f in fields]

            cur.execute(f"""
                INSERT INTO draft_survey_ballast ({columns_sql})
                VALUES ({placeholders})
                RETURNING id
            """, values)

            ballast_id = cur.fetchone()[0]
            conn.commit()

            return {
                "success": True,
                "action": "created_by_put",
                "ballast_id": ballast_id,
                "draft_survey_id": real_id,
                "saved_fields": len(insert_fields)
            }

        ballast_id = existing[0]

        flat_payload = _build_ballast_flat_payload(payload, cols)

        if "draft_report_number" in cols and draft_report_number:
            flat_payload["draft_report_number"] = draft_report_number

        # -----------------------------------------------------
        # NORMALIZAR SEGÚN TIPOS REALES DE DB
        # -----------------------------------------------------
        ballast_meta = _get_table_column_types(cur, "draft_survey_ballast")
        flat_payload = _normalize_payload_by_db_types(flat_payload, ballast_meta)

        update_fields = {
            k: v
            for k, v in flat_payload.items()
            if k in cols and k not in ("id", "created_at", fk_col)
        }

        if not update_fields:
            return {
                "success": True,
                "action": "no_changes",
                "ballast_id": ballast_id,
                "draft_survey_id": real_id
            }

        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        values = list(update_fields.values())

        if "updated_at" in cols:
            set_clause += ", updated_at = NOW()"

        values.append(ballast_id)

        cur.execute(f"""
            UPDATE draft_survey_ballast
            SET {set_clause}
            WHERE id = %s
            RETURNING id
        """, values)

        updated = cur.fetchone()

        if not updated:
            raise HTTPException(500, "Falló el UPDATE de ballast")

        conn.commit()

        print("====== PUT BALLAST OK ======")
        print("INPUT:", draft_survey_id)
        print("REAL ID:", real_id)
        print("BALLAST ID:", updated[0])
        print("FIELDS:", len(update_fields))
        print("============================")

        return {
            "success": True,
            "action": "updated",
            "ballast_id": updated[0],
            "draft_survey_id": real_id,
            "saved_fields": len(update_fields)
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("PUT BALLAST ERROR:", str(e))
        raise HTTPException(500, f"Error actualizando ballast: {str(e)}")

    finally:
        cur.close()

    # ---------------------------------------------------------
    # GET BALLAST — ULTRA BLINDADO (ESPEJO EXACTO DEL POST)
    # ---------------------------------------------------------
    @router.get("/ballast/{draft_survey_id}")
    def get_ballast(draft_survey_id: int, conn=Depends(get_db)):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # =====================================================
            # 1) RESOLVER ID REAL (MISMA LÓGICA QUE POST)
            # =====================================================
            cur.execute("""
                SELECT id FROM draft_survey WHERE general_id = %s
            """, (draft_survey_id,))
            row = cur.fetchone()

            if not row:
                cur.execute("""
                    SELECT id FROM draft_survey WHERE id = %s
                """, (draft_survey_id,))
                row = cur.fetchone()

            if not row:
                raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

            real_id = row["id"]

            # =====================================================
            # 2) DETECTAR COLUMNAS REALES
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'draft_survey_ballast'
            """)
            cols = {r["column_name"] for r in cur.fetchall()}

            if not cols:
                raise HTTPException(500, "No se pudieron leer columnas")

            # =====================================================
            # 3) DETECTAR FK DINÁMICO
            # =====================================================
            fk_col = next(
                (c for c in ["draft_survey_id", "draftsurvey_id"] if c in cols),
                None
            )

            if not fk_col:
                raise HTTPException(500, "FK no encontrada")

            # =====================================================
            # 4) TRAER REGISTRO
            # =====================================================
            cur.execute(f"""
                SELECT *
                FROM draft_survey_ballast
                WHERE {fk_col} = %s
                LIMIT 1
            """, (real_id,))

            db_row = cur.fetchone()

            if not db_row:
                raise HTTPException(404, "No ballast encontrado")

            # =====================================================
            # 🔥 5) PRIORIZAR JSON ORIGINAL (ESPEJO PERFECTO)
            # =====================================================
            original_payload = None

            if "raw_payload" in db_row and db_row["raw_payload"]:
                original_payload = db_row["raw_payload"]

            elif "ballast_json" in db_row and db_row["ballast_json"]:
                original_payload = db_row["ballast_json"]

            # =====================================================
            # 🔥 6) RECONSTRUCCIÓN DINÁMICA (SI NO HAY JSON)
            # =====================================================
            reconstructed = {}

            if not original_payload:
                for k, v in db_row.items():
                    if k in ["id", "created_at", "updated_at"]:
                        continue
                    reconstructed[k] = v

            # =====================================================
            # 🟢 7) FRESH WATER DINÁMICO (NO ROMPE FRONT)
            # =====================================================
            fresh_water = {}

            for phase in ["init", "final"]:
                for i in range(1, 21):

                    for field in ["name", "height", "sounding", "volume", "density", "total"]:
                        key = f"{phase}_fw_{i}_{field}"

                        if key in db_row:
                            fresh_water[key] = db_row.get(key)
                        else:
                            fresh_water[key] = None

            # =====================================================
            # 🔢 8) TOTALES FW
            # =====================================================
            totals_fw = {
                "init_total_fresh_water": db_row.get("init_total_fresh_water"),
                "final_total_fresh_water": db_row.get("final_total_fresh_water")
            }

            # =====================================================
            # DEBUG
            # =====================================================
            print("====== GET BALLAST DEBUG ======")
            print("REAL ID:", real_id)
            print("USANDO JSON:", bool(original_payload))
            print("COLUMNAS DB:", len(db_row.keys()))
            print("===============================")

            # =====================================================
            # 🔥 9) RESPUESTA FINAL (ULTRA BLINDADA)
            # =====================================================
            return {
                "success": True,

                # 🔹 EXACTO LO QUE ENVIO EL FRONT (PRIORIDAD)
                "payload": original_payload if original_payload else reconstructed,

                # 🔹 DATA DB COMPLETA
                "data": db_row,

                # 🔹 FW LISTO UI
                "fresh_water": fresh_water,

                # 🔹 TOTALES
                "fresh_water_totals": totals_fw,

                # 🔹 CONTROL
                "meta": {
                    "draft_survey_id": real_id,
                    "used_json_backup": bool(original_payload),
                    "total_columns": len(db_row.keys())
                }
            }

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(500, f"Error obteniendo ballast: {str(e)}")

        finally:
            cur.close()


@router.put("/word/{draft_survey_id}")
def update_word_report(draft_survey_id: str, payload: dict, conn=Depends(get_db)):
    cur = conn.cursor()

    try:
        payload = payload or {}
        real_id = _resolve_draft_survey_real_id(cur, str(draft_survey_id))

        if not real_id:
            raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

        word_meta = _get_table_column_types(cur, "draft_survey_word_report")
        cols = {
            col
            for col in word_meta
            if col not in ("id", "created_at", "draft_survey_id")
        }

        if not cols:
            raise HTTPException(500, "No se pudieron leer columnas de draft_survey_word_report")

        cur.execute(
            """
            SELECT id, status
            FROM draft_survey_word_report
            WHERE draft_survey_id = %s
            LIMIT 1
            """,
            (real_id,)
        )
        existing = cur.fetchone()

        if not existing:
            raise HTTPException(404, "No existe registro word para actualizar")

        if len(existing) > 1 and existing[1] == "Approved":
            raise HTTPException(403, "Already approved")

        clean_payload = {}
        for key, value in payload.items():
            if key in cols:
                clean_payload[key] = value

        if "status" in cols and "status" not in clean_payload:
            clean_payload["status"] = payload.get("status") or "Pending for review"

        if "raw_payload" in cols:
            clean_payload["raw_payload"] = payload

        if "word_json" in cols:
            clean_payload["word_json"] = payload

        clean_payload = _normalize_payload_by_db_types(clean_payload, word_meta)

        if not clean_payload:
            return {
                "success": True,
                "action": "no_changes",
                "draft_survey_id": real_id
            }

        set_clause = ", ".join([f"{field} = %s" for field in clean_payload.keys()])
        values = list(clean_payload.values())

        if "updated_at" in word_meta:
            set_clause += ", updated_at = NOW()"

        values.append(real_id)

        cur.execute(
            f"""
            UPDATE draft_survey_word_report
            SET {set_clause}
            WHERE draft_survey_id = %s
            RETURNING id
            """,
            values
        )
        updated = cur.fetchone()

        if not updated:
            raise HTTPException(500, "Fallo el UPDATE de Word Report")

        conn.commit()
        return {
            "success": True,
            "action": "updated",
            "draft_survey_id": real_id,
            "saved_fields": len(clean_payload)
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error actualizando word report: {str(e)}")
    finally:
        cur.close()

    # ---------------------------------------------------------
    # PUT BALLAST — ULTRA BLINDADO (ACEPTA ID O REPORT NUMBER)
    # ---------------------------------------------------------
    @router.put("/ballast/{draft_survey_id}")
    def update_ballast(draft_survey_id: str, payload: dict, conn=Depends(get_db)):

        cur = conn.cursor()

        try:
            payload = payload or {}

            # =====================================================
            # 🔥 1) RESOLVER ID REAL (INT O STRING)
            # =====================================================
            real_id = None

            # -----------------------------------------------------
            # INT → general_id
            # -----------------------------------------------------
            if str(draft_survey_id).isdigit():

                cur.execute("""
                    SELECT id FROM draft_survey WHERE general_id = %s
                """, (int(draft_survey_id),))
                row = cur.fetchone()

                if not row:
                    cur.execute("""
                        SELECT id FROM draft_survey WHERE id = %s
                    """, (int(draft_survey_id),))
                    row = cur.fetchone()

                if row:
                    real_id = row[0]

            # -----------------------------------------------------
            # STRING → draft_report_number
            # -----------------------------------------------------
            if not real_id:

                cur.execute("""
                    SELECT id
                    FROM draft_survey
                    WHERE draft_report_number = %s
                """, (str(draft_survey_id),))
                row = cur.fetchone()

                if row:
                    real_id = row[0]

            if not real_id:
                raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

            # =====================================================
            # 🔥 2) COLUMNAS REALES
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'draft_survey_ballast'
            """)

            cols = {
                r[0]
                for r in cur.fetchall()
                if r[0] not in ("id", "created_at")
            }

            if not cols:
                raise HTTPException(500, "No se pudieron leer columnas")

            # =====================================================
            # 🔥 3) FK DETECTION
            # =====================================================
            fk_col = next(
                (c for c in ["draft_survey_id", "draftsurvey_id"] if c in cols),
                None
            )

            if not fk_col:
                raise HTTPException(500, "FK no encontrada")

            # =====================================================
            # 🔒 4) BLOQUEO APPROVED
            # =====================================================
            if "status" in cols:
                cur.execute(f"""
                    SELECT status
                    FROM draft_survey_ballast
                    WHERE {fk_col} = %s
                    LIMIT 1
                """, (real_id,))
                status_row = cur.fetchone()

                if status_row and status_row[0] == "Approved":
                    raise HTTPException(403, "Already approved")

            # =====================================================
            # 🔥 5) LIMPIEZA ROBUSTA
            # =====================================================
            def clean(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    v = v.strip()
                    if v == "" or v.lower() in ("none", "null"):
                        return None
                return v

            clean_payload = {}
            ignored_keys = []

            for k, v in payload.items():

                if not k:
                    continue

                key = str(k)

                if key in cols and key != fk_col:
                    clean_payload[key] = clean(v)
                else:
                    ignored_keys.append(key)

            # =====================================================
            # 🔥 BACKUP JSON (CRÍTICO)
            # =====================================================
            if "raw_payload" in cols:
                clean_payload["raw_payload"] = payload

            if "ballast_json" in cols:
                clean_payload["ballast_json"] = payload

            # =====================================================
            # 🔥 6) VALIDAR EXISTENCIA
            # =====================================================
            cur.execute(f"""
                SELECT id
                FROM draft_survey_ballast
                WHERE {fk_col} = %s
                LIMIT 1
            """, (real_id,))
            existing = cur.fetchone()

            if not existing:
                raise HTTPException(404, "No existe registro ballast para actualizar")

            ballast_id = existing[0]

            # =====================================================
            # 🔥 7) NO CAMBIOS
            # =====================================================
            if not clean_payload:
                return {
                    "success": True,
                    "action": "no_changes",
                    "ballast_id": ballast_id,
                    "draft_survey_id": real_id
                }

            # =====================================================
            # 🔥 8) UPDATE DINÁMICO
            # =====================================================
            has_updated_at = "updated_at" in cols

            set_clause = ", ".join([f"{f} = %s" for f in clean_payload.keys()])
            values = list(clean_payload.values())

            if has_updated_at:
                set_clause += ", updated_at = NOW()"

            values.append(ballast_id)

            cur.execute(f"""
                UPDATE draft_survey_ballast
                SET {set_clause}
                WHERE id = %s
                RETURNING id
            """, values)

            updated_id = cur.fetchone()[0]

            conn.commit()

            # =====================================================
            # DEBUG PRO
            # =====================================================
            print("====== PUT BALLAST OK ======")
            print("INPUT:", draft_survey_id)
            print("REAL ID:", real_id)
            print("UPDATED ID:", updated_id)
            print("FIELDS:", len(clean_payload))
            print("IGNORED:", len(ignored_keys))
            print("============================")

            return {
                "success": True,
                "action": "updated",
                "ballast_id": updated_id,
                "draft_survey_id": real_id,
                "saved_fields": len(clean_payload),
                "ignored_fields": len(ignored_keys)
            }

        except HTTPException:
            conn.rollback()
            raise

        except Exception as e:
            conn.rollback()
            print("PUT BALLAST ERROR:", str(e))
            raise HTTPException(500, f"Error actualizando ballast: {str(e)}")

        finally:
            cur.close()


# =========================================================
# ================= WORD REPORT (CREATE) ===================
# =========================================================
@router.post("/word/{draft_survey_id}")
def create_word(draft_survey_id: str, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # HELPERS (NO TOCAR TEXTO)
        # =====================================================
        def clean_value(v):
            if v is None:
                return None
            if isinstance(v, str) and v == "":
                return None
            return v  # 🔥 TAL CUAL

        # =====================================================
        # PARSE DATETIME FLEXIBLE
        # SOPORTA:
        # 1) "03-19-2026 14:30"
        # 2) date + time separados
        # =====================================================
        from datetime import datetime

        def split_datetime(raw):

            if not raw:
                return None, None

            if isinstance(raw, str) and " " in raw:
                try:
                    d, t = raw.split(" ")

                    # DATE
                    try:
                        date_val = datetime.strptime(d, "%m-%d-%Y").date()
                    except:
                        date_val = None

                    # TIME
                    try:
                        time_val = datetime.strptime(t, "%H:%M").time()
                    except:
                        time_val = None

                    return date_val, time_val

                except:
                    return None, None

            return None, None

        # =====================================================
        # CAMPOS BASE
        # =====================================================
        expected_fields = [
            "word_mt", "word_product", "word_vessel", "word_port", "word_country",
            "word_survey_requested_by", "word_on_behalf_of",
            "word_master", "word_chief_officer",
            "word_name", "word_port_registry", "word_grt", "word_nrt",
            "word_year", "word_imo",
            "word_metric_tons", "word_goods_product", "word_holds",
            "word_draft_figures", "word_bl_figures",
            "word_difference", "word_percentage",
            "word_shore_scale", "word_shore_bl",
            "word_shore_difference", "word_shore_percentage"
        ]

        metadata_fields = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        datetime_fields = [
            "word_arrived_buoy",
            "word_nor_tendered",
            "word_all_fast",
            "word_initial_draft",
            "word_commenced",
            "word_completed",
            "word_final_draft"
        ]

        # =====================================================
        # 1) RESOLVER ID REAL
        # =====================================================
        real_id = _resolve_draft_survey_real_id(cur, str(draft_survey_id))

        if not real_id:
            raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

        # =====================================================
        # 2) LIMPIAR BASE (SIN TOCAR TEXTO)
        # =====================================================
        cleaned = {}

        for f in expected_fields:
            cleaned[f] = clean_value(payload.get(f))

        for f in metadata_fields:
            cleaned[f] = clean_value(payload.get(f))

        # =====================================================
        # 🔥 3) DATETIME INTELIGENTE
        # =====================================================
        for f in datetime_fields:

            # PRIORIDAD 1: separados
            date_val = payload.get(f"{f}_date")
            time_val = payload.get(f"{f}_time")

            if date_val or time_val:
                try:
                    d = datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else None
                except:
                    d = None

                try:
                    t = datetime.strptime(time_val, "%H:%M").time() if time_val else None
                except:
                    t = None

            else:
                # PRIORIDAD 2: string combinado
                d, t = split_datetime(payload.get(f))

            cleaned[f"{f}_date"] = d
            cleaned[f"{f}_time"] = t

        cleaned["draft_survey_id"] = real_id
        cleaned["status"] = clean_value(payload.get("status")) or "Pending for review"

        # =====================================================
        # NORMALIZAR SEGÚN TIPOS REALES DE DB
        # =====================================================
        word_meta = _get_table_column_types(cur, "draft_survey_word_report")
        cleaned = _normalize_payload_by_db_types(cleaned, word_meta)


        # =====================================================
        # 4) UPSERT
        # =====================================================
        cur.execute(
            "SELECT id FROM draft_survey_word_report WHERE draft_survey_id = %s",
            (real_id,)
        )
        exists = cur.fetchone()

        all_fields = expected_fields + metadata_fields + \
            [f"{f}_date" for f in datetime_fields] + \
            [f"{f}_time" for f in datetime_fields]

        if exists:

            set_sql = ", ".join([f"{c} = %({c})s" for c in all_fields])

            cur.execute(f"""
                UPDATE draft_survey_word_report
                SET
                    {set_sql},
                    status = %(status)s,
                    updated_at = NOW()
                WHERE draft_survey_id = %(draft_survey_id)s
            """, cleaned)

        else:

            cols_sql = ", ".join(all_fields)
            vals_sql = ", ".join([f"%({c})s" for c in all_fields])

            cur.execute(f"""
                INSERT INTO draft_survey_word_report (
                    draft_survey_id,
                    created_at,
                    updated_at,
                    {cols_sql},
                    status
                )
                VALUES (
                    %(draft_survey_id)s,
                    NOW(),
                    NOW(),
                    {vals_sql},
                    %(status)s
                )
            """, cleaned)

        conn.commit()

        return {
            "success": True,
            "draft_survey_id": real_id,
            "status": cleaned["status"]
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("WORD ERROR:", str(e))
        raise HTTPException(500, str(e))

    finally:
        cur.close()



    # =========================================================
    # ================= WORD REPORT UPDATE ====================
    # ULTRA BLINDADO — ENTERPRISE FIXED
    # =========================================================
    @router.put("/word/{draft_survey_id}")
    def update_word(draft_survey_id: str, payload: dict, conn=Depends(get_db)):

        cur = conn.cursor()

        try:
            payload = payload or {}

            # =====================================================
            # 1) RESOLVER ID REAL
            # =====================================================
            real_id = _resolve_draft_survey_real_id(cur, str(draft_survey_id))

            if not real_id:
                raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

            # =====================================================
            # 2) COLUMNAS REALES (EXCLUYENDO SISTEMA)
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'draft_survey_word_report'
            """)

            cols = {
                r[0]
                for r in cur.fetchall()
                if r[0] not in ("id", "created_at")
            }

            if not cols:
                raise HTTPException(500, "No se pudieron leer columnas")

            # =====================================================
            # 🔒 3) BLOQUEO APPROVED
            # =====================================================
            if "status" in cols:
                cur.execute("""
                    SELECT status FROM draft_survey_word_report
                    WHERE draft_survey_id = %s
                    LIMIT 1
                """, (real_id,))
                status_row = cur.fetchone()

                if status_row and status_row[0] == "Approved":
                    raise HTTPException(403, "Already approved")

            # =====================================================
            # HELPERS
            # =====================================================
            def clean(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    v = v.strip()
                    if v == "" or v.lower() in ("none", "null"):
                        return None
                return v

            from datetime import datetime

            def split_datetime(raw):
                if not raw:
                    return None, None

                if isinstance(raw, str) and " " in raw:
                    try:
                        d, t = raw.split(" ")

                        try:
                            date_val = datetime.strptime(d, "%m-%d-%Y").date()
                        except:
                            date_val = None

                        try:
                            time_val = datetime.strptime(t, "%H:%M").time()
                        except:
                            time_val = None

                        return date_val, time_val
                    except:
                        return None, None

                return None, None

            # =====================================================
            # CAMPOS CONTROLADOS
            # =====================================================
            expected_fields = [
                "word_mt", "word_product", "word_vessel", "word_port", "word_country",
                "word_survey_requested_by", "word_on_behalf_of",
                "word_master", "word_chief_officer",
                "word_name", "word_port_registry", "word_grt", "word_nrt",
                "word_year", "word_imo",
                "word_metric_tons", "word_goods_product", "word_holds",
                "word_draft_figures", "word_bl_figures",
                "word_difference", "word_percentage",
                "word_shore_scale", "word_shore_bl",
                "word_shore_difference", "word_shore_percentage"
            ]

            metadata_fields = [
                "year", "month", "continent", "country",
                "port", "client", "draft_report_number"
            ]

            datetime_fields = [
                "word_arrived_buoy",
                "word_nor_tendered",
                "word_all_fast",
                "word_initial_draft",
                "word_commenced",
                "word_completed",
                "word_final_draft"
            ]

            # =====================================================
            # 🔥 4) LIMPIEZA + BUILD
            # =====================================================
            clean_payload = {}
            ignored_keys = []

            # normales
            for f in expected_fields + metadata_fields:
                if f in cols:
                    clean_payload[f] = clean(payload.get(f))

            # datetime robusto
            for f in datetime_fields:

                date_val = payload.get(f"{f}_date")
                time_val = payload.get(f"{f}_time")

                if date_val or time_val:
                    try:
                        d = datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else None
                    except:
                        d = None

                    try:
                        t = datetime.strptime(time_val, "%H:%M").time() if time_val else None
                    except:
                        t = None
                else:
                    d, t = split_datetime(payload.get(f))

                if f"{f}_date" in cols:
                    clean_payload[f"{f}_date"] = d

                if f"{f}_time" in cols:
                    clean_payload[f"{f}_time"] = t

            # FK (NO SE ACTUALIZA EN SET)
            fk_col = "draft_survey_id"

            # STATUS
            if "status" in cols:
                clean_payload["status"] = payload.get("status") or "Pending for review"

            # =====================================================
            # 🔥 BACKUP JSON
            # =====================================================
            if "raw_payload" in cols:
                clean_payload["raw_payload"] = payload

            if "word_json" in cols:
                clean_payload["word_json"] = payload

            # =====================================================
            # NORMALIZAR SEGÚN TIPOS REALES DE DB
            # =====================================================
            word_meta = _get_table_column_types(cur, "draft_survey_word_report")
            clean_payload = _normalize_payload_by_db_types(clean_payload, word_meta)

            # =====================================================
            # 🔥 5) VALIDAR EXISTENCIA
            # =====================================================
            cur.execute("""
                SELECT id
                FROM draft_survey_word_report
                WHERE draft_survey_id = %s
                LIMIT 1
            """, (real_id,))
            existing = cur.fetchone()

            if not existing:
                raise HTTPException(404, "No existe registro word para actualizar")

            # =====================================================
            # 🔥 6) SI NO HAY CAMBIOS
            # =====================================================
            if not clean_payload:
                return {
                    "success": True,
                    "action": "no_changes",
                    "draft_survey_id": real_id
                }

            # =====================================================
            # 🔥 7) updated_at OPCIONAL
            # =====================================================
            has_updated_at = "updated_at" in cols

            # =====================================================
            # 🔥 8) UPDATE DINÁMICO SEGURO
            # =====================================================
            set_clause = ", ".join([f"{f} = %s" for f in clean_payload.keys()])
            values = list(clean_payload.values())

            if has_updated_at:
                set_clause += ", updated_at = NOW()"

            values.append(real_id)

            # =====================================================
            # DEBUG PRO
            # =====================================================
            print("====== PUT WORD OK ======")
            print("REAL ID:", real_id)
            print("FIELDS:", len(clean_payload))
            print("=========================")

            cur.execute(f"""
                UPDATE draft_survey_word_report
                SET {set_clause}
                WHERE draft_survey_id = %s
                RETURNING id
            """, values)

            updated = cur.fetchone()

            if not updated:
                raise HTTPException(500, "Falló el UPDATE (no retornó fila)")

            conn.commit()

            return {
                "success": True,
                "action": "updated",
                "draft_survey_id": real_id,
                "saved_fields": len(clean_payload)
            }

        except HTTPException:
            conn.rollback()
            raise

        except Exception as e:
            conn.rollback()
            print("WORD PUT ERROR:", str(e))
            raise HTTPException(500, str(e))

        finally:
            cur.close()

    # =========================================================
    # ================= WORD REPORT GET =======================
    # ULTRA BLINDADO — JSON PRIORITY + DATETIME SAFE
    # =========================================================
    @router.get("/word/{draft_survey_id}")
    def get_word(draft_survey_id: int, conn=Depends(get_db)):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # =====================================================
            # 1) RESOLVER ID REAL (MISMA LÓGICA QUE POST/PUT)
            # =====================================================
            cur.execute("""
                SELECT id FROM draft_survey WHERE general_id = %s
            """, (draft_survey_id,))
            row = cur.fetchone()

            if not row:
                cur.execute("""
                    SELECT id FROM draft_survey WHERE id = %s
                """, (draft_survey_id,))
                row = cur.fetchone()

            if not row:
                raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

            real_id = row["id"]

            # =====================================================
            # 2) TRAER REGISTRO
            # =====================================================
            cur.execute("""
                SELECT *
                FROM draft_survey_word_report
                WHERE draft_survey_id = %s
                LIMIT 1
            """, (real_id,))

            db_row = cur.fetchone()

            if not db_row:
                raise HTTPException(404, "No existe word report")

            # =====================================================
            # 🔥 3) PRIORIZAR JSON ORIGINAL
            # =====================================================
            original_payload = None

            if "raw_payload" in db_row and db_row["raw_payload"]:
                original_payload = db_row["raw_payload"]

            elif "word_json" in db_row and db_row["word_json"]:
                original_payload = db_row["word_json"]

            # =====================================================
            # 🔧 4) RECONSTRUCCIÓN (SI NO HAY JSON)
            # =====================================================
            reconstructed = {}

            if not original_payload:

                for k, v in db_row.items():

                    # ignorar técnicos
                    if k in ["id", "created_at", "updated_at"]:
                        continue

                    # =================================================
                    # 🔥 RECONSTRUIR DATETIME (FORMATO FRONT)
                    # =================================================
                    if k.endswith("_date"):
                        base = k.replace("_date", "")
                        reconstructed[f"{base}_date"] = v.isoformat() if v else None

                    elif k.endswith("_time"):
                        base = k.replace("_time", "")
                        reconstructed[f"{base}_time"] = v.strftime("%H:%M") if v else None

                    else:
                        reconstructed[k] = v

            # =====================================================
            # DEBUG
            # =====================================================
            print("====== GET WORD DEBUG ======")
            print("REAL ID:", real_id)
            print("USANDO JSON:", bool(original_payload))
            print("COLUMNAS:", len(db_row.keys()))
            print("============================")

            # =====================================================
            # 🔥 RESPUESTA FINAL
            # =====================================================
            return {
                "success": True,

                # 🔹 EXACTO LO QUE ENVIO EL FRONT
                "payload": original_payload if original_payload else reconstructed,

                # 🔹 DATA COMPLETA DB
                "data": db_row,

                # 🔹 CONTROL
                "meta": {
                    "draft_survey_id": real_id,
                    "used_json_backup": bool(original_payload),
                    "total_columns": len(db_row.keys())
                }
            }

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(500, f"Error obteniendo word: {str(e)}")

        finally:
            cur.close()

