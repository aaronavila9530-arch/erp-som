from fastapi import APIRouter, HTTPException, Depends
from typing import Dict

from ai.maritime_ai import improve_container_text
from rbac_service import has_permission

router = APIRouter(
    prefix="/reports/ai",
    tags=["Reports - Maritime AI"]
)

# ============================================================
# RBAC GUARD (MISMO ESTÁNDAR ERP-SOM)
# ============================================================
def require_permission(module: str, action: str):
    def checker(x_user_role: str):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(
                status_code=403,
                detail="Not authorized"
            )
    return checker

# ============================================================
# POST /reports/ai/container/improve-text
# ============================================================
@router.post(
    "/container/improve-text",
    dependencies=[Depends(require_permission("reports", "write"))]
)
def improve_container_report_text(payload: Dict):
    """
    Mejora texto de informe de contenedor usando IA marítima.
    NO guarda.
    NO envía a pool.
    """

    try:
        improved_text = improve_container_text(
            user_text=payload.get("text", ""),
            container_no=payload.get("container_no"),
            cargo=payload.get("cargo"),
            location=payload.get("location"),
            condition=payload.get("condition")
        )

        return {
            "status": "ok",
            "text": improved_text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Maritime AI error: {str(e)}"
        )
