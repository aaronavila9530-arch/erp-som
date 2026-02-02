import os
from typing import Optional


# =========================================================
# OPENAI CLIENT (LAZY + SAFE)
# =========================================================
def _get_openai_client():
    """
    Lazy loader del cliente OpenAI.
    Evita que el backend crashee si la key no está configurada.
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
        raise RuntimeError(f"No se pudo inicializar OpenAI client: {str(e)}")


# =========================================================
# PROMPT LOADER (INLINE, SIN PATHS)
# =========================================================
def load_container_prompt() -> str:
    """
    Prompt base para informes de inspección de contenedores.
    """
    return """
You are a Senior Marine Surveyor and Maritime Consultant
with over 20 years of professional experience in container inspections,
cargo damage surveys, and maritime claims handling.

You write exclusively in formal British English,
using precise maritime and insurance terminology.

You do NOT invent facts.
You do NOT add assumptions.
You do NOT speculate or assign liability.
You only enhance clarity, structure, and professional tone.

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
- Use professional maritime survey terminology
- Do not invent findings, causes, or conclusions

Return the output strictly in the following format:

Inspection Narrative:
<rewritten narrative>
""".strip()


# =========================================================
# AI LOGIC
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

    # Reemplazo SEGURO (no usar .format)
    prompt = (
        prompt_template
        .replace("{{container_no}}", container_no or "N/A")
        .replace("{{cargo}}", cargo or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{condition}}", condition or "N/A")
        .replace("{{user_text}}", user_text.strip())
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
    except Exception as e:
        raise RuntimeError(f"Error llamando a OpenAI API: {str(e)}")

    # Blindaje de respuesta
    if (
        not response
        or not response.choices
        or not response.choices[0].message
        or not response.choices[0].message.content
    ):
        raise RuntimeError("Respuesta vacía o inválida del modelo AI.")

    return response.choices[0].message.content.strip()
