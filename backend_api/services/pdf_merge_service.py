import os
import tempfile
from pypdf import PdfWriter, PdfReader


# =====================================================
# MERGE PDFs (Presentation + Report)
# =====================================================
def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    """
    Une dos PDFs en uno solo:
    1) Presentation
    2) Container Report
    """

    # -------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------
    if not presentation_pdf or not report_pdf:
        raise ValueError("PDF paths cannot be empty")

    if not isinstance(presentation_pdf, str) or not isinstance(report_pdf, str):
        raise ValueError("PDF paths must be strings")

    if not os.path.exists(presentation_pdf):
        raise FileNotFoundError(
            f"Presentation PDF not found: {presentation_pdf}"
        )

    if not os.path.exists(report_pdf):
        raise FileNotFoundError(
            f"Report PDF not found: {report_pdf}"
        )

    writer = PdfWriter()

    # -------------------------------------------------
    # READ + APPEND PAGES
    # -------------------------------------------------
    for pdf_path in (presentation_pdf, report_pdf):
        try:
            reader = PdfReader(pdf_path)

            if not reader.pages or len(reader.pages) == 0:
                raise RuntimeError(
                    f"PDF has no pages: {pdf_path}"
                )

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(
                f"Error reading or merging PDF '{pdf_path}': {str(e)}"
            )

    # -------------------------------------------------
    # WRITE OUTPUT
    # -------------------------------------------------
    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(
            f"Error writing merged PDF: {str(e)}"
        )

    # -------------------------------------------------
    # FINAL VALIDATION
    # -------------------------------------------------
    if not os.path.exists(output_path):
        raise RuntimeError(
            "Merged PDF file was not created"
        )

    return output_path



def merge_pdf_list(pdf_paths: list) -> str:
    """
    Une N PDFs en uno solo, en orden.
    """
    if not pdf_paths or not isinstance(pdf_paths, list):
        raise ValueError("pdf_paths must be a non-empty list")

    writer = PdfWriter()

    for p in pdf_paths:
        if not isinstance(p, str) or not p:
            raise ValueError("Each PDF path must be a non-empty string")
        if not os.path.exists(p):
            raise FileNotFoundError(f"PDF not found: {p}")

        reader = PdfReader(p)
        if not reader.pages:
            raise RuntimeError(f"PDF has no pages: {p}")

        for page in reader.pages:
            writer.add_page(page)

    fd, out_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    with open(out_path, "wb") as f:
        writer.write(f)

    if not os.path.exists(out_path):
        raise RuntimeError("Merged PDF was not created")

    return out_path