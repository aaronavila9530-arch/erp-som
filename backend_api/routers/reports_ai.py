from fastapi import APIRouter, HTTPException
from ai.maritime_ai import (
    improve_container_text,
    improve_grain_sampling_text
)

router = APIRouter(
    prefix="/reports/ai",
    tags=["Reports AI"]
)


# =========================================================
# CONTAINER AI (YA FUNCIONANDO)
# =========================================================
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
        # 🔥 DEBUG CRÍTICO
        print("❌ AI CONTAINER ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GRAIN SAMPLING AI (NUEVO)
# =========================================================
@router.post("/improve/grain")
def improve_grain(payload: dict):
    try:
        result = improve_grain_sampling_text(
            user_text=payload.get("text", ""),
            vessel=payload.get("vessel"),
            location=payload.get("location"),
            product=payload.get("product"),
            authority=payload.get("authority"),
        )

        return {"text": result}

    except Exception as e:
        # 🔥 DEBUG CRÍTICO
        print("❌ AI GRAIN ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
