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
# POST / PUT — BALLAST (CREATE / UPDATE) — ULTRA BLINDADO REAL
# GUARDA EXACTAMENTE LO QUE VIENE DEL FRONT
# =========================================================
@router.post("/ballast/{draft_survey_id}")
def create_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # =====================================================
        # HELPER: NO TOCAR TEXTO
        # =====================================================
        def clean_value_as_is(v):
            if v is None:
                return None
            if isinstance(v, str) and v == "":
                return None
            return v

        # =====================================================
        # 1) RESOLVER ID REAL
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

        real_id = row[0]

        # =====================================================
        # 2) COLUMNAS REALES
        # =====================================================
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'draft_survey_ballast'
        """)
        cols = {r[0] for r in cur.fetchall()}

        if not cols:
            raise HTTPException(500, "No se pudieron leer columnas")

        # =====================================================
        # 3) FK
        # =====================================================
        fk_col = next(
            (c for c in ["draft_survey_id", "draftsurvey_id"] if c in cols),
            None
        )

        if not fk_col:
            raise HTTPException(500, "FK no encontrada")

        # =====================================================
        # 4) LIMPIAR PAYLOAD (SIN TOCAR TEXTO)
        # =====================================================
        clean_payload = {}
        ignored_keys = []

        for k, v in payload.items():

            if not k:
                continue

            key = str(k)

            if key in cols:
                clean_payload[key] = clean_value_as_is(v)
            else:
                ignored_keys.append(key)

        # =====================================================
        # 🔥 5) FORZAR FK SIEMPRE
        # =====================================================
        clean_payload[fk_col] = real_id

        # =====================================================
        # 🔥 6) BACKUP JSON (SI EXISTE)
        # =====================================================
        if "raw_payload" in cols:
            clean_payload["raw_payload"] = payload

        if "ballast_json" in cols:
            clean_payload["ballast_json"] = payload

        # =====================================================
        # 🔥 7) FALLBACK: SI SOLO VIENE FK → IGUAL INSERTAR
        # =====================================================
        fields = list(clean_payload.keys())

        if not fields:
            # 🔥 FORZAR MINIMO INSERT
            fields = [fk_col]
            clean_payload = {fk_col: real_id}

        # =====================================================
        # DEBUG
        # =====================================================
        print("====== BALLAST DEBUG ======")
        print("REAL ID:", real_id)
        print("FIELDS:", fields)
        print("TOTAL INPUT:", len(payload))
        print("IGNORADOS:", len(ignored_keys))
        print("===========================")

        # =====================================================
        # 8) EXISTING
        # =====================================================
        cur.execute(f"""
            SELECT id
            FROM draft_survey_ballast
            WHERE {fk_col} = %s
            LIMIT 1
        """, (real_id,))
        existing = cur.fetchone()

        # =====================================================
        # 9) UPDATE
        # =====================================================
        if existing:

            ballast_id = existing[0]

            set_clause = ", ".join([f"{f} = %s" for f in fields])
            values = [clean_payload[f] for f in fields] + [ballast_id]

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
                "draft_survey_id": real_id,
                "saved_fields": len(fields),
                "ignored_fields": len(ignored_keys)
            }

        # =====================================================
        # 10) INSERT (SIEMPRE FUNCIONA)
        # =====================================================
        cols_sql = ", ".join(fields)
        vals_sql = ", ".join(["%s"] * len(fields))
        values = [clean_payload[f] for f in fields]

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
            "draft_survey_id": real_id,
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

    # ---------------------------------------------------------
    # PUT BALLAST — ULTRA BLINDADO (ESPEJO DEL POST)
    # ---------------------------------------------------------
    @router.put("/ballast/{draft_survey_id}")
    def update_ballast(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

        cur = conn.cursor()

        try:
            payload = payload or {}

            # =====================================================
            # 1) RESOLVER ID REAL (MISMA LÓGICA POST/GET)
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

            real_id = row[0]

            # =====================================================
            # 2) DETECTAR COLUMNAS REALES
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'draft_survey_ballast'
            """)
            cols = {r[0] for r in cur.fetchall()}

            if not cols:
                raise HTTPException(500, "No se pudieron leer columnas")

            # =====================================================
            # 3) DETECTAR FK
            # =====================================================
            fk_col = next(
                (c for c in ["draft_survey_id", "draftsurvey_id"] if c in cols),
                None
            )

            if not fk_col:
                raise HTTPException(500, "FK no encontrada")

            # =====================================================
            # 🔒 4) BLOQUEAR SI APPROVED
            # =====================================================
            if "status" in cols:
                cur.execute(f"""
                    SELECT status FROM draft_survey_ballast
                    WHERE {fk_col} = %s
                    LIMIT 1
                """, (real_id,))
                status_row = cur.fetchone()

                if status_row and status_row[0] == "Approved":
                    raise HTTPException(403, "Already approved")

            # =====================================================
            # 5) LIMPIAR PAYLOAD (SIN ALTERAR TEXTO)
            # =====================================================
            def clean_value_as_is(v):
                if v is None:
                    return None
                if isinstance(v, str) and v == "":
                    return None
                return v

            clean_payload = {}
            ignored_keys = []

            for k, v in payload.items():

                if not k:
                    continue

                key = str(k)

                if key in cols:
                    clean_payload[key] = clean_value_as_is(v)
                else:
                    ignored_keys.append(key)

            # =====================================================
            # 🔥 6) FORZAR FK
            # =====================================================
            clean_payload[fk_col] = real_id

            # =====================================================
            # 🔥 7) BACKUP JSON (CRÍTICO)
            # =====================================================
            if "raw_payload" in cols:
                clean_payload["raw_payload"] = payload

            if "ballast_json" in cols:
                clean_payload["ballast_json"] = payload

            # =====================================================
            # 🔧 8) CAMPOS A ACTUALIZAR
            # =====================================================
            fields = list(clean_payload.keys())

            if not fields:
                fields = [fk_col]
                clean_payload = {fk_col: real_id}

            # =====================================================
            # DEBUG
            # =====================================================
            print("====== PUT BALLAST DEBUG ======")
            print("REAL ID:", real_id)
            print("FIELDS:", fields)
            print("TOTAL INPUT:", len(payload))
            print("IGNORADOS:", len(ignored_keys))
            print("===============================")

            # =====================================================
            # 9) VALIDAR EXISTENCIA
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
            # 🔥 10) UPDATE DINÁMICO REAL
            # =====================================================
            set_clause = ", ".join([f"{f} = %s" for f in fields])
            values = [clean_payload[f] for f in fields] + [ballast_id]

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
                "draft_survey_id": real_id,
                "saved_fields": len(fields),
                "ignored_fields": len(ignored_keys)
            }

        except HTTPException:
            conn.rollback()
            raise

        except Exception as e:
            conn.rollback()
            raise HTTPException(500, f"Error actualizando ballast: {str(e)}")

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
    # ULTRA BLINDADO — DINÁMICO + DATETIME + JSON BACKUP
    # =========================================================
    @router.put("/word/{draft_survey_id}")
    def update_word(draft_survey_id: int, payload: dict, conn=Depends(get_db)):

        cur = conn.cursor()

        try:
            payload = payload or {}

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

            real_id = row[0]

            # =====================================================
            # 2) COLUMNAS REALES
            # =====================================================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'draft_survey_word_report'
            """)
            cols = {r[0] for r in cur.fetchall()}

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
            def clean_value(v):
                if v is None:
                    return None
                if isinstance(v, str) and v == "":
                    return None
                return v  # 🔥 NO tocar texto

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
            # CAMPOS CONTROLADOS (IGUAL QUE POST)
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
            # 🔥 4) LIMPIAR + ARMAR PAYLOAD
            # =====================================================
            clean_payload = {}
            ignored_keys = []

            # normales
            for f in expected_fields + metadata_fields:
                if f in cols:
                    clean_payload[f] = clean_value(payload.get(f))

            # datetime inteligente
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

            # FK
            clean_payload["draft_survey_id"] = real_id

            # STATUS
            if "status" in cols:
                clean_payload["status"] = payload.get("status") or "Pending for review"

            # =====================================================
            # 🔥 5) JSON BACKUP (CRÍTICO)
            # =====================================================
            if "raw_payload" in cols:
                clean_payload["raw_payload"] = payload

            if "word_json" in cols:
                clean_payload["word_json"] = payload

            # =====================================================
            # 🔧 6) UPDATE DINÁMICO
            # =====================================================
            fields = list(clean_payload.keys())

            if not fields:
                raise HTTPException(400, "No hay campos para actualizar")

            set_clause = ", ".join([f"{f} = %s" for f in fields])
            values = [clean_payload[f] for f in fields] + [real_id]

            # =====================================================
            # DEBUG
            # =====================================================
            print("====== PUT WORD DEBUG ======")
            print("REAL ID:", real_id)
            print("FIELDS:", fields)
            print("IGNORADOS:", ignored_keys)
            print("============================")

            cur.execute(f"""
                UPDATE draft_survey_word_report
                SET {set_clause},
                    updated_at = NOW()
                WHERE draft_survey_id = %s
                RETURNING id
            """, values)

            updated = cur.fetchone()

            if not updated:
                raise HTTPException(404, "No existe registro word para actualizar")

            conn.commit()

            return {
                "success": True,
                "action": "updated",
                "draft_survey_id": real_id,
                "saved_fields": len(fields)
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

