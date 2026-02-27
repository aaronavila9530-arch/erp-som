from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

router = APIRouter(
    prefix="/vessel-bunker-reports",
    tags=["Vessel Bunker Reports"]
)


class VesselBunkerReportRouter:

    MAX_TANKS = 20
    MAX_BUNKER_FIGURES = 10

    # =========================================================
    # HELPERS
    # =========================================================
    @staticmethod
    def _clean_value(v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s != "" else None
        return v

    @staticmethod
    def _normalize_date_for_db(value: str):
        """
        Acepta:
        - YYYY-MM-DD
        - 'February 27, 2026'
        Retorna YYYY-MM-DD o None/valor original si no parsea.
        """
        if not value:
            return None

        value = str(value).strip()
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%B %d, %Y"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        return value

    @staticmethod
    def _normalize_hhmm(value: str, max_value: int):
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        if not s.isdigit():
            return None
        n = int(s)
        if n < 0 or n > max_value:
            return None
        return f"{n:02d}"

    def _get_table_columns(self, cur):
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='vessel_bunker_reports'
        """)
        return {r["column_name"] for r in cur.fetchall()}

    def _ensure_full_slots(self, payload: dict):
        """
        FULL slots (tanques + bunker figures).
        Útil para CREATE y para PUT full.
        """
        for i in range(1, self.MAX_TANKS + 1):
            for prefix in ("vlsfo", "mgo"):
                payload.setdefault(f"{prefix}_tank_{i}_name", None)
                payload.setdefault(f"{prefix}_tank_{i}_dist_mtrs", None)
                payload.setdefault(f"{prefix}_tank_{i}_gauge_mtrs", None)
                payload.setdefault(f"{prefix}_tank_{i}_volume_m3", None)
                payload.setdefault(f"{prefix}_tank_{i}_temp_c", None)
                payload.setdefault(f"{prefix}_tank_{i}_temp_f", None)
                payload.setdefault(f"{prefix}_tank_{i}_density_15c", None)
                payload.setdefault(f"{prefix}_tank_{i}_weight_mt", None)

        for i in range(1, self.MAX_BUNKER_FIGURES + 1):
            payload.setdefault(f"bunker_figure_{i}_name", None)
            payload.setdefault(f"bunker_figure_{i}_ifo", None)
            payload.setdefault(f"bunker_figure_{i}_vlsfo", None)
            payload.setdefault(f"bunker_figure_{i}_lsmgo", None)

        return payload

    def _ensure_response_slots(self, row: dict) -> dict:
        """
        Asegura que el response tenga todas las keys esperadas por el frontend.
        """
        row = row or {}
        row = self._ensure_full_slots(row)

        # Campos auxiliares del frontend (si existen en DB, vendrán; si no, quedan None)
        row.setdefault("antecedent_arrived_dt", None)
        row.setdefault("antecedent_survey_date_from", None)
        row.setdefault("antecedent_survey_date_to", None)
        row.setdefault("inspection_with", None)
        row.setdefault("workflow_status", None)

        return row

    def _normalize_common(self, payload: dict):
        payload = payload or {}

        # limpiar strings vacíos
        payload = {k: self._clean_value(v) for k, v in payload.items()}

        # fechas UI->DB
        date_keys = [
            "report_date",
            "berthing_date",
            "commenced_date",
            "dslop_date",
            "antecedent_arrived_dt",
            "antecedent_survey_date_from",
            "antecedent_survey_date_to",
        ]
        for k in date_keys:
            if k in payload:
                payload[k] = self._normalize_date_for_db(payload.get(k))

        # HH/MM
        hhmm_limits = {
            "dslop_hour": 23, "dslop_minute": 59,
            "antecedent_survey_hour_from": 23, "antecedent_survey_minute_from": 59,
            "antecedent_survey_hour_to": 23, "antecedent_survey_minute_to": 59,
            "log_eosp_hour": 23, "log_eosp_minute": 59,
            "log_pob_hour": 23, "log_pob_minute": 59,
            "log_fwe_hour": 23, "log_fwe_minute": 59,
            "log_bunker_hour": 23, "log_bunker_minute": 59,
            "log_at_survey_hour": 23, "log_at_survey_minute": 59,
        }
        for k, mx in hhmm_limits.items():
            if k in payload:
                payload[k] = self._normalize_hhmm(payload.get(k), mx)

        return payload

    # =========================================================
    # CREATE
    # =========================================================
    def create(self, payload: dict, conn):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            payload = self._normalize_common(payload)

            payload.setdefault("status", "Pending")
            payload["created_at"] = datetime.utcnow()
            payload["updated_at"] = datetime.utcnow()

            payload = self._ensure_full_slots(payload)

            table_cols = self._get_table_columns(cur)
            filtered = {k: v for k, v in payload.items() if k in table_cols}

            if not filtered:
                raise HTTPException(status_code=422, detail="Empty or invalid payload (no valid columns).")

            columns = list(filtered.keys())
            values = [filtered[c] for c in columns]
            placeholders = ["%s"] * len(columns)

            query = f"""
                INSERT INTO vessel_bunker_reports
                ({", ".join(columns)})
                VALUES ({", ".join(placeholders)})
                RETURNING *
            """

            cur.execute(query, values)
            new_row = cur.fetchone()
            conn.commit()

            return {"success": True, "data": self._ensure_response_slots(dict(new_row))}

        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================
    # UPDATE (FULL PUT + BLINDADO)
    # =========================================================
    def update(self, report_id: int, payload: dict, conn):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute("SELECT status FROM vessel_bunker_reports WHERE id=%s", (report_id,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Report not found")

            if (row.get("status") or "") == "Approved":
                raise HTTPException(status_code=403, detail="Already approved")

            payload = self._normalize_common(payload)
            payload["updated_at"] = datetime.utcnow()

            # FULL slots (esto resetea a None lo que no venga)
            payload = self._ensure_full_slots(payload)

            table_cols = self._get_table_columns(cur)
            blocked_keys = {"id", "created_at"}
            filtered = {k: v for k, v in payload.items() if (k in table_cols and k not in blocked_keys)}

            if not filtered:
                raise HTTPException(status_code=422, detail="Empty or invalid payload (no valid columns).")

            set_clauses = []
            values = []

            for k in sorted(filtered.keys()):
                set_clauses.append(f"{k} = %s")
                values.append(filtered[k])

            values.append(report_id)

            query = f"""
                UPDATE vessel_bunker_reports
                SET {", ".join(set_clauses)}
                WHERE id = %s
                RETURNING *
            """

            cur.execute(query, values)
            updated = cur.fetchone()
            conn.commit()

            return {"success": True, "data": self._ensure_response_slots(dict(updated))}

        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================
    # GET BY ID
    # =========================================================
    def get_by_id(self, report_id: int, conn):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM vessel_bunker_reports WHERE id=%s", (report_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        return {"success": True, "data": self._ensure_response_slots(dict(row))}

    # =========================================================
    # GET ALL (PAGINADO + BUSQUEDA)
    # =========================================================
    def get_all(self, conn, limit: int = 200, offset: int = 0, q: str = None):

        cur = conn.cursor(cursor_factory=RealDictCursor)

        limit = max(1, min(int(limit or 200), 1000))
        offset = max(0, int(offset or 0))

        table_cols = self._get_table_columns(cur)

        where = []
        values = []

        if q:
            q = str(q).strip()
            if q:
                like = f"%{q}%"
                or_parts = []
                for col in ("bunker_cert_no", "ship_name", "client", "port", "country", "certificate", "report_category", "status"):
                    if col in table_cols:
                        or_parts.append(f"CAST({col} AS TEXT) ILIKE %s")
                        values.append(like)
                if or_parts:
                    where.append("(" + " OR ".join(or_parts) + ")")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        query = f"""
            SELECT *
            FROM vessel_bunker_reports
            {where_sql}
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT %s OFFSET %s
        """
        values.extend([limit, offset])

        cur.execute(query, values)
        rows = cur.fetchall() or []

        # listado: no rellenar slots (pesado). El detalle sí.
        return {"success": True, "data": rows, "limit": limit, "offset": offset, "count": len(rows)}


_bunker_router = VesselBunkerReportRouter()


@router.post("/")
def create_vessel_bunker_report(payload: dict, conn=Depends(get_db)):
    return _bunker_router.create(payload, conn)


@router.put("/{report_id}")
def update_vessel_bunker_report(report_id: int, payload: dict, conn=Depends(get_db)):
    return _bunker_router.update(report_id, payload, conn)


@router.get("/{report_id}")
def get_vessel_bunker_report(report_id: int, conn=Depends(get_db)):
    return _bunker_router.get_by_id(report_id, conn)


@router.get("/")
def get_all_vessel_bunker_reports(
    conn=Depends(get_db),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    q: str = Query(None)
):
    return _bunker_router.get_all(conn, limit=limit, offset=offset, q=q)