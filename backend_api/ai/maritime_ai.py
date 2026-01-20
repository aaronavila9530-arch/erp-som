import os


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

    from openai import OpenAI
    return OpenAI(api_key=api_key)


def load_container_prompt() -> str:
    """
    Prompt base para informes de contenedor.
    """
    return """
You are a Senior Marine Surveyor and Maritime Consultant
with over 20 years of experience in container inspections,
cargo damage surveys, and maritime claims handling.

You write in formal British English using professional
maritime and insurance terminology.

You do NOT invent facts.
You do NOT add assumptions.
You only rewrite, enhance, and formalise the content provided.

Context:
- Inspection Type: Container Inspection
- Container Number: {{container_no}}
- Cargo: {{cargo}}
- Location: {{location}}
- Condition: {{condition}}

Original Surveyor Draft:
\"\"\"
{{user_text}}
\"\"\"

Rewrite the text as a formal inspection narrative.

Guidelines:
- Preserve the original meaning
- Use third person
- Maintain a neutral, factual and technical tone
- Use appropriate maritime survey terminology
- Do not invent findings or conclusions

Return the output in the following format:

Inspection Narrative:
<rewritten text>
""".strip()


def improve_container_text(
    user_text: str,
    container_no: str,
    cargo: str,
    location: str,
    condition: str
) -> str:

    client = _get_openai_client()

    prompt_template = load_container_prompt()

    prompt = (
        prompt_template
        .replace("{{container_no}}", container_no or "N/A")
        .replace("{{cargo}}", cargo or "N/A")
        .replace("{{location}}", location or "N/A")
        .replace("{{condition}}", condition or "N/A")
        .replace("{{user_text}}", user_text or "")
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()
