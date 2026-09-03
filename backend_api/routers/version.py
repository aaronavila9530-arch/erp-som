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
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
FALLBACK_VERSION = "1.7.23"
FALLBACK_ASSET_NAME = f"ERP-SOM-Setup-{FALLBACK_VERSION}.exe"
FALLBACK_DOWNLOAD_URL = (
    f"https://github.com/{GITHUB_REPO}/releases/download/"
    f"v{FALLBACK_VERSION}/{FALLBACK_ASSET_NAME}"
)


def _find_installer_asset(assets, latest_version: str):
    if not isinstance(assets, list):
        return None

    version = str(latest_version or "").strip()
    exact_names = {
        f"erp-som-setup-{version}.exe",
        f"erp-som-setup-v{version}.exe",
    }

    for asset in assets:
        name = str(asset.get("name", "")).strip().lower()
        if name in exact_names:
            return asset

    for asset in assets:
        name = str(asset.get("name", "")).strip().lower()
        if name.endswith(".exe") and name.startswith("erp-som-setup-") and version.lower() in name:
            return asset

    for asset in assets:
        name = str(asset.get("name", "")).strip().lower()
        if name == "erp-som-setup.exe":
            return asset

    return None

# ============================================================
# VERSION CHECK (BACKEND NEUTRO, BLINDADO, AISLADO)
# ============================================================
@router.get("/")
def check_version():
    """
    🔒 ENDPOINT DE VERSIONES — BACKEND AISLADO

    • NO importa db
    • NO importa settings
    • NO compara versiones
    • NO conoce versión instalada
    • SOLO refleja GitHub
    • JAMÁS rompe el backend
    """

    try:
        r = requests.get(
            GITHUB_API_URL,
            timeout=8,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ERP-SOM-Version-Endpoint"
            }
        )
        r.raise_for_status()
        data = r.json()

        # ------------------------------
        # Extraer versión
        # ------------------------------
        tag = data.get("tag_name")
        if not isinstance(tag, str):
            raise ValueError("tag_name inválido")

        latest_version = tag.lstrip("v").strip()
        if not latest_version:
            raise ValueError("versión vacía")

        # ------------------------------
        # Buscar instalador .exe
        # ------------------------------
        download_url = None
        asset_name = None
        assets = data.get("assets", [])

        installer_asset = _find_installer_asset(assets, latest_version)
        if installer_asset:
            asset_name = installer_asset.get("name")
            download_url = installer_asset.get("browser_download_url")

        return {
            "latest_version": latest_version,
            "download_url": download_url,
            "asset_name": asset_name,
            # 👇 EL BACKEND SIEMPRE OBLIGA UPDATE
            # El frontend decide si aplica o no
            "force_update": False,
            "message": f"Nueva versión {latest_version} disponible del ERP-SOM."
        }

    except Exception:
        # ----------------------------------------------------
        # FAIL SAFE ABSOLUTO
        # ----------------------------------------------------
        # • GitHub caído
        # • Sin internet
        # • Rate limit
        # • JSON inválido
        #
        # 👉 JAMÁS BLOQUEAR EL BACKEND
        # 👉 JAMÁS LANZAR EXCEPCIÓN
        # ----------------------------------------------------
        return {
            "latest_version": FALLBACK_VERSION,
            "download_url": FALLBACK_DOWNLOAD_URL,
            "asset_name": FALLBACK_ASSET_NAME,
            "force_update": False,
            "message": f"Nueva versión {FALLBACK_VERSION} disponible del ERP-SOM."
        }
