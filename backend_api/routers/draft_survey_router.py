from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime
from database import get_db  # ← usa tu get_db existente

router = APIRouter(
    prefix="/draft-survey",
    tags=["Draft Survey"]
)


# =========================================================
# HELPERS
# =========================================================

def parse_date(value):
    if not value:
        return None
    try:
        if "-" in value and len(value.split("-")[0]) == 4:
            return datetime.strptime(value.split(" ")[0], "%Y-%m-%d").date()
        return datetime.strptime(value.split(" ")[0], "%d-%m-%Y").date()
    except Exception:
        return None


def safe(payload, key):
    v = payload.get(key)
    return v if v not in ["", None] else None


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
# POST — CREATE (BOTH TABLES)
# =========================================================

@router.post("/")
def create_draft_survey(payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ==============================
        # NORMALIZACIONES
        # ==============================
        payload["init_date"] = parse_date(payload.get("init_date"))
        payload["final_date"] = parse_date(payload.get("final_date"))

        # =====================================================
        # 1️⃣ INSERT GENERAL (STATUS FORZADO)
        # =====================================================
        cur.execute("""
            INSERT INTO general_draft_survey (
                vessel_mv, survey_no, call_letters, vessel_previous_names,
                flag, registry, built_year, by,
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
                'Pending for review'
            )
            RETURNING id
        """, payload)

        general_id = cur.fetchone()["id"]

        # =====================================================
        # 2️⃣ INSERT DRAFT (STATUS FORZADO)
        # =====================================================
        draft_data = payload.copy()
        draft_data["general_id"] = general_id

        cur.execute("""
            INSERT INTO draft_survey (
                general_id,

                init_date, init_time_from, init_time_to,
                cargo, port_from, port_to, loading, unloading,

                init_draft_fwd_port, init_draft_fwd_stb,
                init_draft_mid_port, init_draft_mid_stb,
                init_draft_aft_port, init_draft_aft_stb,
                init_draft_fwd_marks, init_draft_mid_marks, init_draft_aft_marks,
                init_sg,
                init_lpp,
                init_tpc_p, init_tpc_s,
                init_bl_figure,
                init_slop, init_swimming_pool,
                init_ballast, init_fresh_water, init_fuel_oil,
                init_diesel_oil, init_lub_oil,
                init_others, init_deductions,

                final_date, final_time_from, final_time_to,
                final_draft_fwd_port, final_draft_fwd_stb,
                final_draft_mid_port, final_draft_mid_stb,
                final_draft_aft_port, final_draft_aft_stb,
                final_draft_fwd_marks, final_draft_mid_marks, final_draft_aft_marks,
                final_sg,
                final_lpp,
                final_tpc_p, final_tpc_s,
                final_bl_figure,
                final_slop, final_swimming_pool,
                final_ballast, final_fresh_water, final_fuel_oil,
                final_diesel_oil, final_lub_oil,
                final_others, final_deductions,

                init_hydro1_draft_1, init_hydro1_disp_1, init_hydro1_tpc_1, init_hydro1_lcf_1,
                init_hydro1_draft_2, init_hydro1_disp_2, init_hydro1_tpc_2, init_hydro1_lcf_2,
                init_hydro1_draft_mtc, init_hydro1_mtc_p50_1, init_hydro1_mtc_m50_1,
                init_hydro1_mtc_p50_2, init_hydro1_mtc_m50_2,

                init_hydro2_draft_1, init_hydro2_disp_1, init_hydro2_tpc_1, init_hydro2_lcf_1,
                init_hydro2_draft_2, init_hydro2_disp_2, init_hydro2_tpc_2, init_hydro2_lcf_2,
                init_hydro2_draft_mtc, init_hydro2_mtc_p50_1, init_hydro2_mtc_m50_1,
                init_hydro2_mtc_p50_2, init_hydro2_mtc_m50_2,

                status
            )
            VALUES (
                %(general_id)s,

                %(init_date)s, %(init_time_from)s, %(init_time_to)s,
                %(cargo)s, %(port_from)s, %(port_to)s, %(loading)s, %(unloading)s,

                %(init_draft_fwd_port)s, %(init_draft_fwd_stb)s,
                %(init_draft_mid_port)s, %(init_draft_mid_stb)s,
                %(init_draft_aft_port)s, %(init_draft_aft_stb)s,
                %(init_draft_fwd_marks)s, %(init_draft_mid_marks)s, %(init_draft_aft_marks)s,
                %(init_sg)s,
                %(init_lpp)s,
                %(init_tpc_p)s, %(init_tpc_s)s,
                %(init_bl_figure)s,
                %(init_slop)s, %(init_swimming_pool)s,
                %(init_ballast)s, %(init_fresh_water)s, %(init_fuel_oil)s,
                %(init_diesel_oil)s, %(init_lub_oil)s,
                %(init_others)s, %(init_deductions)s,

                %(final_date)s, %(final_time_from)s, %(final_time_to)s,
                %(final_draft_fwd_port)s, %(final_draft_fwd_stb)s,
                %(final_draft_mid_port)s, %(final_draft_mid_stb)s,
                %(final_draft_aft_port)s, %(final_draft_aft_stb)s,
                %(final_draft_fwd_marks)s, %(final_draft_mid_marks)s, %(final_draft_aft_marks)s,
                %(final_sg)s,
                %(final_lpp)s,
                %(final_tpc_p)s, %(final_tpc_s)s,
                %(final_bl_figure)s,
                %(final_slop)s, %(final_swimming_pool)s,
                %(final_ballast)s, %(final_fresh_water)s, %(final_fuel_oil)s,
                %(final_diesel_oil)s, %(final_lub_oil)s,
                %(final_others)s, %(final_deductions)s,

                %(init_hydro1_draft_1)s, %(init_hydro1_disp_1)s, %(init_hydro1_tpc_1)s, %(init_hydro1_lcf_1)s,
                %(init_hydro1_draft_2)s, %(init_hydro1_disp_2)s, %(init_hydro1_tpc_2)s, %(init_hydro1_lcf_2)s,
                %(init_hydro1_draft_mtc)s, %(init_hydro1_mtc_p50_1)s, %(init_hydro1_mtc_m50_1)s,
                %(init_hydro1_mtc_p50_2)s, %(init_hydro1_mtc_m50_2)s,

                %(init_hydro2_draft_1)s, %(init_hydro2_disp_1)s, %(init_hydro2_tpc_1)s, %(init_hydro2_lcf_1)s,
                %(init_hydro2_draft_2)s, %(init_hydro2_disp_2)s, %(init_hydro2_tpc_2)s, %(init_hydro2_lcf_2)s,
                %(init_hydro2_draft_mtc)s, %(init_hydro2_mtc_p50_1)s, %(init_hydro2_mtc_m50_1)s,
                %(init_hydro2_mtc_p50_2)s, %(init_hydro2_mtc_m50_2)s,

                'Pending for review'
            )
        """, draft_data)

        conn.commit()

        return {"success": True, "general_id": general_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
# PUT — UPDATE BOTH TABLES
# =========================================================

@router.put("/{general_id}")
def update_draft_survey(general_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ===============================
        # NORMALIZACIONES
        # ===============================
        payload["init_date"] = parse_date(payload.get("init_date"))
        payload["final_date"] = parse_date(payload.get("final_date"))

        # ===============================
        # STATUS CONTROLADO
        # ===============================
        allowed_status = ["Pending for review", "Approved"]

        new_status = payload.get("status")

        if new_status not in allowed_status:
            new_status = "Pending for review"

        # =====================================================
        # UPDATE GENERAL (100% CAMPOS)
        # =====================================================
        cur.execute("""
            UPDATE general_draft_survey
            SET
                vessel_mv=%(vessel_mv)s,
                survey_no=%(survey_no)s,
                call_letters=%(call_letters)s,
                vessel_previous_names=%(vessel_previous_names)s,
                flag=%(flag)s,
                registry=%(registry)s,
                built_year=%(built_year)s,
                by=%(by)s,
                master=%(master)s,
                initial_surveyors=%(initial_surveyors)s,
                chief_officer=%(chief_officer)s,
                final_surveyors=%(final_surveyors)s,
                chief_engineer=%(chief_engineer)s,
                survey_requested_by=%(survey_requested_by)s,
                witness_draughts=%(witness_draughts)s,
                on_account_of=%(on_account_of)s,
                witness_sounding=%(witness_sounding)s,
                attended_also_by=%(attended_also_by)s,
                init_ships_location=%(init_ships_location)s,
                final_ships_location=%(final_ships_location)s,
                length_overall=%(length_overall)s,
                length_between_pp=%(length_between_pp)s,
                extreme_breadth=%(extreme_breadth)s,
                moulded_breadth=%(moulded_breadth)s,
                depth_overall_incl_keel_plate=%(depth_overall_incl_keel_plate)s,
                moulded_depth=%(moulded_depth)s,
                summer_draught=%(summer_draught)s,
                summer_freeboard=%(summer_freeboard)s,
                constant_declared=%(constant_declared)s,
                constant_calculated=%(constant_calculated)s,
                light_displacement=%(light_displacement)s,
                light_shipweight_plan=%(light_shipweight_plan)s,
                summer_displacement=%(summer_displacement)s,
                summer_deadweight=%(summer_deadweight)s,
                net_register_tons=%(net_register_tons)s,
                gross_register_tons=%(gross_register_tons)s,
                hydro_tables_issued=%(hydro_tables_issued)s,
                trim_tables_available=%(trim_tables_available)s,
                hydrometer_no=%(hydrometer_no)s,
                status=%(status)s,
                updated_at=NOW()
            WHERE id=%(general_id)s
        """, {**payload, "general_id": general_id, "status": new_status})

        # =====================================================
        # UPDATE DRAFT (100% CAMPOS)
        # =====================================================
        cur.execute("""
            UPDATE draft_survey
            SET
                init_date=%(init_date)s,
                init_time_from=%(init_time_from)s,
                init_time_to=%(init_time_to)s,

                cargo=%(cargo)s,
                port_from=%(port_from)s,
                port_to=%(port_to)s,
                loading=%(loading)s,
                unloading=%(unloading)s,

                init_draft_fwd_port=%(init_draft_fwd_port)s,
                init_draft_fwd_stb=%(init_draft_fwd_stb)s,
                init_draft_mid_port=%(init_draft_mid_port)s,
                init_draft_mid_stb=%(init_draft_mid_stb)s,
                init_draft_aft_port=%(init_draft_aft_port)s,
                init_draft_aft_stb=%(init_draft_aft_stb)s,

                init_draft_fwd_marks=%(init_draft_fwd_marks)s,
                init_draft_mid_marks=%(init_draft_mid_marks)s,
                init_draft_aft_marks=%(init_draft_aft_marks)s,

                init_sg=%(init_sg)s,
                init_lpp=%(init_lpp)s,
                init_tpc_p=%(init_tpc_p)s,
                init_tpc_s=%(init_tpc_s)s,
                init_bl_figure=%(init_bl_figure)s,
                init_slop=%(init_slop)s,
                init_swimming_pool=%(init_swimming_pool)s,

                init_ballast=%(init_ballast)s,
                init_fresh_water=%(init_fresh_water)s,
                init_fuel_oil=%(init_fuel_oil)s,
                init_diesel_oil=%(init_diesel_oil)s,
                init_lub_oil=%(init_lub_oil)s,
                init_others=%(init_others)s,
                init_deductions=%(init_deductions)s,

                final_date=%(final_date)s,
                final_time_from=%(final_time_from)s,
                final_time_to=%(final_time_to)s,

                final_draft_fwd_port=%(final_draft_fwd_port)s,
                final_draft_fwd_stb=%(final_draft_fwd_stb)s,
                final_draft_mid_port=%(final_draft_mid_port)s,
                final_draft_mid_stb=%(final_draft_mid_stb)s,
                final_draft_aft_port=%(final_draft_aft_port)s,
                final_draft_aft_stb=%(final_draft_aft_stb)s,

                final_draft_fwd_marks=%(final_draft_fwd_marks)s,
                final_draft_mid_marks=%(final_draft_mid_marks)s,
                final_draft_aft_marks=%(final_draft_aft_marks)s,

                final_sg=%(final_sg)s,
                final_lpp=%(final_lpp)s,
                final_tpc_p=%(final_tpc_p)s,
                final_tpc_s=%(final_tpc_s)s,
                final_bl_figure=%(final_bl_figure)s,
                final_slop=%(final_slop)s,
                final_swimming_pool=%(final_swimming_pool)s,

                final_ballast=%(final_ballast)s,
                final_fresh_water=%(final_fresh_water)s,
                final_fuel_oil=%(final_fuel_oil)s,
                final_diesel_oil=%(final_diesel_oil)s,
                final_lub_oil=%(final_lub_oil)s,
                final_others=%(final_others)s,
                final_deductions=%(final_deductions)s,

                init_hydro1_draft_1=%(init_hydro1_draft_1)s,
                init_hydro1_disp_1=%(init_hydro1_disp_1)s,
                init_hydro1_tpc_1=%(init_hydro1_tpc_1)s,
                init_hydro1_lcf_1=%(init_hydro1_lcf_1)s,
                init_hydro1_draft_2=%(init_hydro1_draft_2)s,
                init_hydro1_disp_2=%(init_hydro1_disp_2)s,
                init_hydro1_tpc_2=%(init_hydro1_tpc_2)s,
                init_hydro1_lcf_2=%(init_hydro1_lcf_2)s,
                init_hydro1_draft_mtc=%(init_hydro1_draft_mtc)s,
                init_hydro1_mtc_p50_1=%(init_hydro1_mtc_p50_1)s,
                init_hydro1_mtc_m50_1=%(init_hydro1_mtc_m50_1)s,
                init_hydro1_mtc_p50_2=%(init_hydro1_mtc_p50_2)s,
                init_hydro1_mtc_m50_2=%(init_hydro1_mtc_m50_2)s,

                init_hydro2_draft_1=%(init_hydro2_draft_1)s,
                init_hydro2_disp_1=%(init_hydro2_disp_1)s,
                init_hydro2_tpc_1=%(init_hydro2_tpc_1)s,
                init_hydro2_lcf_1=%(init_hydro2_lcf_1)s,
                init_hydro2_draft_2=%(init_hydro2_draft_2)s,
                init_hydro2_disp_2=%(init_hydro2_disp_2)s,
                init_hydro2_tpc_2=%(init_hydro2_tpc_2)s,
                init_hydro2_lcf_2=%(init_hydro2_lcf_2)s,
                init_hydro2_draft_mtc=%(init_hydro2_draft_mtc)s,
                init_hydro2_mtc_p50_1=%(init_hydro2_mtc_p50_1)s,
                init_hydro2_mtc_m50_1=%(init_hydro2_mtc_m50_1)s,
                init_hydro2_mtc_p50_2=%(init_hydro2_mtc_p50_2)s,
                init_hydro2_mtc_m50_2=%(init_hydro2_mtc_m50_2)s,

                status=%(status)s,
                updated_at=NOW()

            WHERE general_id=%(general_id)s
        """, {**payload, "general_id": general_id, "status": new_status})

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