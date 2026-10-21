from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from resource_utils import resource_path
except ModuleNotFoundError:
    def resource_path(relative_path: str) -> str:
        return str(Path(__file__).resolve().parent / relative_path)


MSL_CODE = "MSL-CR"
MCI_CODE = "MCI-CR"


def is_mci_context(data: dict[str, Any] | None = None, company_code: str | None = None, company_name: str | None = None) -> bool:
    data = data or {}
    code = str(company_code or data.get("company_code") or "").strip().upper()
    name = str(company_name or data.get("company_name") or "").strip().upper()
    return code == MCI_CODE or "MARINE CLAIMS" in name or "RISK & INTELLIGENCE" in name


def company_display_name(data: dict[str, Any] | None = None, company_code: str | None = None, company_name: str | None = None) -> str:
    data = data or {}
    name = str(company_name or data.get("company_name") or "").strip()
    if name:
        return name
    if is_mci_context(data, company_code=company_code):
        return "MSL Marine Claims, Risk & Intelligence"
    return "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL"


def asset_path(name: str) -> str | None:
    here = Path(__file__).resolve().parent
    candidates = [
        Path(resource_path("assets")) / name,
        Path(resource_path(name)),
        here / "assets" / name,
        here.parent / "assets" / name,
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def logo_asset(data: dict[str, Any] | None = None, company_code: str | None = None, company_name: str | None = None) -> str | None:
    if is_mci_context(data, company_code=company_code, company_name=company_name):
        return asset_path("mci_logo.png") or asset_path("msl_logo.png") or asset_path("header.png")
    return asset_path("header.png") or asset_path("msl_logo.png")


def watermark_asset(data: dict[str, Any] | None = None, company_code: str | None = None, company_name: str | None = None) -> str | None:
    if is_mci_context(data, company_code=company_code, company_name=company_name):
        return asset_path("mci_logo.png") or asset_path("watermark.png")
    return asset_path("watermark.png") or asset_path("msl_logo.png")


def footer_text(data: dict[str, Any] | None = None, company_code: str | None = None, company_name: str | None = None) -> str:
    if is_mci_context(data, company_code=company_code, company_name=company_name):
        return (
            "Head Office - Costa Rica, Alajuela, Plaza Aeropuerto G-14\n"
            "MSL 2.0 - Marine Claims & Risk Intelligence"
        )
    return (
        "Head Office - Costa Rica, Alajuela, Plaza Aeropuerto G-14\n"
        "Phone (506) 8814-07-84 - (506) 4052-8382"
    )
