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
CURRENT_VERSION = "1.0.1"

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


# ============================================================
# CHECK DE VERSIÓN (AUTOMÁTICO + FORZADO)
# ============================================================
@router.get("/")
def check_version():
    """
    Endpoint de control de versión para ERP-SOM Desktop.

    REGLAS:
    - Siempre consulta GitHub Releases (latest)
    - Si hay versión mayor → UPDATE OBLIGATORIO
    - Devuelve estructura EXACTA que espera el cliente
    - Si algo falla → NO rompe el ERP
    """

    try:
        r = requests.get(GITHUB_API, timeout=5)
        r.raise_for_status()
        data = r.json()

        # ----------------------------
        # 1️⃣ Versión latest (sin 'v')
        # ----------------------------
        latest_version = data.get("tag_name", "").lstrip("v")

        if not latest_version:
            raise Exception("Release sin tag_name")

        # ----------------------------
        # 2️⃣ Buscar instalador .exe
        # ----------------------------
        asset = next(
            (
                a for a in data.get("assets", [])
                if a.get("name", "").lower().endswith(".exe")
            ),
            None
        )

        download_url = asset.get("browser_download_url") if asset else None

        # ----------------------------
        # 3️⃣ Mensaje (release notes)
        # ----------------------------
        message = data.get("body", "").strip()

        # ----------------------------
        # 4️⃣ FORZAR UPDATE SI VERSION CAMBIÓ
        # ----------------------------
        force_update = latest_version != CURRENT_VERSION

        return {
            # 🔑 CLAVES QUE ESPERA EL DESKTOP
            "latest_version": latest_version,
            "download_url": download_url,
            "force_update": force_update,
            "message": message or "Hay una nueva versión disponible del sistema."
        }

    except Exception as e:
        # ----------------------------------------------------
        # FALLBACK SEGURO
        # - Nunca rompe el ERP
        # - No dispara update fantasma
        # ----------------------------------------------------
        return {
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
