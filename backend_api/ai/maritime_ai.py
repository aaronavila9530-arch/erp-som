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
# GRAIN SAMPLING AI LOGIC
# =========================================================
def improve_grain_sampling_text(
    user_text: str,
    vessel: Optional[str],
    location: Optional[str],
    product: Optional[str],
    authority: Optional[str]
) -> str:

    if not user_text or not user_text.strip():
        raise ValueError("El texto de entrada está vacío.")

    client = _get_openai_client()

    prompt = (
        load_grain_sampling_prompt()
        .replace("{{vessel}}", vessel or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{product}}", product or "Bulk Grain")
        .replace("{{authority}}", authority or "N/A")
        .replace("{{user_text}}", user_text.strip())
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
