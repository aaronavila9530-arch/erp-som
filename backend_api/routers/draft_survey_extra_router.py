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
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
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
        # 2️⃣ NORMALIZAR KEYS
        # =====================================================
        normalized = {}

        for k, v in payload.items():
            if not isinstance(k, str):
                continue

            new_key = k.lower().strip().replace(" ", "_")
            normalized[new_key] = v

        normalized["draft_survey_id"] = real_draft_id

        # =====================================================
        # 3️⃣ CONSTRUIR SQL DINÁMICO HASTA 20 TANQUES
        # =====================================================

        columns = ["draft_survey_id"]
        values = ["%(draft_survey_id)s"]

        # ---------------------------
        # FPT / APT / SLOP
        # ---------------------------
        for phase in ["init", "final"]:
            for base in ["fpt", "apt", "slop_tank"]:
                for field in ["sounding", "volume", "density"]:
                    col = f"{phase}_{base}_{field}"
                    columns.append(col)
                    values.append(f"%({col})s")

        # ---------------------------
        # WBT 1 → 20
        # ---------------------------
        for phase in ["init", "final"]:
            for i in range(1, 21):
                for side in ["p", "s"]:
                    for field in ["sounding", "volume", "density"]:
                        col = f"{phase}_wbt_{i}{side}_{field}"
                        columns.append(col)
                        values.append(f"%({col})s")

        # ---------------------------
        # FRESH WATER
        # ---------------------------
        for phase in ["init", "final"]:
            for fw in ["fw_p", "fw_s", "fw_dist"]:
                for field in ["height", "volume"]:
                    col = f"{phase}_{fw}_{field}"
                    columns.append(col)
                    values.append(f"%({col})s")

        # ---------------------------
        # METADATA
        # ---------------------------
        for m in metadata_keys:
            columns.append(m)
            values.append(f"%({m})s")

        # STATUS
        columns.append("status")
        values.append("'Pending for review'")

        # =====================================================
        # 🔧 GENERAR SQL FINAL
        # =====================================================
        sql = f"""
            INSERT INTO draft_survey_ballast (
                {", ".join(columns)}
            )
            VALUES (
                {", ".join(values)}
            )
        """

        # =====================================================
        # 🔒 RELLENAR FALTANTES CON None
        # =====================================================
        import re
        keys = re.findall(r"%\((.*?)\)s", sql)

        for k in keys:
            normalized.setdefault(k, None)

        # =====================================================
        # 🚀 EXECUTE
        # =====================================================
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
# PUT BALLAST (FULL UPDATE - DINÁMICO HASTA 20 TANQUES)
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
            WHERE draft_survey_id = %s
        """, (draft_survey_id,))

        row = cur.fetchone()

        if row and row[0] == "Approved":
            raise HTTPException(status_code=403, detail="Already approved")

        # -------------------------------------------------
        # 🔒 BLINDAJE METADATA
        # -------------------------------------------------
        metadata_keys = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        for key in metadata_keys:
            payload.setdefault(key, None)

        # -------------------------------------------------
        # 🔒 NORMALIZAR KEYS
        # -------------------------------------------------
        normalized = {}

        for k, v in payload.items():
            if not isinstance(k, str):
                continue
            new_key = k.lower().strip().replace(" ", "_")
            normalized[new_key] = v

        normalized["draft_survey_id"] = draft_survey_id
        normalized["status"] = normalized.get("status", "Approved")

        # -------------------------------------------------
        # 🔧 CONSTRUIR UPDATE DINÁMICO
        # -------------------------------------------------
        set_clauses = []

        # -------- FPT / APT / SLOP --------
        for phase in ["init", "final"]:
            for base in ["fpt", "apt", "slop_tank"]:
                for field in ["sounding", "volume", "density"]:
                    col = f"{phase}_{base}_{field}"
                    set_clauses.append(f"{col}=%({col})s")

        # -------- WBT 1 → 20 --------
        for phase in ["init", "final"]:
            for i in range(1, 21):
                for side in ["p", "s"]:
                    for field in ["sounding", "volume", "density"]:
                        col = f"{phase}_wbt_{i}{side}_{field}"
                        set_clauses.append(f"{col}=%({col})s")

        # -------- FRESH WATER --------
        for phase in ["init", "final"]:
            for fw in ["fw_p", "fw_s", "fw_dist"]:
                for field in ["height", "volume"]:
                    col = f"{phase}_{fw}_{field}"
                    set_clauses.append(f"{col}=%({col})s")

        # -------- METADATA --------
        for m in metadata_keys:
            set_clauses.append(f"{m}=%({m})s")

        # -------- STATUS + UPDATED_AT --------
        set_clauses.append("status=%(status)s")
        set_clauses.append("updated_at=NOW()")

        sql = f"""
            UPDATE draft_survey_ballast
            SET
                {", ".join(set_clauses)}
            WHERE draft_survey_id = %(draft_survey_id)s
        """

        # -------------------------------------------------
        # 🔒 RELLENAR FALTANTES CON None
        # -------------------------------------------------
        import re
        keys = re.findall(r"%\((.*?)\)s", sql)

        for k in keys:
            normalized.setdefault(k, None)

        # -------------------------------------------------
        # 🚀 EXECUTE
        # -------------------------------------------------
        cur.execute(sql, normalized)
        conn.commit()

        return {
            "success": True,
            "status": normalized["status"]
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


