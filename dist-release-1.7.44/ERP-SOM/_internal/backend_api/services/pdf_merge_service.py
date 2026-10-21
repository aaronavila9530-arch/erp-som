import os as _os
import tempfile as _tempfile
import time as _time
import sys
from typing import List

print("\n==== pdf_merge_service LOADED ====")
print("FILE:", __file__)
print("_os module:", _os)
print("sys module:", sys)

from pypdf import PdfWriter, PdfReader


# =====================================================
# INTERNAL SAFE HELPERS
# =====================================================
def _validate_pdf_path(path: str) -> None:
    print("[M1] Validating PDF path:", path)

    if not path or not isinstance(path, str):
        raise ValueError("PDF path must be a non-empty string")

    print("[M2] _os exists?", _os)

    if not _os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    size = _os.path.getsize(path)
    print("[M3] File size:", size)

    if size == 0:
        raise RuntimeError(f"PDF file is empty: {path}")


def _wait_for_file(path: str, timeout_sec: int = 15) -> bool:
    print("[M4] Waiting for file:", path)

    start = _time.time()
    while _time.time() - start < timeout_sec:
        if _os.path.exists(path):
            try:
                if _os.path.getsize(path) > 0:
                    print("[M5] File ready:", path)
                    return True
            except Exception:
                pass
        _time.sleep(0.2)

    print("[M6] Timeout waiting for file:", path)
    return False


def _create_temp_pdf_path() -> str:
    tmp_dir = _tempfile.mkdtemp(prefix="merged_pdf_")
    path = _os.path.abspath(_os.path.join(tmp_dir, "merged_output.pdf"))
    print("[M7] Temp output path:", path)
    return path


# =====================================================
# MERGE TWO PDFs
# =====================================================
def merge_pdfs(presentation_pdf: str, report_pdf: str) -> str:
    print("\n[M8] merge_pdfs START")

    _validate_pdf_path(presentation_pdf)
    _validate_pdf_path(report_pdf)

    writer = PdfWriter()

    for pdf_path in (presentation_pdf, report_pdf):
        print("[M9] Reading:", pdf_path)

        try:
            reader = PdfReader(pdf_path)

            if not reader.pages or len(reader.pages) == 0:
                raise RuntimeError(f"PDF has no pages: {pdf_path}")

            print("[M10] Pages:", len(reader.pages))

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(
                f"Error reading or merging PDF '{pdf_path}': {e}"
            )

    output_path = _create_temp_pdf_path()

    print("[M11] Writing merged file...")

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(f"Error writing merged PDF: {e}")

    if not _wait_for_file(output_path):
        raise RuntimeError("Merged PDF file was not created properly")

    print("[M12] merge_pdfs SUCCESS:", output_path)
    return output_path


# =====================================================
# MERGE N PDFs
# =====================================================
def merge_pdf_list(pdf_paths: List[str]) -> str:
    print("\n[M13] merge_pdf_list START")
    print("[M14] Received paths:", pdf_paths)

    if not pdf_paths or not isinstance(pdf_paths, list):
        raise ValueError("pdf_paths must be a non-empty list")

    writer = PdfWriter()

    for p in pdf_paths:
        print("[M15] Processing:", p)

        _validate_pdf_path(p)

        try:
            reader = PdfReader(p)

            if not reader.pages or len(reader.pages) == 0:
                raise RuntimeError(f"PDF has no pages: {p}")

            print("[M16] Pages:", len(reader.pages))

            for page in reader.pages:
                writer.add_page(page)

        except Exception as e:
            raise RuntimeError(f"Error merging PDF '{p}': {e}")

    output_path = _create_temp_pdf_path()

    print("[M17] Writing merged PDF...")

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise RuntimeError(f"Error writing merged PDF: {e}")

    print("[M18] Checking file existence with _os:", _os)
    print("[M19] Exists?:", _os.path.exists(output_path))

    if not _wait_for_file(output_path):
        raise RuntimeError("Merged PDF was not created properly")

    print("[M20] merge_pdf_list SUCCESS:", output_path)
    return output_path