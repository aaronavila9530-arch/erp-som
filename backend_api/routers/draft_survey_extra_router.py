# =========================================================
# DRAFT SURVEY EXTRA ROUTER
# Ballast + Word Report
# =========================================================

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from database import get_db

router = APIRouter(
    prefix="/draft-survey-extra",
    tags=["Draft Survey Extra"]
)

@router.post("/ballast/{draft_survey_id}")
def create_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # 🔒 BLINDAJE METADATA
        # =====================================================
        metadata_keys = [
            "year","month","continent","country",
            "port","client","draft_report_number"
        ]

        for key in metadata_keys:
            payload.setdefault(key, None)

        # =====================================================
        # 1️⃣ RESOLVER draft_survey.id REAL DESDE general_id
        # =====================================================
        cur.execute(
            "SELECT id FROM draft_survey WHERE general_id = %s",
            (draft_survey_id,)
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"draft_survey_id {draft_survey_id} does not exist"
            )

        real_draft_id = row[0]

        # =====================================================
        # 2️⃣ NORMALIZAR KEYS DEL FRONTEND
        # =====================================================
        normalized = {}

        for k, v in payload.items():

            if not isinstance(k, str):
                continue

            new_key = (
                k.lower()
                 .replace(" ", "_")
                 .replace("tank", "tank")
            )

            normalized[new_key] = v

        normalized["draft_survey_id"] = real_draft_id

        # =====================================================
        # 3️⃣ INSERT 100% ALINEADO CON DB
        # =====================================================
        sql = """
        INSERT INTO draft_survey_ballast (
            draft_survey_id,

            init_fpt_sounding, init_fpt_volume, init_fpt_density,
            init_wbt_1p_sounding, init_wbt_1p_volume, init_wbt_1p_density,
            init_wbt_1s_sounding, init_wbt_1s_volume, init_wbt_1s_density,
            init_wbt_2p_sounding, init_wbt_2p_volume, init_wbt_2p_density,
            init_wbt_2s_sounding, init_wbt_2s_volume, init_wbt_2s_density,
            init_wbt_3p_sounding, init_wbt_3p_volume, init_wbt_3p_density,
            init_wbt_3s_sounding, init_wbt_3s_volume, init_wbt_3s_density,
            init_wbt_4p_sounding, init_wbt_4p_volume, init_wbt_4p_density,
            init_wbt_4s_sounding, init_wbt_4s_volume, init_wbt_4s_density,
            init_wbt_5p_sounding, init_wbt_5p_volume, init_wbt_5p_density,
            init_wbt_5s_sounding, init_wbt_5s_volume, init_wbt_5s_density,
            init_apt_sounding, init_apt_volume, init_apt_density,
            init_slop_tank_sounding, init_slop_tank_volume, init_slop_tank_density,
            init_fw_p_height, init_fw_p_volume,
            init_fw_s_height, init_fw_s_volume,
            init_fw_dist_height, init_fw_dist_volume,

            final_fpt_sounding, final_fpt_volume, final_fpt_density,
            final_wbt_1p_sounding, final_wbt_1p_volume, final_wbt_1p_density,
            final_wbt_1s_sounding, final_wbt_1s_volume, final_wbt_1s_density,
            final_wbt_2p_sounding, final_wbt_2p_volume, final_wbt_2p_density,
            final_wbt_2s_sounding, final_wbt_2s_volume, final_wbt_2s_density,
            final_wbt_3p_sounding, final_wbt_3p_volume, final_wbt_3p_density,
            final_wbt_3s_sounding, final_wbt_3s_volume, final_wbt_3s_density,
            final_wbt_4p_sounding, final_wbt_4p_volume, final_wbt_4p_density,
            final_wbt_4s_sounding, final_wbt_4s_volume, final_wbt_4s_density,
            final_wbt_5p_sounding, final_wbt_5p_volume, final_wbt_5p_density,
            final_wbt_5s_sounding, final_wbt_5s_volume, final_wbt_5s_density,
            final_apt_sounding, final_apt_volume, final_apt_density,
            final_slop_tank_sounding, final_slop_tank_volume, final_slop_tank_density,
            final_fw_p_height, final_fw_p_volume,
            final_fw_s_height, final_fw_s_volume,
            final_fw_dist_height, final_fw_dist_volume,

            -- 🔵 NUEVO METADATA
            year, month, continent, country, port, client, draft_report_number,

            status
        )
        VALUES (
            %(draft_survey_id)s,

            %(init_fpt_sounding)s, %(init_fpt_volume)s, %(init_fpt_density)s,
            %(init_wbt_1p_sounding)s, %(init_wbt_1p_volume)s, %(init_wbt_1p_density)s,
            %(init_wbt_1s_sounding)s, %(init_wbt_1s_volume)s, %(init_wbt_1s_density)s,
            %(init_wbt_2p_sounding)s, %(init_wbt_2p_volume)s, %(init_wbt_2p_density)s,
            %(init_wbt_2s_sounding)s, %(init_wbt_2s_volume)s, %(init_wbt_2s_density)s,
            %(init_wbt_3p_sounding)s, %(init_wbt_3p_volume)s, %(init_wbt_3p_density)s,
            %(init_wbt_3s_sounding)s, %(init_wbt_3s_volume)s, %(init_wbt_3s_density)s,
            %(init_wbt_4p_sounding)s, %(init_wbt_4p_volume)s, %(init_wbt_4p_density)s,
            %(init_wbt_4s_sounding)s, %(init_wbt_4s_volume)s, %(init_wbt_4s_density)s,
            %(init_wbt_5p_sounding)s, %(init_wbt_5p_volume)s, %(init_wbt_5p_density)s,
            %(init_wbt_5s_sounding)s, %(init_wbt_5s_volume)s, %(init_wbt_5s_density)s,
            %(init_apt_sounding)s, %(init_apt_volume)s, %(init_apt_density)s,
            %(init_slop_tank_sounding)s, %(init_slop_tank_volume)s, %(init_slop_tank_density)s,
            %(init_fw_p_height)s, %(init_fw_p_volume)s,
            %(init_fw_s_height)s, %(init_fw_s_volume)s,
            %(init_fw_dist_height)s, %(init_fw_dist_volume)s,

            %(final_fpt_sounding)s, %(final_fpt_volume)s, %(final_fpt_density)s,
            %(final_wbt_1p_sounding)s, %(final_wbt_1p_volume)s, %(final_wbt_1p_density)s,
            %(final_wbt_1s_sounding)s, %(final_wbt_1s_volume)s, %(final_wbt_1s_density)s,
            %(final_wbt_2p_sounding)s, %(final_wbt_2p_volume)s, %(final_wbt_2p_density)s,
            %(final_wbt_2s_sounding)s, %(final_wbt_2s_volume)s, %(final_wbt_2s_density)s,
            %(final_wbt_3p_sounding)s, %(final_wbt_3p_volume)s, %(final_wbt_3p_density)s,
            %(final_wbt_3s_sounding)s, %(final_wbt_3s_volume)s, %(final_wbt_3s_density)s,
            %(final_wbt_4p_sounding)s, %(final_wbt_4p_volume)s, %(final_wbt_4p_density)s,
            %(final_wbt_4s_sounding)s, %(final_wbt_4s_volume)s, %(final_wbt_4s_density)s,
            %(final_wbt_5p_sounding)s, %(final_wbt_5p_volume)s, %(final_wbt_5p_density)s,
            %(final_wbt_5s_sounding)s, %(final_wbt_5s_volume)s, %(final_wbt_5s_density)s,
            %(final_apt_sounding)s, %(final_apt_volume)s, %(final_apt_density)s,
            %(final_slop_tank_sounding)s, %(final_slop_tank_volume)s, %(final_slop_tank_density)s,
            %(final_fw_p_height)s, %(final_fw_p_volume)s,
            %(final_fw_s_height)s, %(final_fw_s_volume)s,
            %(final_fw_dist_height)s, %(final_fw_dist_volume)s,

            %(year)s, %(month)s, %(continent)s, %(country)s, %(port)s, %(client)s, %(draft_report_number)s,

            'Pending for review'
        )
        """

        # rellenar faltantes con None
        import re
        keys = re.findall(r"%\((.*?)\)s", sql)
        for k in keys:
            normalized.setdefault(k, None)

        cur.execute(sql, normalized)
        conn.commit()

        return {"success": True}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()

# ---------------------------------------------------------
# GET BALLAST
# ---------------------------------------------------------

@router.get("/ballast/{draft_survey_id}")
def get_ballast(draft_survey_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT *
            FROM draft_survey_ballast
            WHERE draft_survey_id=%s
        """, (draft_survey_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        return {"success": True, "data": row}

    finally:
        cur.close()

# ---------------------------------------------------------
# PUT BALLAST (FULL UPDATE)
# ---------------------------------------------------------

@router.put("/ballast/{draft_survey_id}")
def update_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # -------------------------------------------------
        # 🔒 BLOQUEAR SI YA ESTÁ APROBADO
        # -------------------------------------------------
        cur.execute("""
            SELECT status FROM draft_survey_ballast
            WHERE draft_survey_id=%s
        """, (draft_survey_id,))

        row = cur.fetchone()

        if row and row[0] == "Approved":
            raise HTTPException(status_code=403, detail="Already approved")

        # -------------------------------------------------
        # 🔒 BLINDAJE METADATA
        # -------------------------------------------------
        metadata_keys = [
            "year","month","continent","country",
            "port","client","draft_report_number"
        ]

        for key in metadata_keys:
            payload.setdefault(key, None)

        payload["draft_survey_id"] = draft_survey_id
        payload["status"] = payload.get("status", "Approved")

        # -------------------------------------------------
        # FULL UPDATE 1:1 CON LA TABLA
        # -------------------------------------------------
        sql = """
        UPDATE draft_survey_ballast
        SET
            init_fpt_sounding=%(init_fpt_sounding)s,
            init_fpt_volume=%(init_fpt_volume)s,
            init_fpt_density=%(init_fpt_density)s,

            init_wbt_1p_sounding=%(init_wbt_1p_sounding)s,
            init_wbt_1p_volume=%(init_wbt_1p_volume)s,
            init_wbt_1p_density=%(init_wbt_1p_density)s,
            init_wbt_1s_sounding=%(init_wbt_1s_sounding)s,
            init_wbt_1s_volume=%(init_wbt_1s_volume)s,
            init_wbt_1s_density=%(init_wbt_1s_density)s,
            init_wbt_2p_sounding=%(init_wbt_2p_sounding)s,
            init_wbt_2p_volume=%(init_wbt_2p_volume)s,
            init_wbt_2p_density=%(init_wbt_2p_density)s,
            init_wbt_2s_sounding=%(init_wbt_2s_sounding)s,
            init_wbt_2s_volume=%(init_wbt_2s_volume)s,
            init_wbt_2s_density=%(init_wbt_2s_density)s,
            init_wbt_3p_sounding=%(init_wbt_3p_sounding)s,
            init_wbt_3p_volume=%(init_wbt_3p_volume)s,
            init_wbt_3p_density=%(init_wbt_3p_density)s,
            init_wbt_3s_sounding=%(init_wbt_3s_sounding)s,
            init_wbt_3s_volume=%(init_wbt_3s_volume)s,
            init_wbt_3s_density=%(init_wbt_3s_density)s,
            init_wbt_4p_sounding=%(init_wbt_4p_sounding)s,
            init_wbt_4p_volume=%(init_wbt_4p_volume)s,
            init_wbt_4p_density=%(init_wbt_4p_density)s,
            init_wbt_4s_sounding=%(init_wbt_4s_sounding)s,
            init_wbt_4s_volume=%(init_wbt_4s_volume)s,
            init_wbt_4s_density=%(init_wbt_4s_density)s,
            init_wbt_5p_sounding=%(init_wbt_5p_sounding)s,
            init_wbt_5p_volume=%(init_wbt_5p_volume)s,
            init_wbt_5p_density=%(init_wbt_5p_density)s,
            init_wbt_5s_sounding=%(init_wbt_5s_sounding)s,
            init_wbt_5s_volume=%(init_wbt_5s_volume)s,
            init_wbt_5s_density=%(init_wbt_5s_density)s,
            init_apt_sounding=%(init_apt_sounding)s,
            init_apt_volume=%(init_apt_volume)s,
            init_apt_density=%(init_apt_density)s,
            init_slop_tank_sounding=%(init_slop_tank_sounding)s,
            init_slop_tank_volume=%(init_slop_tank_volume)s,
            init_slop_tank_density=%(init_slop_tank_density)s,

            init_fw_p_height=%(init_fw_p_height)s,
            init_fw_p_volume=%(init_fw_p_volume)s,
            init_fw_s_height=%(init_fw_s_height)s,
            init_fw_s_volume=%(init_fw_s_volume)s,
            init_fw_dist_height=%(init_fw_dist_height)s,
            init_fw_dist_volume=%(init_fw_dist_volume)s,

            final_fpt_sounding=%(final_fpt_sounding)s,
            final_fpt_volume=%(final_fpt_volume)s,
            final_fpt_density=%(final_fpt_density)s,

            final_wbt_1p_sounding=%(final_wbt_1p_sounding)s,
            final_wbt_1p_volume=%(final_wbt_1p_volume)s,
            final_wbt_1p_density=%(final_wbt_1p_density)s,
            final_wbt_1s_sounding=%(final_wbt_1s_sounding)s,
            final_wbt_1s_volume=%(final_wbt_1s_volume)s,
            final_wbt_1s_density=%(final_wbt_1s_density)s,
            final_wbt_2p_sounding=%(final_wbt_2p_sounding)s,
            final_wbt_2p_volume=%(final_wbt_2p_volume)s,
            final_wbt_2p_density=%(final_wbt_2p_density)s,
            final_wbt_2s_sounding=%(final_wbt_2s_sounding)s,
            final_wbt_2s_volume=%(final_wbt_2s_volume)s,
            final_wbt_2s_density=%(final_wbt_2s_density)s,
            final_wbt_3p_sounding=%(final_wbt_3p_sounding)s,
            final_wbt_3p_volume=%(final_wbt_3p_volume)s,
            final_wbt_3p_density=%(final_wbt_3p_density)s,
            final_wbt_3s_sounding=%(final_wbt_3s_sounding)s,
            final_wbt_3s_volume=%(final_wbt_3s_volume)s,
            final_wbt_3s_density=%(final_wbt_3s_density)s,
            final_wbt_4p_sounding=%(final_wbt_4p_sounding)s,
            final_wbt_4p_volume=%(final_wbt_4p_volume)s,
            final_wbt_4p_density=%(final_wbt_4p_density)s,
            final_wbt_4s_sounding=%(final_wbt_4s_sounding)s,
            final_wbt_4s_volume=%(final_wbt_4s_volume)s,
            final_wbt_4s_density=%(final_wbt_4s_density)s,
            final_wbt_5p_sounding=%(final_wbt_5p_sounding)s,
            final_wbt_5p_volume=%(final_wbt_5p_volume)s,
            final_wbt_5p_density=%(final_wbt_5p_density)s,
            final_wbt_5s_sounding=%(final_wbt_5s_sounding)s,
            final_wbt_5s_volume=%(final_wbt_5s_volume)s,
            final_wbt_5s_density=%(final_wbt_5s_density)s,
            final_apt_sounding=%(final_apt_sounding)s,
            final_apt_volume=%(final_apt_volume)s,
            final_apt_density=%(final_apt_density)s,
            final_slop_tank_sounding=%(final_slop_tank_sounding)s,
            final_slop_tank_volume=%(final_slop_tank_volume)s,
            final_slop_tank_density=%(final_slop_tank_density)s,

            final_fw_p_height=%(final_fw_p_height)s,
            final_fw_p_volume=%(final_fw_p_volume)s,
            final_fw_s_height=%(final_fw_s_height)s,
            final_fw_s_volume=%(final_fw_s_volume)s,
            final_fw_dist_height=%(final_fw_dist_height)s,
            final_fw_dist_volume=%(final_fw_dist_volume)s,

            year=%(year)s,
            month=%(month)s,
            continent=%(continent)s,
            country=%(country)s,
            port=%(port)s,
            client=%(client)s,
            draft_report_number=%(draft_report_number)s,

            status=%(status)s,
            updated_at=NOW()

        WHERE draft_survey_id=%(draft_survey_id)s
        """

        cur.execute(sql, payload)

        conn.commit()

        return {
            "success": True,
            "status": payload["status"]
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()


# =========================================================
# ================= WORD REPORT ===========================
# =========================================================

@router.post("/word/{draft_survey_id}")
def create_word(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:

        payload = payload or {}

        # =====================================================
        # 🔒 CAMPOS WORD ESPERADOS
        # =====================================================
        expected_fields = [
            "word_mt", "word_product", "word_vessel", "word_port", "word_country",
            "word_survey_requested_by", "word_on_behalf_of",
            "word_master", "word_chief_officer",
            "word_name", "word_port_registry", "word_grt", "word_nrt",
            "word_year", "word_imo",
            "word_arrived_buoy", "word_nor_tendered",
            "word_all_fast", "word_initial_draft",
            "word_commenced", "word_completed", "word_final_draft",
            "word_metric_tons", "word_goods_product", "word_holds",
            "word_draft_figures", "word_bl_figures",
            "word_difference", "word_percentage",
            "word_shore_scale", "word_shore_bl",
            "word_shore_difference", "word_shore_percentage"
        ]

        # =====================================================
        # 🔒 METADATA (ALINEADO CON TABLA)
        # =====================================================
        metadata_fields = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        # =====================================================
        # 🔒 NORMALIZACIÓN + BLINDAJE
        # =====================================================
        cleaned = {}

        for field in expected_fields + metadata_fields:
            value = payload.get(field)
            cleaned[field] = None if value in ["", "None", None] else value

        cleaned["draft_survey_id"] = draft_survey_id

        # Status controlado
        cleaned["status"] = payload.get("status", "Pending for review")

        # =====================================================
        # INSERT 100% 1:1 CON LA TABLA
        # =====================================================
        sql = """
            INSERT INTO draft_survey_word_report (
                draft_survey_id,
                created_at,
                updated_at,

                word_mt, word_product, word_vessel, word_port, word_country,
                word_survey_requested_by, word_on_behalf_of,
                word_master, word_chief_officer,
                word_name, word_port_registry, word_grt, word_nrt,
                word_year, word_imo,
                word_arrived_buoy, word_nor_tendered,
                word_all_fast, word_initial_draft,
                word_commenced, word_completed, word_final_draft,
                word_metric_tons, word_goods_product, word_holds,
                word_draft_figures, word_bl_figures,
                word_difference, word_percentage,
                word_shore_scale, word_shore_bl,
                word_shore_difference, word_shore_percentage,

                year, month, continent, country,
                port, client, draft_report_number,

                status
            )
            VALUES (
                %(draft_survey_id)s,
                NOW(),
                NOW(),

                %(word_mt)s, %(word_product)s, %(word_vessel)s, %(word_port)s, %(word_country)s,
                %(word_survey_requested_by)s, %(word_on_behalf_of)s,
                %(word_master)s, %(word_chief_officer)s,
                %(word_name)s, %(word_port_registry)s, %(word_grt)s, %(word_nrt)s,
                %(word_year)s, %(word_imo)s,
                %(word_arrived_buoy)s, %(word_nor_tendered)s,
                %(word_all_fast)s, %(word_initial_draft)s,
                %(word_commenced)s, %(word_completed)s, %(word_final_draft)s,
                %(word_metric_tons)s, %(word_goods_product)s, %(word_holds)s,
                %(word_draft_figures)s, %(word_bl_figures)s,
                %(word_difference)s, %(word_percentage)s,
                %(word_shore_scale)s, %(word_shore_bl)s,
                %(word_shore_difference)s, %(word_shore_percentage)s,

                %(year)s, %(month)s, %(continent)s, %(country)s,
                %(port)s, %(client)s, %(draft_report_number)s,

                %(status)s
            )
        """

        cur.execute(sql, cleaned)

        conn.commit()

        return {
            "success": True,
            "status": cleaned["status"]
        }

    except Exception as e:
        conn.rollback()
        print("WORD INSERT ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()



# =========================================================
# ================= WORD REPORT UPDATE ====================
# =========================================================

@router.put("/word/{draft_survey_id}")
def update_word(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:

        payload = payload or {}

        # -----------------------------------------------------
        # 🔒 BLOQUEAR SI YA ESTÁ APROBADO
        # -----------------------------------------------------
        cur.execute("""
            SELECT status
            FROM draft_survey_word_report
            WHERE draft_survey_id = %s
        """, (draft_survey_id,))

        row = cur.fetchone()

        if row and row[0] == "Approved":
            raise HTTPException(status_code=403, detail="Already approved")

        # -----------------------------------------------------
        # 🔒 CAMPOS WORD
        # -----------------------------------------------------
        expected_fields = [
            "word_mt", "word_product", "word_vessel", "word_port", "word_country",
            "word_survey_requested_by", "word_on_behalf_of",
            "word_master", "word_chief_officer",
            "word_name", "word_port_registry", "word_grt", "word_nrt",
            "word_year", "word_imo",
            "word_arrived_buoy", "word_nor_tendered",
            "word_all_fast", "word_initial_draft",
            "word_commenced", "word_completed", "word_final_draft",
            "word_metric_tons", "word_goods_product", "word_holds",
            "word_draft_figures", "word_bl_figures",
            "word_difference", "word_percentage",
            "word_shore_scale", "word_shore_bl",
            "word_shore_difference", "word_shore_percentage"
        ]

        # -----------------------------------------------------
        # 🔒 METADATA
        # -----------------------------------------------------
        metadata_fields = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        # -----------------------------------------------------
        # 🔒 NORMALIZAR + BLINDAR
        # -----------------------------------------------------
        cleaned = {}

        for field in expected_fields + metadata_fields:
            value = payload.get(field)
            cleaned[field] = None if value in ["", "None", None] else value

        cleaned["draft_survey_id"] = draft_survey_id

        # Status controlado
        allowed_status = ["Pending for review", "Approved"]
        new_status = payload.get("status")

        if new_status not in allowed_status:
            new_status = "Pending for review"

        cleaned["status"] = new_status

        # -----------------------------------------------------
        # FULL UPDATE 1:1
        # -----------------------------------------------------
        sql = """
        UPDATE draft_survey_word_report
        SET
            word_mt=%(word_mt)s,
            word_product=%(word_product)s,
            word_vessel=%(word_vessel)s,
            word_port=%(word_port)s,
            word_country=%(word_country)s,

            word_survey_requested_by=%(word_survey_requested_by)s,
            word_on_behalf_of=%(word_on_behalf_of)s,

            word_master=%(word_master)s,
            word_chief_officer=%(word_chief_officer)s,

            word_name=%(word_name)s,
            word_port_registry=%(word_port_registry)s,
            word_grt=%(word_grt)s,
            word_nrt=%(word_nrt)s,

            word_year=%(word_year)s,
            word_imo=%(word_imo)s,

            word_arrived_buoy=%(word_arrived_buoy)s,
            word_nor_tendered=%(word_nor_tendered)s,
            word_all_fast=%(word_all_fast)s,
            word_initial_draft=%(word_initial_draft)s,
            word_commenced=%(word_commenced)s,
            word_completed=%(word_completed)s,
            word_final_draft=%(word_final_draft)s,

            word_metric_tons=%(word_metric_tons)s,
            word_goods_product=%(word_goods_product)s,
            word_holds=%(word_holds)s,

            word_draft_figures=%(word_draft_figures)s,
            word_bl_figures=%(word_bl_figures)s,
            word_difference=%(word_difference)s,
            word_percentage=%(word_percentage)s,

            word_shore_scale=%(word_shore_scale)s,
            word_shore_bl=%(word_shore_bl)s,
            word_shore_difference=%(word_shore_difference)s,
            word_shore_percentage=%(word_shore_percentage)s,

            year=%(year)s,
            month=%(month)s,
            continent=%(continent)s,
            country=%(country)s,
            port=%(port)s,
            client=%(client)s,
            draft_report_number=%(draft_report_number)s,

            status=%(status)s,
            updated_at=NOW()

        WHERE draft_survey_id=%(draft_survey_id)s
        """

        cur.execute(sql, cleaned)

        conn.commit()

        return {
            "success": True,
            "status": new_status
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()


