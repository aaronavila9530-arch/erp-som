import os
import subprocess
import tempfile
from pathlib import Path

from services.grain_sampling_doc_service import generate_grain_sampling_doc


# ============================================================
# GENERATE GRAIN SAMPLING PDF (LAYOUT PRESERVATION MODE)
# ============================================================

def generate_grain_sampling_pdf(report: dict) -> str:
    """
    Genera PDF real desde Word usando LibreOffice
    Preserva layout, márgenes y posicionamiento
    """

    # ========================================================
    # 1) GENERAR WORD DESDE TEMPLATE
    # ========================================================

    word_path = generate_grain_sampling_doc(report)

    if not os.path.exists(word_path):
        raise RuntimeError("Word file was not generated")

    # ========================================================
    # 2) DIRECTORIO TEMPORAL AISLADO
    # ========================================================

    output_dir = tempfile.mkdtemp(prefix="grain_sampling_pdf_")
    libre_profile = tempfile.mkdtemp(prefix="lo_profile_")

    # ========================================================
    # 3) COMANDO LIBREOFFICE ULTRA CONTROLADO
    # ========================================================

    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--norestore",
        f"-env:UserInstallation=file://{libre_profile}",
        "--convert-to",
        "pdf:writer_pdf_Export",
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

    # ========================================================
    # 4) VALIDAR PDF GENERADO
    # ========================================================

    pdf_name = Path(word_path).with_suffix(".pdf").name
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    if os.path.getsize(pdf_path) == 0:
        raise RuntimeError("PDF was generated but is empty")

    return pdf_path
