from pypdf import PdfWriter, PdfReader
import tempfile
import os


def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    writer = PdfWriter()

    for pdf_path in (presentation_pdf, report_pdf):
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
