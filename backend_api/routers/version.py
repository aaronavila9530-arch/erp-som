from fastapi import APIRouter, HTTPException
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
    if not token:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN not configured in environment"
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ERP-SOM-Updater",
        "Authorization": f"Bearer {token}"
    }

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # ----------------------------------------------------
        # 1️⃣ Versión latest desde GitHub
        # ----------------------------------------------------
        tag = data.get("tag_name")
        if not tag:
            raise HTTPException(
                status_code=500,
                detail="Invalid GitHub release: missing tag_name"
            )

        latest_version = tag.lstrip("v").strip()

        # ----------------------------------------------------
        # 2️⃣ Buscar instalador EXE
        # ----------------------------------------------------
        assets = data.get("assets", [])
        installer = next(
            (a for a in assets if a.get("name", "").lower().endswith(".exe")),
            None
        )

        if not installer:
            raise HTTPException(
                status_code=500,
                detail="Release found but no installer (.exe) attached"
            )

        download_url = installer.get("browser_download_url")
        if not download_url:
            raise HTTPException(
                status_code=500,
                detail="Installer asset missing download URL"
            )

        # ----------------------------------------------------
        # 3️⃣ Comparación ESTRICTA (forzar update)
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

    except HTTPException:
        raise

    except Exception as e:
        # 🔴 SI FALLA GITHUB → NO SE ACTUALIZA, PERO SE REPORTA
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": f"Updater failure: {str(e)}"
        }
