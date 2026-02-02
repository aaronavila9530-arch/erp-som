import os
from typing import Optional


# =========================================================
# OPENAI CLIENT (LAZY + SAFE)
# =========================================================
def _get_openai_client():
    """
    Lazy loader del cliente OpenAI.
    Evita que el backend crashee si la key no está configurada
    o si el SDK no está disponible.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada en el entorno."
        )

    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as e:
        raise RuntimeError(
            f"No se pudo inicializar OpenAI client: {str(e)}"
        )


# =========================================================
# PROMPT LOADER (INLINE, SIN PATHS)
# =========================================================
def load_container_prompt() -> str:
    """
    Prompt base para informes de inspección de contenedores.
    Optimizado para uso en claims, P&I Clubs e informes técnicos.
    """
    return """
You are acting as a Senior Marine Surveyor and Maritime Consultant
with over 20 years of professional experience in container inspections,
cargo condition surveys, damage assessments, and maritime claims handling.

You are fully conversant with standard practices applied by
P&I Clubs, marine insurers, shipping lines, terminal operators,
and survey companies.

You write exclusively in formal British English,
using precise, objective, and industry-accepted maritime
and insurance terminology suitable for official survey reports.

STRICT PROFESSIONAL RULES:
- You do NOT invent facts
- You do NOT introduce assumptions
- You do NOT speculate on causes, responsibilities, or liability
- You do NOT exaggerate findings
- You only clarify, structure, and professionally formalise the text provided

Inspection Context (for reference only):
- Inspection Type: Container Inspection
- Container Number: {{container_no}}
- Cargo Description: {{cargo}}
- Location of Inspection: {{location}}
- Observed Condition Summary: {{condition}}

Original Surveyor Draft:
\"\"\"
{{user_text}}
\"\"\"

INSTRUCTIONS:
- Preserve the original meaning and factual content
- Use third-person narrative at all times
- Maintain a neutral, factual, and technical tone
- Improve clarity, structure, grammar, and terminology
- Use recognised maritime survey vocabulary
- Do NOT introduce new findings, causes, opinions, or conclusions

OUTPUT FORMAT (MANDATORY):
Inspection Narrative:
<rewritten inspection narrative>
""".strip()


# =========================================================
# AI LOGIC (PRODUCTION SAFE)
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
    prompt_template = load_container_prompt()

    # Reemplazo seguro (NO usar .format)
    prompt = (
        prompt_template
        .replace("{{container_no}}", container_no or "N/A")
        .replace("{{cargo}}", cargo or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{condition}}", condition or "N/A")
        .replace("{{user_text}}", user_text.strip())
    )

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )
    except Exception as e:
        raise RuntimeError(
            f"Error llamando a OpenAI API: {str(e)}"
        )

    # =====================================================
    # BLINDAJE DE RESPUESTA
    # =====================================================
    output_text = getattr(response, "output_text", None)

    if not output_text or not output_text.strip():
        raise RuntimeError(
            "La respuesta del modelo AI está vacía o es inválida."
        )

    return output_text.strip()
