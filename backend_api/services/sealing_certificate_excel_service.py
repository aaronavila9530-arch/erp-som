# =========================================================
# GENERATE EXCEL
# =========================================================

@router.get("/{record_id}/excel")
def generate_sampling_excel(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT *
                FROM sampling_certificates
                WHERE id=%s

            """, (record_id,))

            row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_excel(row)

        return FileResponse(
            path=file_path,
            filename=f"sampling_certificate_{record_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GENERATE PDF
# =========================================================

@router.get("/{record_id}/pdf")
def generate_sampling_pdf(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT *
                FROM sampling_certificates
                WHERE id=%s

            """, (record_id,))

            row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_pdf(row)

        return FileResponse(
            path=file_path,
            filename=f"sampling_certificate_{record_id}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )