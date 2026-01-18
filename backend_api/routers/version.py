from fastapi import APIRouter
import requests
import os

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

# ============================================================
# CONFIGURACIÓN
# ============================================================
GITHUB_REPO = "aaronavila9530-arch/erp-som"
CURRENT_VERSION = "1.0.1"


# ============================================================
# CHECK VERSION / FORCE UPDATE
# ============================================================
@router.get("/")
def check_version():

    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ERP-SOM-Updater"
    }

    # 🔒 Token es OPCIONAL (repos públicos)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # ----------------------------------------------------
        # 1️⃣ Versión latest EXACTA desde GitHub
        # ----------------------------------------------------
        tag = data.get("tag_name")
        if not tag:
            raise RuntimeError("Invalid GitHub release: missing tag_name")

        # ⚠️ NO normalizar, NO convertir, NO formatear
        latest_version = tag.lstrip("v")

        # ----------------------------------------------------
        # 2️⃣ Buscar instalador EXE
        # ----------------------------------------------------
        assets = data.get("assets", [])
        installer = next(
            (a for a in assets if a.get("name", "").lower().endswith(".exe")),
            None
        )

        if not installer:
            return {
                "current_version": CURRENT_VERSION,
                "latest_version": latest_version,
                "download_url": None,
                "force_update": False,
                "message": "Release found but no installer attached"
            }

        download_url = installer.get("browser_download_url")

        if not download_url:
            return {
                "current_version": CURRENT_VERSION,
                "latest_version": latest_version,
                "download_url": None,
                "force_update": False,
                "message": "Installer asset missing download URL"
            }

        # ----------------------------------------------------
        # 3️⃣ Comparación estricta → update obligatorio
        # ----------------------------------------------------
        force_update = latest_version != CURRENT_VERSION

        return {
            "current_version": CURRENT_VERSION,
            "latest_version": latest_version,
            "download_url": download_url,
            "force_update": force_update,
            "message": (
                "UPDATE REQUIRED"
                if force_update
                else "Application up to date"
            )
        }

    except Exception as e:
        # 🔒 FAIL SAFE: nunca romper el ERP
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": f"Updater failure: {str(e)}"
        }