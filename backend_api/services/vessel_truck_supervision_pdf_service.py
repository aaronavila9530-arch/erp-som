import os
import subprocess
import tempfile
from pathlib import Path

from services.vessel_truck_supervision_doc_service import generate_vessel_truck_supervision_doc


def generate_vessel_truck_supervision_pdf(report: dict) -> str:

    # 1️⃣ Generar Word
    word_path = generate_vessel_truck_supervision_doc(report)

    if not os.path.exists(word_path):
        raise RuntimeError("Word file was not generated")

    # 2️⃣ Directorios temporales
    output_dir = tempfile.mkdtemp(prefix="truck_supervision_pdf_")
    libre_profile = tempfile.mkdtemp(prefix="lo_profile_")

    # 3️⃣ LibreOffice headless (igual que grain sampling)
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
        raise RuntimeError(f"LibreOffice PDF conversion failed:\n{result.stderr}")

    pdf_name = Path(word_path).with_suffix(".pdf").name
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    return pdf_path
