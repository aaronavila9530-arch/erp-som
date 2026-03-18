# =========================================================
# DRAFT SURVEY EXTRA ROUTER
# Ballast + Word Report
# =========================================================

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from database import get_db


def normalize_numeric(v):

    if v is None:
        return None

    if isinstance(v, str):

        vv = v.strip()

        if vv == "":
            return None

        vv = vv.replace(",", ".")

        try:
            return float(vv)
        except:
            return vv

    return v


router = APIRouter(
    prefix="/draft-survey-extra",
    tags=["Draft Survey Extra"]
)

# =========================================================
# POST / PUT — BALLAST (CREATE / UPDATE) — ULTRA MAX PRO
# =========================================================
@router.post("/ballast/{draft_survey_id}")
def create_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # 1) RESOLVER ID REAL
        # =====================================================
        cur.execute("SELECT id FROM draft_survey WHERE general_id = %s", (draft_survey_id,))
        row = cur.fetchone()

        if not row:
            cur.execute("SELECT id FROM draft_survey WHERE id = %s", (draft_survey_id,))
            row = cur.fetchone()

        if not row:
            raise HTTPException(404, f"No existe draft_survey {draft_survey_id}")

        real_id = row[0]

        # =====================================================
        # 2) COLUMNAS + TIPOS
        # =====================================================
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'draft_survey_ballast'
        """)

        col_types = {r[0]: r[1] for r in cur.fetchall()}
        cols = set(col_types.keys())

        # =====================================================
        # 3) CLEAN INTELIGENTE
        # =====================================================
        def clean(key, value):

            if value is None:
                return None

            if isinstance(value, str):
                value = value.strip()

                if value == "":
                    return None

                value = value.replace(",", ".")

            col_type = col_types.get(key, "")

            if col_type in ["double precision", "numeric", "real"]:
                try:
                    return float(value)
                except:
                    return None

            if "char" in col_type or col_type == "text":
                return str(value)

            return value

        # =====================================================
        # 🔥 4) NORMALIZAR PAYLOAD COMPLETO
        # =====================================================
        clean_payload = {}
        ignored_keys = []

        for k, v in payload.items():

            key = str(k).strip()

            if not key:
                continue

            if key in cols:
                clean_payload[key] = clean(key, v)
            else:
                ignored_keys.append(key)

        # =====================================================
        # 🔥 5) FORZAR FW (aunque columnas no existan)
        # =====================================================
        fw_detected = [k for k in payload.keys() if "_fw_" in k]

        if fw_detected:
            print("🔥 FW DETECTADO:", len(fw_detected), "campos")

        # =====================================================
        # 6) FK
        # =====================================================
        fk_col = next((c for c in ["draft_survey_id", "draftsurvey_id"] if c in cols), None)

        if not fk_col:
            raise HTTPException(500, "FK no encontrada")

        clean_payload[fk_col] = real_id

        # =====================================================
        # 🔥 7) JSON BACKUP SIEMPRE COMPLETO
        # =====================================================
        if "raw_payload" in cols:
            clean_payload["raw_payload"] = payload

        if "ballast_json" in cols:
            clean_payload["ballast_json"] = payload

        # =====================================================
        # 🔥 DEBUG NIVEL DIOS
        # =====================================================
        print("====== BALLAST DEBUG ======")
        print("REAL ID:", real_id)
        print("TOTAL INPUT:", len(payload))
        print("GUARDADOS:", len(clean_payload))
        print("IGNORADOS:", len(ignored_keys))
        print("SAMPLE IGNORADOS:", ignored_keys[:10])
        print("===========================")

        # =====================================================
        # 🔥 8) UPSERT
        # =====================================================
        cur.execute(f"""
            SELECT id FROM draft_survey_ballast
            WHERE {fk_col} = %s
            LIMIT 1
        """, (real_id,))
        existing = cur.fetchone()

        fields = list(clean_payload.keys())

        if existing:
            ballast_id = existing[0]

            set_clause = ", ".join([f"{c} = %s" for c in fields])
            values = [clean_payload[c] for c in fields] + [ballast_id]

            cur.execute(f"""
                UPDATE draft_survey_ballast
                SET {set_clause},
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, values)

            ballast_id = cur.fetchone()[0]

            conn.commit()

            return {
                "success": True,
                "action": "updated",
                "ballast_id": ballast_id,
                "saved_fields": len(fields),
                "ignored_fields": len(ignored_keys)
            }

        else:
            cols_sql = ", ".join(fields)
            vals_sql = ", ".join(["%s"] * len(fields))
            values = [clean_payload[c] for c in fields]

            cur.execute(f"""
                INSERT INTO draft_survey_ballast ({cols_sql})
                VALUES ({vals_sql})
                RETURNING id
            """, values)

            ballast_id = cur.fetchone()[0]

            conn.commit()

            return {
                "success": True,
                "action": "created",
                "ballast_id": ballast_id,
                "saved_fields": len(fields),
                "ignored_fields": len(ignored_keys)
            }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error guardando ballast: {str(e)}")

    finally:
        cur.close()


# ---------------------------------------------------------
# GET BALLAST — FIX RECONSTRUCCIÓN FW
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

        # =====================================================
        # 🔥 RECONSTRUIR FRESH WATER
        # =====================================================
        fresh_water = {
            "init": [],
            "final": []
        }

        for phase in ["init", "final"]:
            for i in range(1, 21):

                name = row.get(f"{phase}_fw_{i}_name")
                height = row.get(f"{phase}_fw_{i}_height")
                sounding = row.get(f"{phase}_fw_{i}_sounding")
                volume = row.get(f"{phase}_fw_{i}_volume")
                density = row.get(f"{phase}_fw_{i}_density")
                total = row.get(f"{phase}_fw_{i}_total")

                # 🔥 SOLO AGREGAR SI HAY DATA REAL
                if any([name, height, sounding, volume, density, total]):

                    fresh_water[phase].append({
                        "tank_name": name,
                        "height": height,
                        "sounding": sounding,
                        "volume": volume,
                        "density": density,
                        "total": total
                    })

        # =====================================================
        # 🔥 TOTAL FW
        # =====================================================
        totals_fw = {
            "init": row.get("init_total_fresh_water"),
            "final": row.get("final_total_fresh_water")
        }

        # =====================================================
        # 🔥 RESPUESTA FINAL
        # =====================================================
        return {
            "success": True,
            "data": row,
            "fresh_water": fresh_water,
            "fresh_water_totals": totals_fw
        }

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

            # limpiar vacíos
            if v is None:
                value = None

            elif isinstance(v, str):
                vv = v.strip()

                if vv.lower() in ("", "none", "null", "empty"):
                    value = None
                else:
                    value = vv

            else:
                value = v

            # normalizar números (coma decimal → punto)
            value = normalize_numeric(value)

            normalized[new_key] = value

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

        # -------- FRESH WATER (DINÁMICO 1 → 20) --------
        for phase in ["init", "final"]:
            for i in range(1, 21):
                for field in ["height", "volume"]:
                    col = f"{phase}_fw_{i}_{field}"
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
# ================= WORD REPORT (CREATE) ===================
# =========================================================
@router.post("/word/{draft_survey_id}")
def create_word(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # 🔒 CAMPOS WORD ESPERADOS (NO OBLIGA A LLENAR)
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
        # 🔒 METADATA
        # =====================================================
        metadata_fields = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        # =====================================================
        # 🔧 NORMALIZADOR NUMÉRICO ULTRA BLINDADO
        # =====================================================
        def normalize_numeric(v):

            if v is None:
                return None

            if isinstance(v, str):

                vv = v.strip()

                if vv.lower() in ("", "none", "null", "empty"):
                    return None

                # eliminar separador miles
                vv = vv.replace(",", "")

	        # eliminar espacios internos
                vv = vv.replace(" ", "")

                try:
                    return float(vv)
                except:
                    return vv

            return v

        # =====================================================
        # 🔧 LIMPIEZA GENERAL DE VALORES
        # =====================================================
        def _clean_value(v):

            if v is None:
                return None

            if isinstance(v, str):

                vv = v.strip()

                if vv.lower() in ("", "none", "null", "empty"):
                    return None

                return normalize_numeric(vv)

            return normalize_numeric(v)

        # =====================================================
        # 1️⃣ RESOLVER draft_survey.id REAL
        # =====================================================
        cur.execute(
            "SELECT id FROM draft_survey WHERE general_id = %s",
            (draft_survey_id,)
        )

        row = cur.fetchone()

        if row:
            real_draft_id = row[0]
        else:
            real_draft_id = draft_survey_id

        # =====================================================
        # 2️⃣ LIMPIAR PAYLOAD
        # =====================================================
        cleaned = {}

        for field in expected_fields:
            cleaned[field] = _clean_value(payload.get(field))

        for field in metadata_fields:
            cleaned[field] = _clean_value(payload.get(field))

        cleaned["draft_survey_id"] = real_draft_id
        cleaned["status"] = _clean_value(payload.get("status")) or "Pending for review"

        # =====================================================
        # 3️⃣ UPSERT
        # =====================================================
        cur.execute(
            "SELECT id FROM draft_survey_word_report WHERE draft_survey_id = %s",
            (real_draft_id,)
        )

        exists = cur.fetchone()

        if exists:

            set_parts = []

            for col in expected_fields + metadata_fields:
                set_parts.append(f"{col} = %({col})s")

            update_sql = f"""
                UPDATE draft_survey_word_report
                SET
                    {", ".join(set_parts)},
                    updated_at = NOW(),
                    status = %(status)s
                WHERE draft_survey_id = %(draft_survey_id)s
            """

            cur.execute(update_sql, cleaned)

        else:

            insert_sql = """
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

            cur.execute(insert_sql, cleaned)

        conn.commit()

        return {
            "success": True,
            "draft_survey_id": real_draft_id,
            "status": cleaned["status"]
        }

    except HTTPException:
        conn.rollback()
        raise

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


