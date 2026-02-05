from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from services.presentation_doc_service import generate_presentation_pdf
from services.pdf_merge_service import merge_pdfs
from routers.container_presentation import get_container_presentation_data
from routers.container_reports import download_container_report_pdf


router = APIRouter(
    prefix="/container-presentation-pdf",
    tags=["Container Presentation PDF"]
)


@router.get("/{container_report_id}/presentation")
def generate_presentation_only(
    container_report_id: int,
    conn=Depends(get_db)
):
    data = get_container_presentation_data(container_report_id, conn)
    pdf_path = generate_presentation_pdf(data)

    return FileResponse(
        pdf_path,
        filename="presentation.pdf",
        media_type="application/pdf"
    )


@router.get("/{container_report_id}/unified")
def generate_unified_pdf(
    container_report_id: int,
    conn=Depends(get_db)
):
    data = get_container_presentation_data(container_report_id, conn)
    presentation_pdf = generate_presentation_pdf(data)

    report_pdf = download_container_report_pdf(container_report_id)

    unified_pdf = merge_pdfs(presentation_pdf, report_pdf)

    return FileResponse(
        unified_pdf,
        filename="container_report_unified.pdf",
        media_type="application/pdf"
    )
