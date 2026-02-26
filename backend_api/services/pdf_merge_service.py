import os as _os
import tempfile as _tempfile
import time as _time
from typing import List

from pypdf import PdfWriter, PdfReader


# =====================================================
# INTERNAL SAFE HELPERS
# =====================================================
def _validate_pdf_path(path: str) -> None:
    if not path or not isinstance(path, str):
        raise ValueError("PDF path must be a non-empty string")

    if not _os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    if _os.path.getsize(path) == 0:
        raise RuntimeError(f"PDF file is empty: {path}")


def _wait_for_file(path: str, timeout_sec: int = 15) -> bool:
    start = _time.time()
    while _time.time() - start < timeout_sec:
        if _os.path.exists(path):
            try:
                if _os.path.getsize(path) > 0:
                    return True
            except Exception:
                pass
        _time.sleep(0.2)
    return False


def _create_temp_pdf_path() -> str:
    tmp_dir = _tempfile.mkdtemp(prefix="merged_pdf_")
    return _os.path.abspath(_os.path.join(tmp_dir, "merged_output.pdf"))


# =====================================================
# MERGE TWO PDFs
# =====================================================
def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    """
    Une exactamente dos PDFs en orden:
    1) Presentation
    2) Report
    """

    _validate_pdf_path(presentation_pdf)
    _validate_pdf_path(report_pdf)

    writer = PdfWriter()

    for pdf_path in (presentation_pdf, report_pdf):
        try:
            reader = PdfReader(pdf_path)

            if not reader.pages or len(reader.pages) == 0:
                raise RuntimeError(f"PDF has no pages: {pdf_path}")

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(
                f"Error reading or merging PDF '{pdf_path}': {e}"
            )

    output_path = _create_temp_pdf_path()

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(f"Error writing merged PDF: {e}")

    if not _wait_for_file(output_path):
        raise RuntimeError("Merged PDF file was not created properly")

    return output_path


# =====================================================
# MERGE N PDFs (ORDER PRESERVED)
# =====================================================
def merge_pdf_list(pdf_paths: List[str]) -> str:
    """
    Une N PDFs en uno solo respetando el orden.
    """

    if not pdf_paths or not isinstance(pdf_paths, list):
        raise ValueError("pdf_paths must be a non-empty list")

    writer = PdfWriter()

    for p in pdf_paths:
        _validate_pdf_path(p)

        try:
            reader = PdfReader(p)

            if not reader.pages or len(reader.pages) == 0:
                raise RuntimeError(f"PDF has no pages: {p}")

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(f"Error merging PDF '{p}': {e}")

    output_path = _create_temp_pdf_path()

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(f"Error writing merged PDF: {e}")

    if not _wait_for_file(output_path):
        raise RuntimeError("Merged PDF was not created properly")

    return output_path