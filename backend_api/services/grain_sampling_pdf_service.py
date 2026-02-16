import os
import subprocess
import tempfile
from pathlib import Path

from services.grain_sampling_doc_service import generate_grain_sampling_doc


# ============================================================
# GENERATE GRAIN SAMPLING PDF (REAL PDF VIA LIBREOFFICE)
# ============================================================

def generate_grain_sampling_pdf(report: dict) -> str:
    """
    Genera PDF real desde Word usando LibreOffice (Docker-safe)
    """

    # 1) Generar Word
    word_path = generate_grain_sampling_doc(report)

    if not os.path.exists(word_path):
        raise RuntimeError("Word file was not generated")

    # 2) Directorio temporal
    output_dir = tempfile.mkdtemp(prefix="grain_sampling_pdf_")

    # 3) Comando LibreOffice (igual patrón que containers)
    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nolockcheck",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        word_path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice PDF conversion failed:\n{result.stderr}"
        )

    # 4) PDF generado
    pdf_name = Path(word_path).with_suffix(".pdf").name
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    return pdf_path
