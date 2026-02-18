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
# GRAIN SAMPLING AI (BILINGUAL + HARDENED)
# =========================================================
@router.post("/improve/grain")
def improve_grain(payload: dict):

    try:
        # 🔒 Validación básica
        user_text = (payload.get("text") or "").strip()
        if not user_text:
            raise HTTPException(
                status_code=400,
                detail="Text is required"
            )

        # 🔒 Normalizar idioma
        language = (payload.get("language") or "ES").upper()
        if language not in ("ES", "EN"):
            language = "ES"

        # 🔥 Llamada al servicio IA
        result = improve_grain_sampling_text(
            user_text=user_text,
            vessel=payload.get("vessel"),
            location=payload.get("location"),
            product=payload.get("product"),
            authority=payload.get("authority"),
            language=language  # 🔥 NUEVO
        )

        return {
            "success": True,
            "language": language,
            "text": result
        }

    except HTTPException:
        raise

    except Exception as e:
        # 🔥 DEBUG CRÍTICO
        print("❌ AI GRAIN ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"AI grain improvement failed: {str(e)}"
        )



# =========================================================
# TRUCK SUPERVISION AI
# =========================================================
@router.post("/improve/truck")
def improve_truck(payload: dict):

    try:
        user_text = (payload.get("text") or "").strip()
        if not user_text:
            raise HTTPException(
                status_code=400,
                detail="Text is required"
            )

        language = (payload.get("language") or "ES").upper()
        if language not in ("ES", "EN"):
            language = "ES"

        result = improve_truck_supervision_text(
            user_text=user_text,
            vessel=payload.get("vessel"),
            location=payload.get("location"),
            cargo=payload.get("cargo"),
            language=language
        )

        return {
            "success": True,
            "language": language,
            "text": result
        }

    except HTTPException:
        raise

    except Exception as e:
        print("❌ AI TRUCK ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"AI truck improvement failed: {str(e)}"
        )
