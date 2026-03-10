import os
from typing import Optional


# =========================================================
# OPENAI CLIENT (LAZY + SAFE)
# =========================================================
def _get_openai_client():
    """
    Lazy loader del cliente OpenAI (SDK v1).
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada en el entorno.")

    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"No se pudo inicializar OpenAI client: {str(e)}")


# =========================================================
# PROMPT LOADERS
# =========================================================
def load_container_prompt() -> str:
    return """
You are acting as a Senior Marine Surveyor and Maritime Consultant
with over 20 years of professional experience in container inspections,
cargo condition surveys, and maritime claims handling.

You write exclusively in formal British English.
You do NOT invent facts.
You do NOT speculate or assign liability.

Inspection Context:
- Inspection Type: Container Inspection
- Container Number: {{container_no}}
- Cargo Description: {{cargo}}
- Location of Inspection: {{location}}
- Observed Condition Summary: {{condition}}

Original Surveyor Draft:
\"\"\"
{{user_text}}
\"\"\"

Rewrite the draft as a formal inspection narrative.

Return strictly:

Inspection Narrative:
<rewritten narrative>
""".strip()


def load_grain_sampling_prompt() -> str:
    base_path = os.path.dirname(__file__)
    prompt_path = os.path.join(base_path, "maritime_grain_sampling.prompt.txt")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError("Grain sampling prompt file not found.")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()



# =========================================================
# CARGO CONDITION PROMPT LOADER
# =========================================================
def load_cargo_condition_prompt() -> str:
    base_path = os.path.dirname(__file__)
    prompt_path = os.path.join(base_path, "maritime_cargo_condition.prompt.txt")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError("Cargo condition prompt file not found.")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


# =========================================================
# CONTAINER AI LOGIC
# =========================================================
def improve_container_text(
    user_text: str,
    container_no: Optional[str],
    cargo: Optional[str],
    location: Optional[str],
    condition: Optional[str]
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("El texto de entrada está vacío.")

    client = _get_openai_client()

    prompt = (
        load_container_prompt()
        .replace("{{container_no}}", container_no or "N/A")
        .replace("{{cargo}}", cargo or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{condition}}", condition or "N/A")
        .replace("{{user_text}}", user_text.strip())
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.2,
        max_output_tokens=600
    )

    output_text = getattr(response, "output_text", None)

    if not output_text or not output_text.strip():
        raise RuntimeError("La IA devolvió una respuesta vacía.")

    return output_text.strip()


# =========================================================
# GRAIN SAMPLING AI LOGIC (BILINGUAL + HARDENED)
# =========================================================
def improve_grain_sampling_text(
    user_text: str,
    vessel: Optional[str],
    location: Optional[str],
    product: Optional[str],
    authority: Optional[str],
    language: str = "ES"  # 🔥 NUEVO
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("El texto de entrada está vacío.")

    client = _get_openai_client()

    # 🔒 Normalizar idioma
    language = (language or "ES").upper()
    if language not in ("ES", "EN"):
        language = "ES"

    # 🔥 Cargar prompt base
    base_prompt = load_grain_sampling_prompt()

    # 🔥 Instrucción dinámica por idioma
    if language == "EN":
        language_instruction = (
            "\n\nIMPORTANT: Rewrite the report strictly in professional maritime English. "
            "Use formal surveyor tone. Maintain technical precision. Avoid exaggeration."
        )
    else:
        language_instruction = (
            "\n\nIMPORTANTE: Reescribe el informe estrictamente en español técnico profesional marítimo. "
            "Mantén tono formal de surveyor. Evita exageraciones."
        )

    prompt = (
        base_prompt
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{product}}", product or "Bulk Grain")
        .replace("{{authority}}", authority or "N/A")
        .replace("{{user_text}}", user_text.strip())
        + language_instruction
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=800
    )

    output_text = getattr(response, "output_text", None)

    if not output_text or not output_text.strip():
        raise RuntimeError("La IA devolvió una respuesta vacía.")

    return output_text.strip()



# =========================================================
# TRUCK SUPERVISION AI LOGIC (BILINGUAL)
# =========================================================
def improve_truck_supervision_text(
    user_text: str,
    vessel: Optional[str],
    location: Optional[str],
    cargo: Optional[str],
    language: str = "ES"
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("El texto de entrada está vacío.")

    client = _get_openai_client()

    language = (language or "ES").upper()
    if language not in ("ES", "EN"):
        language = "ES"

    base_path = os.path.dirname(__file__)
    prompt_path = os.path.join(base_path, "maritime_truck_supervision.prompt.txt")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError("Truck supervision prompt file not found.")

    with open(prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read().strip()

    if language == "EN":
        language_instruction = (
            "\n\nIMPORTANT: Rewrite strictly in professional maritime English. "
            "Maintain technical precision and neutral surveyor tone."
        )
    else:
        language_instruction = (
            "\n\nIMPORTANTE: Reescribe estrictamente en español técnico profesional marítimo. "
            "Mantén tono formal de inspector portuario."
        )

    prompt = (
        base_prompt
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{cargo}}", cargo or "Bulk Cargo")
        .replace("{{user_text}}", user_text.strip())
        + language_instruction
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=1000
    )

    output_text = getattr(response, "output_text", None)

    if not output_text or not output_text.strip():
        raise RuntimeError("La IA devolvió una respuesta vacía.")

    return output_text.strip()


# =========================================================
# CARGO CONDITION AI LOGIC (BILINGUAL + PRECAUTION SAFE)
# =========================================================
def improve_cargo_condition_text(
    user_text: str,
    vessel: Optional[str],
    port: Optional[str],
    section: Optional[str],
    language: str = "ES"
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("El texto de entrada está vacío.")

    client = _get_openai_client()

    language = (language or "ES").upper()
    if language not in ("ES", "EN"):
        language = "ES"

    base_prompt = load_cargo_condition_prompt()

    # 🔹 Instrucción dinámica por idioma
    if language == "EN":
        language_instruction = (
            "\n\nIMPORTANT: Rewrite strictly in professional maritime English. "
            "Maintain neutral surveyor tone."
        )
    else:
        language_instruction = (
            "\n\nIMPORTANTE: Reescribe estrictamente en español técnico profesional marítimo. "
            "Mantén tono formal de surveyor."
        )

    prompt = (
        base_prompt
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{port}}", port or "N/A")
        .replace("{{section}}", section or "narrative")
        .replace("{{user_text}}", user_text.strip())
        + language_instruction
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=900
    )

    output_text = getattr(response, "output_text", None)

    if not output_text or not output_text.strip():
        raise RuntimeError("La IA devolvió una respuesta vacía.")

    return output_text.strip()


# =========================================================
# CRANE INSPECTION PROMPT LOADER
# =========================================================
def load_crane_inspection_prompt() -> str:

    base_path = os.path.dirname(__file__)

    prompt_path = os.path.join(
        base_path,
        "maritime_crane_inspection.prompt.txt"
    )

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(
            "Crane inspection prompt file not found."
        )

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def improve_crane_inspection_text(
    user_text: str,
    vessel: Optional[str],
    port: Optional[str],
    section: Optional[str],
    language: str = "EN"
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("Input text is empty")

    client = _get_openai_client()

    language = (language or "EN").upper()

    base_prompt = load_crane_inspection_prompt()

    prompt = (
        base_prompt
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{port}}", port or "N/A")
        .replace("{{section}}", section or "remarks")
        .replace("{{language}}", language)
        .replace("{{user_text}}", user_text.strip())
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=900
    )

    output_text = getattr(response, "output_text", None)

    if not output_text:
        raise RuntimeError("AI returned empty response")

    return output_text.strip()



def improve_vessel_condition_text(
    user_text: str,
    vessel: Optional[str],
    port: Optional[str],
    report_type: Optional[str],
    section: Optional[str],
    language: str = "EN"
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("Input text is empty")

    client = _get_openai_client()

    language = (language or "EN").upper()

    base_path = os.path.dirname(__file__)

    prompt_path = os.path.join(
        base_path,
        "maritime_vessel_condition.prompt.txt"
    )

    if not os.path.exists(prompt_path):
        raise FileNotFoundError("Vessel condition prompt file not found.")

    with open(prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read().strip()

    prompt = (
        base_prompt
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{port}}", port or "N/A")
        .replace("{{report_type}}", report_type or "Vessel Condition Survey")
        .replace("{{section}}", section or "narrative")
        .replace("{{language}}", language)
        .replace("{{user_text}}", user_text.strip())
    )

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.15,
        max_output_tokens=900
    )

    output_text = getattr(response, "output_text", None)

    if not output_text:
        raise RuntimeError("AI returned empty response")

    return output_text.strip()

