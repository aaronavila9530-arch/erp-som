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

    # 🔒 Repo privado → token requerido
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        # ----------------------------------------------------
        # 1️⃣ OBTENER RELEASE LATEST
        # ----------------------------------------------------
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # ----------------------------------------------------
        # 2️⃣ VERSION DESDE TAG (SIN NORMALIZAR)
        # ----------------------------------------------------
        tag = data.get("tag_name")
        if not tag:
            raise RuntimeError("Invalid GitHub release: missing tag_name")

        latest_version = tag.lstrip("v")

        # ----------------------------------------------------
        # 3️⃣ BUSCAR ASSET .EXE
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
                "download_asset_id": None,
                "force_update": False,
                "message": "Release found but no installer attached"
            }

        asset_id = installer.get("id")
        if not asset_id:
            return {
                "current_version": CURRENT_VERSION,
                "latest_version": latest_version,
                "download_asset_id": None,
                "force_update": False,
                "message": "Installer asset missing ID"
            }

        # ----------------------------------------------------
        # 4️⃣ COMPARACIÓN ESTRICTA
        # ----------------------------------------------------
        force_update = latest_version != CURRENT_VERSION

        return {
            "current_version": CURRENT_VERSION,
            "latest_version": latest_version,
            "download_asset_id": asset_id,
            "force_update": force_update,
            "message": (
                "UPDATE REQUIRED"
                if force_update
                else "Application up to date"
            )
        }

    except Exception as e:
        # ----------------------------------------------------
        # FAIL SAFE — JAMÁS ROMPER EL ERP
        # ----------------------------------------------------
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "download_asset_id": None,
            "force_update": False,
            "message": f"Updater failure: {str(e)}"
        }
