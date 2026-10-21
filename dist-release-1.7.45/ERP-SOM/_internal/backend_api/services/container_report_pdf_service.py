import os
import subprocess
import tempfile
from pathlib import Path

from services.container_report_excel_service import generate_container_report_excel


def generate_container_report_pdf(report: dict) -> str:
    """
    Genera PDF REAL desde Excel usando LibreOffice (Docker-safe)
    """

    # 1) Generar Excel
    excel_path = generate_container_report_excel(report)

    if not os.path.exists(excel_path):
        raise RuntimeError("Excel file was not generated")

    # 2) Directorio temporal
    output_dir = tempfile.mkdtemp(prefix="container_pdf_")

    # 3) Usar soffice (NO libreoffice)
    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nolockcheck",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        excel_path
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
    pdf_name = Path(excel_path).with_suffix(".pdf").name
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    return pdf_path
