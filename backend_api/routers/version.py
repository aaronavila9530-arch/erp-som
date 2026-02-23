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
        assets = data.get("assets", [])

        if isinstance(assets, list):
            for a in assets:
                name = str(a.get("name", "")).lower()
                if name.endswith(".exe"):
                    download_url = a.get("browser_download_url")
                    break

        return {
            "latest_version": latest_version,
            "download_url": download_url,
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
            "latest_version": None,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
