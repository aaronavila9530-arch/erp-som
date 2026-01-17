from fastapi import APIRouter
import requests
import os

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

GITHUB_REPO = "aaronavila9530-arch/erp-som"
CURRENT_VERSION = "1.0.1"


@router.get("/")
def check_version():

    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ERP-SOM-Updater"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        latest_version = data["tag_name"].lstrip("v")

        asset = next(
            (a for a in data.get("assets", []) if a["name"].lower().endswith(".exe")),
            None
        )

        if not asset:
            return {
                "latest_version": latest_version,
                "download_url": None,
                "force_update": False,
                "message": "No installer asset found"
            }

        force_update = latest_version != CURRENT_VERSION

        return {
            "latest_version": latest_version,
            "download_url": asset["browser_download_url"],
            "force_update": force_update,
            "message": "Update available" if force_update else ""
        }

    except Exception as e:
        return {
            "latest_version": CURRENT_VERSION,
            "download_url": None,
            "force_update": False,
            "message": f"Updater error: {str(e)}"
        }
