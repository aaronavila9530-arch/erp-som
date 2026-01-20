from fastapi import APIRouter, HTTPException
from ai.maritime_ai import improve_container_text

router = APIRouter(
    prefix="/reports/ai",
    tags=["Reports AI"]
)


@router.post("/improve/container")
def improve_container(payload: dict):

    try:
        return {
            "text": improve_container_text(
                user_text=payload.get("text", ""),
                container_no=payload.get("container_no"),
                cargo=payload.get("cargo"),
                location=payload.get("location"),
                condition=payload.get("condition"),
            )
        }

    except RuntimeError as e:
        # Error de configuración (API KEY)
        raise HTTPException(500, str(e))

    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")
