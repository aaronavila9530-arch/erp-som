from fastapi import APIRouter
import requests

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

# ============================================================
# CONFIGURACIÓN
# ============================================================
GITHUB_REPO = "aaronavila9530-arch/erp-som"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


# ============================================================
# CHECK DE VERSIÓN (SOLO INFORMA)
# ============================================================
@router.get("/")
def check_version():
    """
    Endpoint de control de versión para ERP-SOM Desktop.

    RESPONSABILIDAD DEL BACKEND:
    - Consultar GitHub Releases
    - Informar última versión disponible
    - Entregar URL del instalador
    - NUNCA decidir si el cliente debe actualizar
    """

    try:
        r = requests.get(GITHUB_API, timeout=5)
        r.raise_for_status()
        data = r.json()

        # 1️⃣ Versión latest
        latest_version = data.get("tag_name", "").lstrip("v")
        if not latest_version:
            raise Exception("Release sin tag_name")

        # 2️⃣ Buscar instalador .exe
        asset = next(
            (
                a for a in data.get("assets", [])
                if a.get("name", "").lower().endswith(".exe")
            ),
            None
        )

        download_url = asset.get("browser_download_url") if asset else None

        # 3️⃣ Mensaje
        message = data.get("body", "").strip()

        return {
            "latest_version": latest_version,
            "download_url": download_url,
            "force_update": False,  # 🔑 lo decide el CLIENTE
            "message": message or "Hay una nueva versión disponible del sistema."
        }

    except Exception:
        return {
            "latest_version": None,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
