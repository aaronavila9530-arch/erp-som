from fastapi import APIRouter
import requests

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

GITHUB_REPO = "aaronavila9530-arch/erp-som"
CURRENT_VERSION = "1.0.0"

@router.get("")
def check_version():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()

        latest = data["tag_name"].lstrip("v")

        asset = next(
            (a for a in data["assets"] if a["name"].endswith(".exe")),
            None
        )

        return {
            "current_version": CURRENT_VERSION,
            "latest_version": latest,
            "force_update": False,
            "message": "Nueva versión disponible.",
            "download_url": asset["browser_download_url"] if asset else None
        }

    except Exception:
        return {
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "force_update": False
        }
