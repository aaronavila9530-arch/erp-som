from fastapi import APIRouter
import requests

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

GITHUB_REPO = "aaronavila9530-arch/erp-som"
CURRENT_VERSION = "1.0.2"
APP_VERSION = CURRENT_VERSION  # 👈 alias para frontend


@router.get("/")
def check_version():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()

        tag = data.get("tag_name", "")
        latest_version = tag.lstrip("v")

        assets = data.get("assets", [])
        installer = next(
            (a for a in assets if a.get("name", "").lower().endswith(".exe")),
            None
        )

        return {
            "current_version": CURRENT_VERSION,
            "latest_version": latest_version,
            "download_url": installer["browser_download_url"] if installer else None,
            "force_update": latest_version != CURRENT_VERSION,
            "message": "UPDATE REQUIRED" if latest_version != CURRENT_VERSION else ""
        }

    except Exception:
        # FAIL SAFE: jamás romper el ERP
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": ""
        }
