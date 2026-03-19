from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
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


# =========================================================
# POST / PUT — BALLAST (CREATE / UPDATE) — BLINDADO REAL
# TAL COMO LO RECIBE DEL FRONT, ASÍ LO GUARDA
# =========================================================
@router.post("/ballast/{draft_survey_id}")
def create_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # 1) RESOLVER ID REAL DE draft_survey
        # =====================================================
        cur.execute(
            """
            SELECT id
            FROM draft_survey
            WHERE general_id = %s
            """,
            (draft_survey_id,)
        )
        row = cur.fetchone()

        if not row:
            cur.execute(
                """
                SELECT id
                FROM draft_survey
                WHERE id = %s
                """,
                (draft_survey_id,)
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No existe draft_survey {draft_survey_id}"
            )

        real_id = row[0]

        # =====================================================
        # 2) LEER COLUMNAS REALES DE LA TABLA
        # =====================================================
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'draft_survey_ballast'
            ORDER BY ordinal_position
            """
        )
        cols = {r[0] for r in cur.fetchall()}

        if not cols:
            raise HTTPException(
                status_code=500,
                detail="No se pudieron leer columnas de draft_survey_ballast"
            )

        # =====================================================
        # 3) DETECTAR FK REAL
        # =====================================================
        fk_col = None

        for candidate in ["draft_survey_id", "draftsurvey_id"]:
            if candidate in cols:
                fk_col = candidate
                break

        if not fk_col:
            raise HTTPException(
                status_code=500,
                detail="FK no encontrada en draft_survey_ballast"
            )

        # =====================================================
        # 4) LIMPIAR PAYLOAD SIN TOCAR TEXTOS
        # =====================================================
        clean_payload = {}
        ignored_keys = []

        for k, v in payload.items():

            if k is None:
                continue

            key = str(k)

            if key == "":
                continue

            if key in cols:
                clean_payload[key] = clean_value_as_is(v)
            else:
                ignored_keys.append(key)

        # =====================================================
        # 5) FORZAR FK
        # =====================================================
        clean_payload[fk_col] = real_id

        # =====================================================
        # 6) BACKUP JSON COMPLETO SI EXISTE LA COLUMNA
        # =====================================================
        if "raw_payload" in cols:
            clean_payload["raw_payload"] = payload

        if "ballast_json" in cols:
            clean_payload["ballast_json"] = payload

        # =====================================================
        # 7) DEBUG
        # =====================================================
        print("====== BALLAST DEBUG ======")
        print("GENERAL/PATH ID:", draft_survey_id)
        print("REAL DRAFT ID:", real_id)
        print("TOTAL INPUT:", len(payload))
        print("GUARDADOS:", len(clean_payload))
        print("IGNORADOS:", len(ignored_keys))
        print("SAMPLE IGNORADOS:", ignored_keys[:20])
        print("===========================")

        # =====================================================
        # 8) VERIFICAR SI YA EXISTE REGISTRO
        # =====================================================
        cur.execute(
            f"""
            SELECT id
            FROM draft_survey_ballast
            WHERE {fk_col} = %s
            LIMIT 1
            """,
            (real_id,)
        )
        existing = cur.fetchone()

        fields = list(clean_payload.keys())

        if not fields:
            raise HTTPException(
                status_code=400,
                detail="No hay campos válidos para guardar en draft_survey_ballast"
            )

        # =====================================================
        # 9) UPDATE
        # =====================================================
        if existing:
            ballast_id = existing[0]

            set_clause = ", ".join([f"{field} = %s" for field in fields])
            values = [clean_payload[field] for field in fields] + [ballast_id]

            cur.execute(
                f"""
                UPDATE draft_survey_ballast
                SET
                    {set_clause},
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                values
            )

            updated_row = cur.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo actualizar draft_survey_ballast"
                )

            ballast_id = updated_row[0]

            conn.commit()

            return {
                "success": True,
                "action": "updated",
                "ballast_id": ballast_id,
                "draft_survey_id": real_id,
                "saved_fields": len(fields),
                "ignored_fields": len(ignored_keys),
                "ignored_keys": ignored_keys
            }

        # =====================================================
        # 10) INSERT
        # =====================================================
        cols_sql = ", ".join(fields)
        vals_sql = ", ".join(["%s"] * len(fields))
        values = [clean_payload[field] for field in fields]

        cur.execute(
            f"""
            INSERT INTO draft_survey_ballast ({cols_sql})
            VALUES ({vals_sql})
            RETURNING id
            """,
            values
        )

        inserted_row = cur.fetchone()

        if not inserted_row:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear draft_survey_ballast"
            )

        ballast_id = inserted_row[0]

        conn.commit()

        return {
            "success": True,
            "action": "created",
            "ballast_id": ballast_id,
            "draft_survey_id": real_id,
            "saved_fields": len(fields),
            "ignored_fields": len(ignored_keys),
            "ignored_keys": ignored_keys
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando ballast: {str(e)}"
        )

    finally:
        cur.close()


    # ---------------------------------------------------------
    # GET BALLAST — FIX RECONSTRUCCIÓN FW (BLINDADO)
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
            # 🟢 FRESH WATER — ESTRUCTURA PLANA (COMPATIBLE FRONT)
            # =====================================================
            fresh_water = {}

            for phase in ["init", "final"]:
                for i in range(1, 21):

                    fresh_water[f"{phase}_fw_{i}_name"] = row.get(f"{phase}_fw_{i}_name")
                    fresh_water[f"{phase}_fw_{i}_height"] = row.get(f"{phase}_fw_{i}_height")
                    fresh_water[f"{phase}_fw_{i}_sounding"] = row.get(f"{phase}_fw_{i}_sounding")
                    fresh_water[f"{phase}_fw_{i}_volume"] = row.get(f"{phase}_fw_{i}_volume")
                    fresh_water[f"{phase}_fw_{i}_density"] = row.get(f"{phase}_fw_{i}_density")
                    fresh_water[f"{phase}_fw_{i}_total"] = row.get(f"{phase}_fw_{i}_total")

            # =====================================================
            # 🔢 TOTAL FW
            # =====================================================
            totals_fw = {
                "init_total_fresh_water": row.get("init_total_fresh_water"),
                "final_total_fresh_water": row.get("final_total_fresh_water")
            }

            # =====================================================
            # 🔥 RESPUESTA FINAL (BLINDADA)
            # =====================================================
            return {
                "success": True,

                # 🔹 DATA ORIGINAL (para compatibilidad legacy)
                "data": row,

                # 🔹 FW listo para UI dinámica
                "fresh_water": fresh_water,

                # 🔹 Totales
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
        cur.execute(
            "SELECT id FROM draft_survey WHERE general_id = %s",
            (draft_survey_id,)
        )
        row = cur.fetchone()
        real_id = row[0] if row else draft_survey_id

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
            "word_metric_tons", "word_goods_product", "word_holds",
            "word_draft_figures", "word_bl_figures",
            "word_difference", "word_percentage",
            "word_shore_scale", "word_shore_bl",
            "word_shore_difference", "word_shore_percentage"
        ]

        # -----------------------------------------------------
        # 🔥 DATETIME FIELDS (NUEVOS)
        # -----------------------------------------------------
        datetime_fields = [
            "word_arrived_buoy",
            "word_nor_tendered",
            "word_all_fast",
            "word_initial_draft",
            "word_commenced",
            "word_completed",
            "word_final_draft"
        ]

        # -----------------------------------------------------
        # 🔒 METADATA
        # -----------------------------------------------------
        metadata_fields = [
            "year", "month", "continent", "country",
            "port", "client", "draft_report_number"
        ]

        # -----------------------------------------------------
        # 🔒 CLEAN SIN ROMPER TEXTOS
        # -----------------------------------------------------
        def clean(v):
            if v in ["", "None", None]:
                return None
            return v  # NO tocar strings

        cleaned = {}

        # normales
        for field in expected_fields + metadata_fields:
            cleaned[field] = clean(payload.get(field))

        # -----------------------------------------------------
        # 🔥 DATETIME SEPARADO (CLAVE)
        # -----------------------------------------------------
        for key in datetime_fields:

            date_val = payload.get(f"{key}_date")
            time_val = payload.get(f"{key}_time")

            cleaned[f"{key}_date"] = clean(date_val)
            cleaned[f"{key}_time"] = clean(time_val)

        cleaned["draft_survey_id"] = draft_survey_id

        # -----------------------------------------------------
        # STATUS CONTROLADO
        # -----------------------------------------------------
        allowed_status = ["Pending for review", "Approved"]
        new_status = payload.get("status")

        if new_status not in allowed_status:
            new_status = "Pending for review"

        cleaned["status"] = new_status

        # -----------------------------------------------------
        # 🔥 SQL UPDATE (CON DATETIME NUEVO)
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

            # 🔥 NUEVO
            word_arrived_buoy_date=%(word_arrived_buoy_date)s,
            word_arrived_buoy_time=%(word_arrived_buoy_time)s,

            word_nor_tendered_date=%(word_nor_tendered_date)s,
            word_nor_tendered_time=%(word_nor_tendered_time)s,

            word_all_fast_date=%(word_all_fast_date)s,
            word_all_fast_time=%(word_all_fast_time)s,

            word_initial_draft_date=%(word_initial_draft_date)s,
            word_initial_draft_time=%(word_initial_draft_time)s,

            word_commenced_date=%(word_commenced_date)s,
            word_commenced_time=%(word_commenced_time)s,

            word_completed_date=%(word_completed_date)s,
            word_completed_time=%(word_completed_time)s,

            word_final_draft_date=%(word_final_draft_date)s,
            word_final_draft_time=%(word_final_draft_time)s,

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


