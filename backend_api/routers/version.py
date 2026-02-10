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
GITHUB_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
)

# ============================================================
# VERSION CHECK (BACKEND NEUTRO Y BLINDADO)
# ============================================================
@router.get("/")
def check_version():
    """
    🔒 ENDPOINT DE VERSIONES — BACKEND NEUTRO Y SEGURO

    • El backend NO conoce la versión instalada
    • El backend NO compara versiones
    • El backend SOLO refleja GitHub Releases
    • El frontend decide si actualizar o no
    """

    try:
        response = requests.get(
            GITHUB_API_URL,
            timeout=10,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ERP-SOM-Version-Checker"
            }
        )
        response.raise_for_status()
        data = response.json()

        # ----------------------------------------------------
        # OBTENER TAG DE VERSIÓN
        # ----------------------------------------------------
        tag = (data.get("tag_name") or "").strip()

        if not tag:
            raise ValueError("Release sin tag_name")

        # Normalizar: v1.0.6 → 1.0.6
        latest_version = tag.lstrip("v").strip()

        if not latest_version:
            raise ValueError("Versión inválida en tag_name")

        # ----------------------------------------------------
        # BUSCAR INSTALLER .exe
        # ----------------------------------------------------
        installer_url = None
        for asset in data.get("assets", []):
            name = (asset.get("name") or "").lower()
            if name.endswith(".exe"):
                installer_url = asset.get("browser_download_url")
                break

        return {
            "latest_version": latest_version,
            "download_url": installer_url,
            "force_update": True,
            "message": f"Nueva versión {latest_version} disponible del ERP-SOM."
        }

    except Exception:
        # ====================================================
        # FAIL SAFE ABSOLUTO
        # ====================================================
        # • GitHub caído
        # • Sin internet
        # • Rate limit
        # • JSON inválido
        #
        # 👉 JAMÁS BLOQUEAR EL ERP
        # ====================================================
        return {
            "latest_version": None,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
