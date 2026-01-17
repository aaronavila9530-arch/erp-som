from fastapi import APIRouter
import requests

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

GITHUB_API = "https://api.github.com/repos/aaronavila9530-arch/erp-som/releases/latest"
CURRENT_VERSION = "1.0.1"


@router.get("/")
def check_version():
    """
    Control de versión ERP-SOM.
    Reglas:
    - Si GitHub responde y hay versión mayor → update forzado
    - Si falta el EXE → bloquear update
    - Si GitHub falla → fallback seguro (no romper ERP)
    """

    try:
        r = requests.get(GITHUB_API, timeout=6)
        r.raise_for_status()
        data = r.json()

        latest_version = data.get("tag_name", "").lstrip("v")

        # Buscar instalador
        asset = next(
            (
                a for a in data.get("assets", [])
                if a.get("name", "").lower().endswith(".exe")
            ),
            None
        )

        # Si GitHub respondió pero no hay versión válida
        if not latest_version:
            return {
                "latest_version": CURRENT_VERSION,
                "download_url": None,
                "force_update": False,
                "message": ""
            }

        # Si hay versión nueva pero NO hay EXE → bloquear
        if latest_version != CURRENT_VERSION and not asset:
            return {
                "latest_version": latest_version,
                "download_url": None,
                "force_update": True,
                "message": (
                    "Hay una nueva versión del ERP, pero no se encontró el instalador.\n"
                    "Contacte al administrador del sistema."
                )
            }

        # Flujo normal
        return {
            "latest_version": latest_version,
            "download_url": asset.get("browser_download_url") if asset else None,
            "force_update": latest_version != CURRENT_VERSION,
            "message": data.get("body", "") or "Hay una nueva versión disponible."
        }

    except Exception:
        # 🔒 Fallback ABSOLUTO
        # No sabemos si hay update → NO forzar
        return {
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
