from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from database import get_db
from reports.monthly_financial_report import (
    build_monthly_financial_data,
    generate_monthly_financial_docx,
    generate_monthly_financial_pdf,
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
