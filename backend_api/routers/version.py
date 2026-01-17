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
    GitHub API REQUIERE User-Agent.
    """

    headers = {
        "User-Agent": "ERP-SOM-Updater/1.0",
        "Accept": "application/vnd.github+json"
    }

    try:
        r = requests.get(GITHUB_API, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()

        latest_version = data.get("tag_name", "").lstrip("v")

        asset = next(
            (
                a for a in data.get("assets", [])
                if a.get("name", "").lower().endswith(".exe")
            ),
            None
        )

        # Si hay versión nueva pero no EXE → bloquear
        if latest_version and latest_version != CURRENT_VERSION and not asset:
            return {
                "latest_version": latest_version,
                "download_url": None,
                "force_update": True,
                "message": (
                    "Hay una nueva versión del ERP, pero no se encontró el instalador.\n"
                    "Contacte al administrador del sistema."
                )
            }

        return {
            "latest_version": latest_version or CURRENT_VERSION,
            "download_url": asset.get("browser_download_url") if asset else None,
            "force_update": bool(latest_version and latest_version != CURRENT_VERSION),
            "message": data.get("body", "") or "Hay una nueva versión disponible."
        }

    except Exception as e:
        # ⚠️ Si entra aquí, GitHub NO respondió correctamente
        return {
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": f"Updater fallback: {str(e)}"
        }
