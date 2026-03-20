from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime
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
        raw = str(value).split(" ")[0]

        if "-" in raw and len(raw.split("-")[0]) == 4:
            return datetime.strptime(raw, "%Y-%m-%d").date()

        return datetime.strptime(raw, "%d-%m-%Y").date()

    except:
        return None


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
        # LIMPIEZA MINIMA
        # =====================================================
        def clean_value(v):
            if v is None:
                return None
            if isinstance(v, str):
                v = v.strip()
                if v == "":
                    return None
            return v

        payload = {
            k: clean_value(v)
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
                payload["trim_tables_available"] = bool(payload.get("trim_tables_yes"))

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
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'draft_survey'
        """)
        cols = {
            row["column_name"]
            for row in cur.fetchall()
            if row["column_name"] not in ("id", "created_at", "updated_at")
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
    # PUT — UPDATE BOTH TABLES (FIX REAL PRODUCCIÓN)
    # =========================================================
    @router.put("/{identifier}")
    def update_draft_survey(identifier: str, payload: dict, conn=Depends(get_db)):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            payload = payload or {}

            # =====================================================
            # 0) RESOLVER GENERAL_ID
            # =====================================================
            try:
                general_id = int(identifier)
            except:
                cur.execute("""
                    SELECT id
                    FROM general_draft_survey
                    WHERE draft_report_number = %s
                """, (identifier,))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(404, f"No existe {identifier}")

                general_id = row["id"]

            # =====================================================
            # 1) CLEAN
            # =====================================================
            def clean(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    v = v.strip()
                    if v == "" or v.lower() in ("none", "null"):
                        return None
                return v

            payload = {k: clean(v) for k, v in payload.items() if isinstance(k, str)}

            # =====================================================
            # 2) NORMALIZACIONES CRÍTICAS (TU CASO REAL)
            # =====================================================

            # 🔥 trim_tables
            if "trim_tables_yes" in payload or "trim_tables_no" in payload:
                payload["trim_tables_available"] = bool(payload.get("trim_tables_yes"))

            # 🔥 cargo / ports → draft_survey
            if "cargo" in payload:
                payload["init_cargo"] = payload["cargo"]

            if "port_from" in payload:
                payload["init_port_from"] = payload["port_from"]

            if "port_to" in payload:
                payload["init_port_to"] = payload["port_to"]

            # =====================================================
            # 3) FECHAS
            # =====================================================
            payload["init_date"] = parse_date(payload.get("init_date"))
            payload["final_date"] = parse_date(payload.get("final_date"))

            # =====================================================
            # 4) VALIDACIONES
            # =====================================================
            cur.execute("SELECT id FROM general_draft_survey WHERE id = %s", (general_id,))
            if not cur.fetchone():
                raise HTTPException(404, "General no existe")

            cur.execute("SELECT id FROM draft_survey WHERE general_id = %s", (general_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Draft no existe")

            # =====================================================
            # 5) COLUMNAS
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'general_draft_survey'
            """)
            general_cols = {r["column_name"] for r in cur.fetchall()}

            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'draft_survey'
            """)
            draft_cols = {r["column_name"] for r in cur.fetchall()}

            # =====================================================
            # 6) SPLIT REAL + DEBUG
            # =====================================================
            general_payload = {}
            draft_payload = {}
            ignored = []

            for k, v in payload.items():

                if k in general_cols:
                    general_payload[k] = v

                elif k in draft_cols:
                    draft_payload[k] = v

                else:
                    ignored.append(k)

            print("IGNORED:", ignored)
            print("GENERAL KEYS:", list(general_payload.keys()))
            print("DRAFT KEYS:", list(draft_payload.keys()))

            # =====================================================
            # 🚨 NO MÁS SILENCIO
            # =====================================================
            if not general_payload and not draft_payload:
                raise HTTPException(
                    400,
                    "NO HAY CAMPOS VÁLIDOS PARA UPDATE"
                )

            # =====================================================
            # 7) UPDATE GENERAL
            # =====================================================
            if general_payload:

                set_clause = ", ".join([f"{k} = %s" for k in general_payload])
                values = list(general_payload.values())

                set_clause += ", updated_at = NOW()"
                values.append(general_id)

                cur.execute(f"""
                    UPDATE general_draft_survey
                    SET {set_clause}
                    WHERE id = %s
                """, values)

                print("UPDATED GENERAL:", cur.rowcount)

            # =====================================================
            # 8) UPDATE DRAFT
            # =====================================================
            if draft_payload:

                set_clause = ", ".join([f"{k} = %s" for k in draft_payload])
                values = list(draft_payload.values())

                set_clause += ", updated_at = NOW()"
                values.append(general_id)

                cur.execute(f"""
                    UPDATE draft_survey
                    SET {set_clause}
                    WHERE general_id = %s
                """, values)

                print("UPDATED DRAFT:", cur.rowcount)

            # =====================================================
            # 9) COMMIT REAL
            # =====================================================
            conn.commit()

            return {
                "success": True,
                "general_updated": len(general_payload),
                "draft_updated": len(draft_payload)
            }

        except HTTPException:
            conn.rollback()
            raise

        except Exception as e:
            conn.rollback()
            print("ERROR:", str(e))
            raise HTTPException(500, str(e))

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