from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from Modulos.MasterData.masterdata_forms import export_masterdata_form, get_spec


router = APIRouter(prefix="/master-data/forms", tags=["Master Data - Forms"])


def _safe_name(value: str) -> str:
    return "_".join("".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in value).split())


@router.get("/{entity_key}/{fmt}")
def download_masterdata_form(entity_key: str, fmt: str):
    fmt = fmt.lower().strip()
    if fmt not in {"word", "docx", "excel", "xlsx"}:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use word o excel.")
    try:
        key_map = {
            "clientes": "cliente",
            "proveedores": "proveedor",
            "empleados": "empleado",
            "surveyores": "surveyor",
            "servicios-md": "servicio",
        }
        resolved_key = key_map.get(entity_key, entity_key)
        spec = get_spec(resolved_key)
        suffix = ".docx" if fmt in {"word", "docx"} else ".xlsx"
        output_dir = tempfile.mkdtemp(prefix="masterdata_form_")
        filename = f"Formulario_MasterData_{_safe_name(spec.label)}{suffix}"
        output_path = str(Path(output_dir) / filename)
        export_masterdata_form(resolved_key, "Word" if suffix == ".docx" else "Excel", output_path)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if suffix == ".docx"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return FileResponse(output_path, filename=filename, media_type=media_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo exportar formulario: {exc}")
