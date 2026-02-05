from pypdf import PdfMerger
import tempfile
import os


def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    merger = PdfMerger()

    merger.append(presentation_pdf)
    merger.append(report_pdf)

    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    merger.write(output_path)
    merger.close()

    return output_path
