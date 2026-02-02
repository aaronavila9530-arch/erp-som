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
# PROMPT
# =========================================================
def load_container_prompt() -> str:
    return """
You are acting as a Senior Marine Surveyor and Maritime Consultant
with over 20 years of professional experience in container inspections,
cargo condition surveys, and maritime claims handling.

You are fully conversant with standard practices applied by
P&I Clubs, marine insurers, shipping lines, terminal operators,
and port authorities.

You write exclusively in formal British English,
using precise maritime and insurance terminology.

You do NOT invent facts.
You do NOT add assumptions.
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

Rules:
- Preserve the original meaning
- Use third-person narrative
- Maintain a neutral, factual, and technical tone
- Do not invent findings, causes, or conclusions

Return the output strictly in the following format:

Inspection Narrative:
<rewritten narrative>
""".strip()


# =========================================================
# AI LOGIC (RESPONSES API)
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

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
            temperature=0.2,
            max_output_tokens=600
        )
    except Exception as e:
        raise RuntimeError(f"Error llamando a OpenAI Responses API: {str(e)}")

    # 🔒 Blindaje de salida
    try:
        output_text = response.output_text
    except Exception:
        raise RuntimeError("Respuesta inválida del modelo AI.")

    if not output_text or not output_text.strip():
        raise RuntimeError("La IA devolvió una respuesta vacía.")

    return output_text.strip()
