from fastapi import APIRouter, HTTPException
from ai.maritime_ai import improve_container_text

router = APIRouter(
    prefix="/reports/ai",
    tags=["Reports AI"]
)


@router.post("/improve/container")
def improve_container(payload: dict):
    try:
        result = improve_container_text(
            user_text=payload.get("text", ""),
            container_no=payload.get("container_no"),
            cargo=payload.get("cargo"),
            location=payload.get("location"),
            condition=payload.get("condition"),
        )

        return {"text": result}

    except Exception as e:
        # 🔥 ESTO ES CLAVE
        print("❌ AI CONTAINER ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
