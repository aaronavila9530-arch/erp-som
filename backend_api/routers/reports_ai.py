from fastapi import APIRouter, HTTPException
from ai.maritime_ai import (
    improve_container_text,
    improve_truck_supervision_text,
    improve_grain_sampling_text,
    improve_cargo_condition_text,
    improve_crane_inspection_text,
    improve_vessel_condition_text,
    improve_port_captancy_text
)

router = APIRouter(
    prefix="/reports/ai",
    tags=["Reports PORTIA"]
)


# =========================================================
# CONTAINER PORTIA (YA FUNCIONANDO)
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
        print("❌ PORTIA CONTAINER ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GRAIN SAMPLING PORTIA (BILINGUAL + HARDENED)
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

        # 🔥 Llamada al servicio PORTIA
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
        print("❌ PORTIA GRAIN ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"PORTIA grain improvement failed: {str(e)}"
        )



# =========================================================
# TRUCK SUPERVISION PORTIA
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
        print("❌ PORTIA TRUCK ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=f"PORTIA truck improvement failed: {str(e)}"
        )



# =========================================================
# CARGO CONDITION PORTIA (SINGLE OR MULTI BLOCK)
# =========================================================
@router.post("/improve/cargo-condition")
def improve_cargo_condition(payload: dict):

    try:
        language = (payload.get("language") or "ES").upper()
        if language not in ("ES", "EN"):
            language = "ES"

        vessel = payload.get("vessel")
        port = payload.get("port")
        section = payload.get("section")

        # -----------------------------------------------------
        # CASE 1: MULTIPLE ITEMS (BULLETS)
        # -----------------------------------------------------
        items = payload.get("items")

        if isinstance(items, list) and items:

            improved_items = []

            for item in items:
                text = (item or "").strip()
                if not text:
                    improved_items.append("")
                    continue

                result = improve_cargo_condition_text(
                    user_text=text,
                    vessel=vessel,
                    port=port,
                    section=section,
                    language=language
                )

                improved_items.append(result)

            return {
                "success": True,
                "language": language,
                "items": improved_items
            }

        # -----------------------------------------------------
        # CASE 2: SINGLE TEXT
        # -----------------------------------------------------
        user_text = (payload.get("text") or "").strip()

        if not user_text:
            raise HTTPException(
                status_code=400,
                detail="Text or items are required"
            )

        result = improve_cargo_condition_text(
            user_text=user_text,
            vessel=vessel,
            port=port,
            section=section,
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
        print("❌ PORTIA CARGO CONDITION ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail="PORTIA cargo condition improvement failed."
        )

# =========================================================
# Crane inspection PORTIA
# =========================================================

@router.post("/improve/crane-inspection")
def improve_crane_inspection(payload: dict):

    try:

        language = (payload.get("language") or "EN").upper()
        if language not in ("ES", "EN"):
            language = "EN"

        vessel = payload.get("vessel")
        port = payload.get("port")
        section = payload.get("section")

        items = payload.get("items")

        if isinstance(items, list):

            improved = []

            for item in items:

                result = improve_crane_inspection_text(
                    user_text=item,
                    vessel=vessel,
                    port=port,
                    section=section,
                    language=language
                )

                improved.append(result)

            return {
                "success": True,
                "items": improved
            }

        raise HTTPException(status_code=400, detail="Items required")

    except Exception as e:

        print("❌ PORTIA CRANE INSPECTION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# =========================================================
# VESSEL CONDITION SURVEY PORTIA
# =========================================================
@router.post("/improve/vessel-condition")
def improve_vessel_condition(payload: dict):

    try:

        language = (payload.get("language") or "EN").upper()

        if language not in ("ES", "EN"):
            language = "EN"

        vessel = payload.get("vessel")
        port = payload.get("port")
        report_type = payload.get("report_type")
        section = payload.get("section")

        # -----------------------------------------------------
        # CASE 1 — MULTIPLE BULLETS
        # -----------------------------------------------------
        items = payload.get("items")

        if isinstance(items, list):

            improved = []

            for item in items:

                text = (item or "").strip()

                if not text:
                    improved.append("")
                    continue

                result = improve_vessel_condition_text(
                    user_text=text,
                    vessel=vessel,
                    port=port,
                    report_type=report_type,
                    section=section,
                    language=language
                )

                improved.append(result)

            return {
                "success": True,
                "language": language,
                "items": improved
            }

        # -----------------------------------------------------
        # CASE 2 — SINGLE TEXT
        # -----------------------------------------------------
        user_text = (payload.get("text") or "").strip()

        if not user_text:
            raise HTTPException(
                status_code=400,
                detail="Text or items are required"
            )

        result = improve_vessel_condition_text(
            user_text=user_text,
            vessel=vessel,
            port=port,
            report_type=report_type,
            section=section,
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

        print("❌ PORTIA VESSEL CONDITION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="PORTIA vessel condition improvement failed."
        )


# =========================================================
# PORT CAPTANCY PORTIA
# =========================================================
@router.post("/improve/port-captancy")
def improve_port_captancy(payload: dict):

    try:

        language = (payload.get("language") or "EN").upper()

        if language not in ("ES","EN"):
            language = "EN"

        vessel = payload.get("vessel")
        port = payload.get("port")
        operation = payload.get("operation")
        section = payload.get("section")

        items = payload.get("items")

        if isinstance(items, list):

            improved = []

            for item in items:

                text = (item or "").strip()

                if not text:
                    improved.append("")
                    continue

                result = improve_port_captancy_text(
                    user_text=text,
                    vessel=vessel,
                    port=port,
                    operation=operation,
                    section=section,
                    language=language
                )

                improved.append(result)

            return {
                "success": True,
                "language": language,
                "items": improved
            }

        raise HTTPException(status_code=400, detail="Items required")

    except Exception as e:

        print("❌ PORTIA PORT CAPTANCY ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# LOGRA PORTIA
# =========================================================
@router.post("/improve/logra")
def improve_logra(payload: dict):
    try:
        language = (payload.get("language") or "EN").upper()
        if language not in ("ES", "EN"):
            language = "EN"

        section = payload.get("section") or "logra"
        category = payload.get("category") or "logra"
        items = payload.get("items")

        def _fallback(text: str) -> str:
            clean = " ".join((text or "").split())
            if language == "EN":
                return clean
            return clean

        if isinstance(items, list):
            improved = []
            for item in items:
                text = (item or "").strip()
                if not text:
                    improved.append("")
                    continue
                try:
                    result = improve_port_captancy_text(
                        user_text=text,
                        vessel="LOGRA",
                        port=category,
                        operation="Meeting log",
                        section=section,
                        language=language,
                    )
                except Exception:
                    result = _fallback(text)
                improved.append(result)

            return {
                "success": True,
                "language": language,
                "items": improved,
            }

        user_text = (payload.get("text") or "").strip()
        if not user_text:
            raise HTTPException(status_code=400, detail="Text or items are required")

        try:
            result = improve_port_captancy_text(
                user_text=user_text,
                vessel="LOGRA",
                port=category,
                operation="Meeting log",
                section=section,
                language=language,
            )
        except Exception:
            result = _fallback(user_text)

        return {
            "success": True,
            "language": language,
            "text": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("PORTIA LOGRA ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
