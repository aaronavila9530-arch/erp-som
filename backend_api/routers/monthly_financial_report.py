from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from database import get_db
from reports.monthly_financial_report import (
    build_monthly_financial_data,
    build_monthly_obligation_preview,
    generate_monthly_financial_docx,
    generate_monthly_financial_pdf,
    save_monthly_obligations,
)


router = APIRouter(
    prefix="/monthly-financial-report",
    tags=["Monthly Financial Report"]
)


@router.get("/summary")
def monthly_financial_report_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    conn=Depends(get_db)
):
    return build_monthly_financial_data(conn, year, month)


@router.get("/obligations-preview")
def monthly_financial_report_obligations_preview(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    conn=Depends(get_db)
):
    return build_monthly_obligation_preview(conn, year, month)


@router.post("/obligations-preview")
def monthly_financial_report_obligations_save(
    payload: dict,
    conn=Depends(get_db)
):
    year = int(payload.get("year"))
    month = int(payload.get("month"))
    return save_monthly_obligations(
        conn,
        year,
        month,
        payload.get("rows") or [],
        payload.get("user"),
    )


@router.get("/pdf")
def monthly_financial_report_pdf(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    conn=Depends(get_db)
):
    path, filename = generate_monthly_financial_pdf(conn, year, month)
    return FileResponse(path, filename=filename, media_type="application/pdf")


@router.get("/word")
def monthly_financial_report_word(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    conn=Depends(get_db)
):
    path, filename = generate_monthly_financial_docx(conn, year, month)
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
