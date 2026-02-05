import os
import tempfile
from pypdf import PdfWriter, PdfReader


def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    """
    Une dos PDFs en uno solo (presentation + report)
    """

    if not presentation_pdf or not report_pdf:
        raise ValueError("PDF paths cannot be empty")

    if not os.path.exists(presentation_pdf):
        raise FileNotFoundError(f"Presentation PDF not found: {presentation_pdf}")

    if not os.path.exists(report_pdf):
        raise FileNotFoundError(f"Report PDF not found: {report_pdf}")

    writer = PdfWriter()

    for pdf_path in (presentation_pdf, report_pdf):
        try:
            reader = PdfReader(pdf_path)

            if not reader.pages:
                raise RuntimeError(f"PDF has no pages: {pdf_path}")

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(
                f"Error reading or merging PDF '{pdf_path}': {str(e)}"
            )

    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(f"Error writing merged PDF: {str(e)}")

    if not os.path.exists(output_path):
        raise RuntimeError("Merged PDF file was not created")

    return output_path
