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
    🔒 ENDPOINT DE VERSIONES — BACKEND NEUTRO

    • El backend NO conoce su versión
    • El backend NO compara versiones
    • El backend SOLO refleja GitHub
    • El frontend decide qué hacer
    """

    try:
        r = requests.get(
            GITHUB_API_URL,
            timeout=15,
            headers={
                "Accept": "application/vnd.github+json"
            }
        )
        r.raise_for_status()
        data = r.json()

        # --------------------------------------------
        # VERSION DESDE GITHUB (tag_name)
        # --------------------------------------------
        tag = (data.get("tag_name") or "").strip()
        latest_version = tag.lstrip("v")

        if not latest_version:
            raise ValueError("GitHub release sin tag_name")

        # --------------------------------------------
        # BUSCAR INSTALLER .exe
        # --------------------------------------------
        assets = data.get("assets", [])
        installer = next(
            (
                a for a in assets
                if a.get("name", "").lower().endswith(".exe")
            ),
            None
        )

        return {
            "latest_version": latest_version,
            "download_url": (
                installer.get("browser_download_url")
                if installer else None
            ),
            "force_update": True,
            "message": "Nueva versión disponible del ERP-SOM."
        }

    except Exception:
        # ====================================================
        # FAIL SAFE ABSOLUTO
        # ====================================================
        # • GitHub caído
        # • Sin internet
        # • JSON inválido
        # • Timeout
        #
        # 👉 JAMÁS BLOQUEAR EL ERP
        # ====================================================
        return {
            "latest_version": None,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
