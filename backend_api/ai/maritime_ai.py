import os
from openai import OpenAI

# ============================================================
# CONFIGURACIÓN OPENAI
# ============================================================
# Usa la variable de entorno OPENAI_API_KEY
# Railway / local / .env
client = OpenAI()

# ============================================================
# PATH DEL PROMPT
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROMPT_PATH = os.path.join(
    BASE_DIR,
    "prompts",
    "maritime_container_report.prompt.txt"
)

# ============================================================
# CARGAR PROMPT DE CONTENEDOR
# ============================================================
def load_container_prompt() -> str:
    """
    Carga el prompt marítimo desde archivo.
    Este prompt es un ACTIVO del ERP, no código.
    """
    if not os.path.exists(PROMPT_PATH):
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_PATH}"
        )

    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================
# IA — MEJORAR TEXTO DE INFORME DE CONTENEDOR
# ============================================================
def improve_container_text(
    user_text: str,
    container_no: str | None = None,
    cargo: str | None = None,
    location: str | None = None,
    condition: str | None = None
) -> str:
    """
    Mejora un texto de inspección usando IA marítima.
    NO guarda nada.
    NO inventa datos.
    """

    if not user_text or not user_text.strip():
        raise ValueError("User text is required")

    prompt_template = load_container_prompt()

    # Inyección CONTROLADA de contexto
    prompt = (
        prompt_template
        .replace("{{container_no}}", container_no or "N/A")
        .replace("{{cargo}}", cargo or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{condition}}", condition or "N/A")
        .replace("{{user_text}}", user_text.strip())
    )

    # Llamada a OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,     # Bajo = factual
        max_tokens=600
    )

    return response.choices[0].message.content.strip()
