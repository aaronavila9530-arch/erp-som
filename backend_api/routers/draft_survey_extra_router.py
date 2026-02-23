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

            # ejemplo:
            # init_WBT 1P_volume → init_wbt_1p_volume
            # init_SLOP TANK_density → init_slop_tank_density
            # init_FW P_height → init_fw_p_height

            normalized[new_key] = v

        normalized["draft_survey_id"] = real_draft_id

        # =====================================================
        # 3️⃣ EXTRAER PLACEHOLDERS DEL SQL
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
        # bloquear si ya está aprobado
        cur.execute("""
            SELECT status FROM draft_survey_ballast
            WHERE draft_survey_id=%s
        """, (draft_survey_id,))

        row = cur.fetchone()

        if row and row[0] == "Approved":
            raise HTTPException(status_code=403, detail="Already approved")

        payload["draft_survey_id"] = draft_survey_id
        payload["status"] = payload.get("status", "Approved")

        cur.execute("""
            UPDATE draft_survey_ballast
            SET
                init_fpt_sounding=%(init_fpt_sounding)s,
                init_fpt_volume=%(init_fpt_volume)s,
                init_fpt_density=%(init_fpt_density)s,
                final_fw_dist_volume=%(final_fw_dist_volume)s,
                status=%(status)s,
                updated_at=NOW()
            WHERE draft_survey_id=%(draft_survey_id)s
        """, payload)

        conn.commit()
        return {"success": True, "status": payload["status"]}

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

        # =====================================================
        # NORMALIZAR VACÍOS → NULL
        # =====================================================
        cleaned_payload = {}

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

        for field in expected_fields:
            value = payload.get(field)

            if value == "" or value == "None":
                cleaned_payload[field] = None
            else:
                cleaned_payload[field] = value

        # =====================================================
        # INSERT CON TIMESTAMPS EXPLÍCITOS
        # =====================================================
        cur.execute("""
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
                status
            )
            VALUES (
                %s,
                NOW(),
                NOW(),
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                'Pending for review'
            )
        """, (
            draft_survey_id,
            cleaned_payload["word_mt"],
            cleaned_payload["word_product"],
            cleaned_payload["word_vessel"],
            cleaned_payload["word_port"],
            cleaned_payload["word_country"],
            cleaned_payload["word_survey_requested_by"],
            cleaned_payload["word_on_behalf_of"],
            cleaned_payload["word_master"],
            cleaned_payload["word_chief_officer"],
            cleaned_payload["word_name"],
            cleaned_payload["word_port_registry"],
            cleaned_payload["word_grt"],
            cleaned_payload["word_nrt"],
            cleaned_payload["word_year"],
            cleaned_payload["word_imo"],
            cleaned_payload["word_arrived_buoy"],
            cleaned_payload["word_nor_tendered"],
            cleaned_payload["word_all_fast"],
            cleaned_payload["word_initial_draft"],
            cleaned_payload["word_commenced"],
            cleaned_payload["word_completed"],
            cleaned_payload["word_final_draft"],
            cleaned_payload["word_metric_tons"],
            cleaned_payload["word_goods_product"],
            cleaned_payload["word_holds"],
            cleaned_payload["word_draft_figures"],
            cleaned_payload["word_bl_figures"],
            cleaned_payload["word_difference"],
            cleaned_payload["word_percentage"],
            cleaned_payload["word_shore_scale"],
            cleaned_payload["word_shore_bl"],
            cleaned_payload["word_shore_difference"],
            cleaned_payload["word_shore_percentage"]
        ))

        conn.commit()
        return {"success": True}

    except Exception as e:
        conn.rollback()

        # 🔴 ESTO TE VA A DECIR EL ERROR REAL EN LOG
        print("WORD INSERT ERROR:", str(e))

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()