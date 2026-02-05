from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from database import get_db


router = APIRouter(
    prefix="/container-presentation",
    tags=["Container Presentation"]
)


@router.get("/{container_report_id}")
def get_container_presentation_data(
    container_report_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # =====================================================
        # 1️⃣ OBTENER DATOS BASE DESDE container_reports
        # =====================================================
        cur.execute("""
            SELECT
                id,
                linked_report_number,
                report_no,
                inspection_place,
                init_inspection_datetime
            FROM container_reports
            WHERE id = %s
        """, (container_report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Container report not found"
            )

        linked_report_number = report["linked_report_number"]

        # =====================================================
        # 2️⃣ OBTENER CLIENTE DESDE servicios
        # =====================================================
        cliente = None

        if linked_report_number:
            cur.execute("""
                SELECT cliente
                FROM servicios
                WHERE num_informe = %s
                LIMIT 1
            """, (linked_report_number,))

            row = cur.fetchone()
            if row:
                cliente = row["cliente"]

        # =====================================================
        # 3️⃣ FORMATEAR FECHA A DD-MM-YYYY
        # =====================================================
        formatted_date = None
        if report["init_inspection_datetime"]:
            formatted_date = report["init_inspection_datetime"].strftime("%d-%m-%Y")

        # =====================================================
        # 4️⃣ RESPUESTA FINAL PARA POPUP
        # =====================================================
        return {
            "cert_no": linked_report_number,
            "container": report["report_no"],
            "to": cliente,
            "place": report["inspection_place"],
            "date": formatted_date
        }

    finally:
        cur.close()
