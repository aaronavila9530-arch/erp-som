from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from database import get_db
from psycopg2 import IntegrityError

router = APIRouter(
    prefix="/draft-survey",
    tags=["Draft Survey"]
)

# =========================================================
# HELPERS (NO TOCAR TEXTO)
# =========================================================

def clean_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        if v.strip().lower() in ("", "none", "null"):
            return None
        return v  # 🔥 TAL CUAL VIENE
    return v


def parse_date(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = str(value).strip()
        normalized = " ".join(text.replace(",", " ").split())

        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%b %d %Y",
            "%B %d %Y",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(normalized, fmt).date()
            except Exception:
                pass

        return datetime.fromisoformat(text[:19].replace(" ", "T")).date()

    except:
        return None


def _ensure_current_draft_form_columns(cur):
    """
    The desktop Draft Survey form has grown over time. Production databases may
    not have every technical field yet, so create missing text columns before
    dynamic insert/update logic discovers the schema.
    """
    prefixes = ("init", "final")
    draft_fields = [
        "time_from", "time_to",
        "draft_fwd_port", "draft_fwd_stb", "draft_fwd_marks",
        "draft_mid_port", "draft_mid_stb", "draft_mid_marks",
        "draft_aft_port", "draft_aft_stb", "draft_aft_marks",
        "sg", "lpp", "tpc_p", "tpc_s",
        "ballast", "fresh_water", "fuel_oil", "diesel_oil", "lub_oil",
        "slop", "swimming_pool", "others", "light_ship",
        "historic_constant", "bl_figure",
    ]
    hydro_fields = []

    for table_no in (1, 2, 3):
        hydro_fields.extend([
            f"hydro{table_no}_draft_1",
            f"hydro{table_no}_disp_1",
            f"hydro{table_no}_tpc_1",
            f"hydro{table_no}_lcf_1",
            f"hydro{table_no}_draft_2",
            f"hydro{table_no}_disp_2",
            f"hydro{table_no}_tpc_2",
            f"hydro{table_no}_lcf_2",
            f"hydro{table_no}_draft_mtc",
            f"hydro{table_no}_mtc_p50_1",
            f"hydro{table_no}_mtc_m50_1",
            f"hydro{table_no}_mtc_p50_2",
            f"hydro{table_no}_mtc_m50_2",
        ])

    columns = []
    for prefix in prefixes:
        columns.extend(f"{prefix}_{field}" for field in draft_fields)

    for prefix in prefixes:
        columns.extend(f"{prefix}_{field}" for field in hydro_fields)

    for column in columns:
        cur.execute(
            f'ALTER TABLE draft_survey ADD COLUMN IF NOT EXISTS "{column}" TEXT'
        )


# =========================================================
# FILTER SERVICIOS (DYNAMIC CASCADE FILTER)
# =========================================================

@router.get("/servicios/filter")
def filter_servicios(
    year: int | None = None,
    month: int | None = None,
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    cliente: str | None = None,
    operacion: str | None = None,
    conn=Depends(get_db)
):
    """
    Filtro dinámico tipo cascada.
    Si mando:
        year=2026
        month=1
        continente=América
    Me devuelve solo registros que cumplan.
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        base_query = """
            SELECT
                num_informe,
                buque_contenedor,
                cliente,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio
            FROM servicios
            WHERE 1=1
        """

        params = []

        # -----------------------------------------------------
        # YEAR FILTER (fecha_inicio formato YYYY-MM-DD)
        # -----------------------------------------------------
        if year:
            base_query += " AND EXTRACT(YEAR FROM fecha_inicio) = %s"
            params.append(year)

        # -----------------------------------------------------
        # MONTH FILTER
        # -----------------------------------------------------
        if month:
            base_query += " AND EXTRACT(MONTH FROM fecha_inicio) = %s"
            params.append(month)

        # -----------------------------------------------------
        # CONTINENTE
        # -----------------------------------------------------
        if continente:
            base_query += " AND continente ILIKE %s"
            params.append(continente)

        # -----------------------------------------------------
        # PAIS
        # -----------------------------------------------------
        if pais:
            base_query += " AND pais ILIKE %s"
            params.append(pais)

        # -----------------------------------------------------
        # PUERTO
        # -----------------------------------------------------
        if puerto:
            base_query += " AND puerto ILIKE %s"
            params.append(puerto)

        # -----------------------------------------------------
        # CLIENTE
        # -----------------------------------------------------
        if cliente:
            base_query += " AND cliente ILIKE %s"
            params.append(cliente)

        # -----------------------------------------------------
        # OPERACION
        # -----------------------------------------------------
        if operacion:
            base_query += " AND operacion ILIKE %s"
            params.append(operacion)

        base_query += " ORDER BY fecha_inicio DESC"

        cur.execute(base_query, params)

        rows = cur.fetchall()

        return {
            "success": True,
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()


# =========================================================
# POST — CREATE (ULTRA BLINDADO REAL 100% FIXED)
# NO INSERTA ID / CREATED_AT / UPDATED_AT
# GUARDA TODO DINÁMICO SIN ROMPER DB
# =========================================================

@router.post("/")
def create_draft_survey(payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        payload = payload or {}

        # =====================================================
        # LIMPIEZA + NORMALIZACIÓN BLINDADA
        # =====================================================
        def clean_value(v):
            if v is None:
                return None

            if isinstance(v, str):
                v = v.strip()
                if v == "" or v.lower() in ("none", "null"):
                    return None

            return v

        def parse_bool(v):
            if isinstance(v, bool):
                return v

            if v is None:
                return None

            if isinstance(v, str):
                vv = v.strip().lower()
                if vv in ("true", "1", "yes", "y", "si", "sí"):
                    return True
                if vv in ("false", "0", "no", "n"):
                    return False

            return v

        def normalize_decimal_string(v):
            """
            Convierte solo strings numéricos reales.
            Soporta coma decimal.
            No rompe textos como:
            - MV GREAT 61
            - PUERTO CALDERA
            """
            if v is None:
                return None

            if isinstance(v, (int, float, bool)):
                return v

            if isinstance(v, str):
                s = v.strip()

                if s == "":
                    return None

                # reemplazo coma → punto
                s2 = s.replace(",", ".")

                try:
                    float(s2)
                    return s2
                except Exception:
                    return v

            return v

        payload = {
            str(k): clean_value(v)
            for k, v in payload.items()
            if isinstance(k, str)
        }

        # =====================================================
        # PARSE FECHAS
        # =====================================================
        payload["init_date"] = parse_date(payload.get("init_date"))
        payload["final_date"] = parse_date(payload.get("final_date"))

        # =====================================================
        # FALLBACKS
        # =====================================================
        if payload.get("init_cargo") is None:
            payload["init_cargo"] = payload.get("cargo")

        if payload.get("init_port_from") is None:
            payload["init_port_from"] = payload.get("port_from")

        if payload.get("init_port_to") is None:
            payload["init_port_to"] = payload.get("port_to")

        if payload.get("cargo") is None:
            payload["cargo"] = payload.get("init_cargo")

        if payload.get("port_from") is None:
            payload["port_from"] = payload.get("init_port_from")

        if payload.get("port_to") is None:
            payload["port_to"] = payload.get("init_port_to")

        if payload.get("trim_tables_available") is None:
            if payload.get("trim_tables_yes") is not None:
                payload["trim_tables_available"] = parse_bool(payload.get("trim_tables_yes"))

        _ensure_current_draft_form_columns(cur)

        # =====================================================
        # 🔥 DETECTAR TIPOS REALES DE DB
        # =====================================================
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'general_draft_survey'
        """)
        general_meta = {
            row["column_name"]: row["data_type"]
            for row in cur.fetchall()
        }

        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'draft_survey'
        """)
        draft_meta = {
            row["column_name"]: row["data_type"]
            for row in cur.fetchall()
        }

        def normalize_by_db_type(key, value, meta_dict):
            if key not in meta_dict:
                return value

            dtype = (meta_dict[key] or "").lower()

            if value is None:
                return None

            if dtype in ("boolean",):
                return parse_bool(value)

            if dtype in ("date",):
                return parse_date(value)

            if dtype in (
                "integer",
                "bigint",
                "smallint",
                "numeric",
                "decimal",
                "real",
                "double precision"
            ):
                return normalize_decimal_string(value)

            return value

        # =====================================================
        # 🔥 NORMALIZAR PAYLOAD SEGÚN DB
        # =====================================================
        normalized_payload = {}

        for k, v in payload.items():

            if k in general_meta:
                normalized_payload[k] = normalize_by_db_type(k, v, general_meta)

            elif k in draft_meta:
                normalized_payload[k] = normalize_by_db_type(k, v, draft_meta)

            else:
                normalized_payload[k] = v

        payload = normalized_payload

        # =====================================================
        # VALIDACIÓN
        # =====================================================
        critical_fields = [
            "vessel_mv","survey_no","year","month",
            "continent","country","port","client","draft_report_number"
        ]

        missing = [f for f in critical_fields if not payload.get(f)]

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing)}"
            )

        # =====================================================
        # DUPLICADO
        # =====================================================
        cur.execute("""
            SELECT id FROM general_draft_survey
            WHERE draft_report_number = %s
        """, (payload["draft_report_number"],))

        if cur.fetchone():
            raise HTTPException(400, "draft_report_number already exists")

        # =====================================================
        # INSERT GENERAL
        # =====================================================
        cur.execute("""
            INSERT INTO general_draft_survey (
                vessel_mv, survey_no, call_letters, vessel_previous_names,
                flag, registry, built_year, "by",
                master, initial_surveyors, chief_officer, final_surveyors,
                chief_engineer, survey_requested_by, witness_draughts,
                on_account_of, witness_sounding, attended_also_by,
                init_ships_location, final_ships_location,
                length_overall, length_between_pp,
                extreme_breadth, moulded_breadth,
                depth_overall_incl_keel_plate, moulded_depth,
                summer_draught, summer_freeboard,
                constant_declared, constant_calculated,
                light_displacement, light_shipweight_plan,
                summer_displacement, summer_deadweight,
                net_register_tons, gross_register_tons,
                hydro_tables_issued, trim_tables_available,
                hydrometer_no,
                year, month, continent, country, port, client, draft_report_number,
                status
            )
            VALUES (
                %(vessel_mv)s, %(survey_no)s, %(call_letters)s, %(vessel_previous_names)s,
                %(flag)s, %(registry)s, %(built_year)s, %(by)s,
                %(master)s, %(initial_surveyors)s, %(chief_officer)s, %(final_surveyors)s,
                %(chief_engineer)s, %(survey_requested_by)s, %(witness_draughts)s,
                %(on_account_of)s, %(witness_sounding)s, %(attended_also_by)s,
                %(init_ships_location)s, %(final_ships_location)s,
                %(length_overall)s, %(length_between_pp)s,
                %(extreme_breadth)s, %(moulded_breadth)s,
                %(depth_overall_incl_keel_plate)s, %(moulded_depth)s,
                %(summer_draught)s, %(summer_freeboard)s,
                %(constant_declared)s, %(constant_calculated)s,
                %(light_displacement)s, %(light_shipweight_plan)s,
                %(summer_displacement)s, %(summer_deadweight)s,
                %(net_register_tons)s, %(gross_register_tons)s,
                %(hydro_tables_issued)s, %(trim_tables_available)s,
                %(hydrometer_no)s,
                %(year)s, %(month)s, %(continent)s, %(country)s, %(port)s, %(client)s, %(draft_report_number)s,
                'Pending for review'
            )
            RETURNING id
        """, payload)

        general_id = cur.fetchone()["id"]

        # =====================================================
        # 🔥 COLUMNAS REALES (EXCLUYENDO AUTO)
        # =====================================================
        cols = {
            col_name
            for col_name in draft_meta.keys()
            if col_name not in ("id", "created_at", "updated_at")
        }

        # =====================================================
        # 🔥 MAPEO DINÁMICO
        # =====================================================
        draft_data = {}

        for k, v in payload.items():
            if k in cols:
                draft_data[k] = v

        # SIEMPRE link
        draft_data["general_id"] = general_id

        # =====================================================
        # 🔥 COMPLETAR CAMPOS FALTANTES (SIN TOCAR AUTO)
        # =====================================================
        for col in cols:
            draft_data.setdefault(col, None)

        # =====================================================
        # 🔥 INSERT DINÁMICO LIMPIO
        # =====================================================
        columns = ", ".join(draft_data.keys())
        placeholders = ", ".join([f"%({k})s" for k in draft_data.keys()])

        query = f"""
            INSERT INTO draft_survey ({columns})
            VALUES ({placeholders})
        """

        cur.execute(query, draft_data)

        conn.commit()

        return {
            "success": True,
            "general_id": general_id
        }

    except IntegrityError as e:
        conn.rollback()
        raise HTTPException(400, str(e))

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Unexpected error: {str(e)}")

    finally:
        cur.close()


# =========================================================
# GET ALL (JOIN)
# =========================================================

@router.get("/")
def list_draft_surveys(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                g.id AS general_id,
                g.vessel_mv,
                g.survey_no,
                g.status AS general_status,
                d.status AS draft_status,
                d.init_date,
                d.final_date
            FROM general_draft_survey g
            LEFT JOIN draft_survey d ON g.id = d.general_id
            ORDER BY g.id DESC
        """)

        return {"success": True, "data": cur.fetchall()}

    finally:
        cur.close()


# =========================================================
# STATUS ACTIONS
# =========================================================

@router.put("/{identifier}/approve")
def approve_draft_survey(identifier: str, conn=Depends(get_db)):
    return _set_draft_status(identifier, "Approved", conn)


@router.put("/{identifier}/reject")
def reject_draft_survey(identifier: str, conn=Depends(get_db)):
    return _set_draft_status(identifier, "Rejected", conn)


def _set_draft_status(identifier: str, status: str, conn):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        general_id = None

        try:
            general_id = int(identifier)
        except Exception:
            pass

        if general_id is None:
            cur.execute(
                """
                SELECT id
                FROM general_draft_survey
                WHERE draft_report_number = %s
                LIMIT 1
                """,
                (identifier,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No existe draft_report_number {identifier}"
                )
            general_id = row["id"]

        cur.execute(
            """
            SELECT draft_report_number
            FROM general_draft_survey
            WHERE id = %s
            LIMIT 1
            """,
            (general_id,)
        )
        general_row = cur.fetchone()
        if not general_row:
            raise HTTPException(
                status_code=404,
                detail=f"No existe general_draft_survey con id {general_id}"
            )

        draft_report_number = general_row["draft_report_number"]

        for table in (
            "general_draft_survey",
            "draft_survey",
            "draft_survey_ballast",
            "draft_survey_word_report"
        ):
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                """,
                (table,)
            )
            cols = {row["column_name"] for row in cur.fetchall()}

            if "status" not in cols or "draft_report_number" not in cols:
                continue

            set_clause = "status = %s"
            if "updated_at" in cols:
                set_clause += ", updated_at = NOW()"

            cur.execute(
                f"""
                UPDATE {table}
                SET {set_clause}
                WHERE draft_report_number = %s
                """,
                (status, draft_report_number)
            )

        conn.commit()

        return {
            "success": True,
            "draft_report_number": draft_report_number,
            "status": status
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating Draft status: {str(e)}"
        )

    finally:
        cur.close()


# =========================================================
# GET BY ID (FULL JOIN)
# =========================================================

@router.get("/{general_id}")
def get_draft_survey(general_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                g.*,
                d.*
            FROM general_draft_survey g
            LEFT JOIN draft_survey d
                ON g.id = d.general_id
            WHERE g.id = %s
        """, (general_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        return {"success": True, "data": row}

    finally:
        cur.close()

# =========================================================
# PUT — UPDATE BOTH TABLES (ULTRA BLINDADO REAL)
# SOPORTA: general_id (int) Y draft_report_number (str)
# ACTUALIZA: general_draft_survey + draft_survey
# =========================================================
@router.put("/{identifier}")
def update_draft_survey(identifier: str, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        payload = payload or {}

        # =====================================================
        # 0) HELPERS
        # =====================================================
        def clean(v):
            if v is None:
                return None

            if isinstance(v, str):
                v = v.strip()
                if v == "" or v.lower() in ("none", "null"):
                    return None

            return v

        def parse_bool(v):
            if isinstance(v, bool):
                return v

            if v is None:
                return None

            if isinstance(v, str):
                vv = v.strip().lower()
                if vv in ("true", "1", "yes", "y", "si", "sí"):
                    return True
                if vv in ("false", "0", "no", "n"):
                    return False

            return v

        def parse_date_flexible(v):
            if v in (None, ""):
                return None
            if isinstance(v, datetime):
                return v.date()
            if isinstance(v, date):
                return v

            text = str(v).strip()
            normalized = " ".join(text.replace(",", " ").split())
            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%m-%d-%Y",
                "%m/%d/%Y",
                "%b %d %Y",
                "%B %d %Y",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(normalized, fmt).date()
                except Exception:
                    pass

            try:
                return datetime.fromisoformat(text[:19].replace(" ", "T")).date()
            except Exception:
                return None

        def normalize_decimal_string(v):
            """
            Solo convierte strings numéricos reales.
            No toca textos como:
            - MV ULTRA UNITY
            - NEW ORLEANS
            - ABS JAN 12 /2001
            """
            if v is None:
                return None

            if isinstance(v, (int, float, bool)):
                return v

            if isinstance(v, str):
                s = v.strip()
                if s == "":
                    return None

                # soportar coma decimal
                s2 = s.replace(",", ".")

                try:
                    # convertir solo si realmente es número puro
                    float(s2)
                    return s2
                except Exception:
                    return v

            return v

        # =====================================================
        # 1) LIMPIEZA INICIAL
        # =====================================================
        payload = {
            str(k): clean(v)
            for k, v in payload.items()
            if isinstance(k, str)
        }

        # =====================================================
        # 2) QUITAR BLOQUES QUE NO PERTENECEN A ESTE PUT
        #    (ballast / fresh_water / word se actualizan en otros PUTs)
        # =====================================================
        ignored_blocks = {"ballast", "fresh_water", "word"}
        payload = {
            k: v
            for k, v in payload.items()
            if k not in ignored_blocks and not isinstance(v, dict)
        }

        # =====================================================
        # 3) RESOLVER GENERAL_ID + DRAFT_ID
        # =====================================================
        general_id = None

        try:
            general_id = int(identifier)
        except Exception:
            pass

        if general_id is None:
            cur.execute(
                """
                SELECT id
                FROM general_draft_survey
                WHERE draft_report_number = %s
                LIMIT 1
                """,
                (identifier,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No existe draft_report_number {identifier}"
                )

            general_id = row["id"]

        # validar general
        cur.execute(
            """
            SELECT id, draft_report_number
            FROM general_draft_survey
            WHERE id = %s
            LIMIT 1
            """,
            (general_id,)
        )
        general_row = cur.fetchone()

        if not general_row:
            raise HTTPException(
                status_code=404,
                detail=f"No existe general_draft_survey con id {general_id}"
            )

        # validar draft
        cur.execute(
            """
            SELECT id, general_id, draft_report_number
            FROM draft_survey
            WHERE general_id = %s
            LIMIT 1
            """,
            (general_id,)
        )
        draft_row = cur.fetchone()

        if not draft_row:
            raise HTTPException(
                status_code=404,
                detail=f"No existe draft_survey asociado al general_id {general_id}"
            )

        draft_id = draft_row["id"]

        # =====================================================
        # 4) MAPEO DE ALIASES DEL FRONT → DB
        # =====================================================
        alias_map = {
            # general metadata
            "trim_tables_yes": "trim_tables_available",

            # draft aliases top block
            "cargo": "cargo",
            "port_from": "port_from",
            "port_to": "port_to",

            # compatibilidad inicial
            "cargo": "cargo",
            "port_from": "port_from",
            "port_to": "port_to",
        }

        normalized = {}

        for k, v in payload.items():
            target_key = alias_map.get(k, k)
            normalized[target_key] = v

        payload = normalized

        # =====================================================
        # 5) CAMPOS DERIVADOS / SINCRONIZADOS
        # =====================================================
        if "cargo" in payload:
            payload["init_cargo"] = payload["cargo"]

        if "port_from" in payload:
            payload["init_port_from"] = payload["port_from"]

        if "port_to" in payload:
            payload["init_port_to"] = payload["port_to"]

        # trim tables desde YES/NO
        if "trim_tables_available" in payload:
            payload["trim_tables_available"] = parse_bool(payload["trim_tables_available"])
        elif "trim_tables_yes" in payload:
            payload["trim_tables_available"] = parse_bool(payload["trim_tables_yes"])

        # checkboxes loading/unloading
        if "loading" in payload:
            payload["loading"] = parse_bool(payload["loading"])

        if "unloading" in payload:
            payload["unloading"] = parse_bool(payload["unloading"])

        # fechas
        if "init_date" in payload:
            payload["init_date"] = parse_date_flexible(payload.get("init_date"))

        if "final_date" in payload:
            payload["final_date"] = parse_date_flexible(payload.get("final_date"))

        _ensure_current_draft_form_columns(cur)

        # =====================================================
        # 6) DESCUBRIR COLUMNAS REALES + TIPOS
        # =====================================================
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'general_draft_survey'
            """
        )
        general_meta = {
            r["column_name"]: r["data_type"]
            for r in cur.fetchall()
        }

        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'draft_survey'
            """
        )
        draft_meta = {
            r["column_name"]: r["data_type"]
            for r in cur.fetchall()
        }

        general_cols = set(general_meta.keys())
        draft_cols = set(draft_meta.keys())

        # =====================================================
        # 7) NORMALIZAR SOLO SEGÚN TIPO REAL DB
        # =====================================================
        def normalize_by_db_type(key, value, meta_dict):
            if key not in meta_dict:
                return value

            dtype = (meta_dict[key] or "").lower()

            if value is None:
                return None

            if dtype in ("boolean",):
                return parse_bool(value)

            if dtype in ("date",):
                return parse_date_flexible(value)

            if dtype in (
                "integer",
                "bigint",
                "smallint",
                "numeric",
                "decimal",
                "real",
                "double precision"
            ):
                return normalize_decimal_string(value)

            return value

        # =====================================================
        # 8) ARMAR PAYLOADS REALES
        # =====================================================
        excluded_auto = {"id", "created_at", "updated_at", "general_id"}

        general_payload = {}
        draft_payload = {}

        for k, v in payload.items():

            if k in general_cols and k not in excluded_auto:
                general_payload[k] = normalize_by_db_type(k, v, general_meta)

            if k in draft_cols and k not in excluded_auto:
                draft_payload[k] = normalize_by_db_type(k, v, draft_meta)

        # status controlado
        allowed_status = {"Pending for review", "Approved"}

        if "status" in general_payload:
            if general_payload["status"] not in allowed_status:
                general_payload["status"] = "Pending for review"

        if "status" in draft_payload:
            if draft_payload["status"] not in allowed_status:
                draft_payload["status"] = "Pending for review"

        # =====================================================
        # 9) VALIDAR QUE HAYA CAMPOS REALES
        # =====================================================
        if not general_payload and not draft_payload:
            raise HTTPException(
                status_code=400,
                detail="El payload no contiene columnas válidas para actualizar en general_draft_survey o draft_survey"
            )


        # =====================================================
        # 🔍 DEBUG PAYLOADS
        # =====================================================
        print("===================================")
        print("GENERAL PAYLOAD:")
        print(general_payload)
        print("DRAFT PAYLOAD:")
        print(draft_payload)
        print("GENERAL ID:", general_id)
        print("DRAFT ID:", draft_id)
        print("===================================")

        # =====================================================
        # 10) UPDATE GENERAL_DRAFT_SURVEY
        # =====================================================
        general_updated = 0

        if general_payload:
            set_clause = ", ".join([f"{k} = %s" for k in general_payload.keys()])
            values = list(general_payload.values())
            values.append(general_id)

            sql = f"""
                UPDATE general_draft_survey
                SET {set_clause},
                    updated_at = NOW()
                WHERE id = %s
            """

            cur.execute(sql, values)
            general_updated = cur.rowcount

            if general_updated == 0:
                raise HTTPException(
                    status_code=409,
                    detail="No se actualizó ninguna fila en general_draft_survey"
                )

        # =====================================================
        # 11) UPDATE DRAFT_SURVEY
        # =====================================================
        draft_updated = 0

        if draft_payload:
            set_clause = ", ".join([f"{k} = %s" for k in draft_payload.keys()])
            values = list(draft_payload.values())
            values.append(draft_id)

            sql = f"""
                UPDATE draft_survey
                SET {set_clause},
                    updated_at = NOW()
                WHERE id = %s
            """

            cur.execute(sql, values)
            draft_updated = cur.rowcount

            if draft_updated == 0:
                raise HTTPException(
                    status_code=409,
                    detail="No se actualizó ninguna fila en draft_survey"
                )

        # =====================================================
        # 12) COMMIT
        # =====================================================
        conn.commit()

        # =====================================================
        # 13) RESPUESTA FINAL
        # =====================================================
        return {
            "success": True,
            "general_id": general_id,
            "draft_id": draft_id,
            "general_updated": general_updated,
            "draft_updated": draft_updated
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()


# =========================================================
# Preview
# =========================================================


@router.post("/preview/excel")
def preview_draft_survey_excel(payload: dict):

    try:
        from services.draft_survey_excel_service import generate_draft_survey_excel
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Excel preview service unavailable: {e}"
        )

    try:
        file_path = generate_draft_survey_excel(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating excel preview: {e}")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Draft_Survey_Preview.xlsx"
    )
