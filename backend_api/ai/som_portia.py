import json
import os

try:
    from ai.maritime_ai import _get_openai_client
    from ai.som_portia_knowledge import SOM_QA
except ImportError:
    from backend_api.ai.maritime_ai import _get_openai_client
from backend_api.ai.som_portia_knowledge import SOM_QA


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "N/D"


def _pct(numerator, denominator) -> str:
    try:
        denominator = float(denominator or 0)
        if denominator == 0:
            return "N/D"
        return f"{(float(numerator or 0) / denominator) * 100:,.2f}%"
    except Exception:
        return "N/D"


def _has_financial_context(fin: dict) -> bool:
    if not isinstance(fin, dict) or not fin:
        return False
    keys = (
        "facturado_total",
        "cuentas_por_cobrar",
        "pagos_recibidos",
        "cuentas_por_pagar_pendientes",
    )
    return any(fin.get(key) not in (None, "") for key in keys)


def _local_answer(question: str, context: dict) -> str:
    q = (question or "").lower()
    has_context = bool(context)

    if any(word in q for word in ("finanza", "financ", "factura", "cobrar", "cobranza", "saldo")):
        fin = context.get("finanzas", {})
        top = context.get("top_clientes_ar", [])
        servicios = context.get("servicios", {})
        comercial = context.get("comercial", {})
        if not _has_financial_context(fin):
            return (
                "No tengo contexto financiero vivo cargado en esta sesion. "
                "Para emitir un estado financiero real necesito leer Dashboard Finanzas, "
                "Collections, Incoming Payments e Invoice to Pay. No te muestro 0.00 "
                "como si fuera dato real porque eso ocultaria el problema de conexion."
            )

        facturado = fin.get("facturado_total", 0)
        ar = fin.get("cuentas_por_cobrar", 0)
        pagos = fin.get("pagos_recibidos", 0)
        ap = fin.get("cuentas_por_pagar_pendientes", 0)
        exposicion_neta = float(ar or 0) - float(ap or 0)
        lines = [
            "Estado financiero ejecutivo SOM:",
            f"- Facturado del periodo: USD {_money(facturado)}.",
            f"- Cuentas por cobrar abiertas: USD {_money(ar)}.",
            f"- Pagos recibidos/aplicados: USD {_money(pagos)}.",
            f"- Cuentas por pagar pendientes: USD {_money(ap)}.",
            f"- Exposicion neta de caja (AR - AP): USD {_money(exposicion_neta)}.",
            f"- Recuperacion sobre facturacion: {_pct(pagos, facturado)}.",
            f"- Presion de cobranza sobre facturacion: {_pct(ar, facturado)}.",
        ]
        if servicios:
            lines.append(
                "- Servicios finalizados pendientes de factura: "
                f"{servicios.get('pendientes_factura') or 0}."
            )
        if comercial:
            margen = comercial.get("margen_neto_pct")
            if margen not in (None, ""):
                try:
                    lines.append(f"- Margen neto comercial estimado: {float(margen):,.2f}%.")
                except Exception:
                    lines.append(f"- Margen neto comercial estimado: {margen}.")
        if top:
            lines.append("Clientes con mayor exposicion en cobro:")
            lines.extend(
                f"- {x.get('cliente', 'N/D')}: USD {_money(x.get('saldo'))}"
                for x in top[:5]
            )
        lines.extend([
            "Lectura PORTIA:",
            "- Si cuentas por cobrar sube contra pagos, prioridad es Collections y seguimiento de vencidos.",
            "- Si hay finalizados sin factura, Billing debe convertir esos servicios antes de medir cobranza.",
            "- Si AP supera AR, revisar flujo de caja y pagos programados antes de comprometer nuevos desembolsos.",
        ])
        if not has_context:
            lines.append("Nota: respuesta local sin snapshot completo del backend.")
        return "\n".join(lines)

    if any(word in q for word in ("servicio", "operacion", "finalizado", "facturar")):
        svc = context.get("servicios", {})
        return "\n".join([
            "Resumen de servicios SOM:",
            f"- Servicios totales: {svc.get('total') or 0}",
            f"- Servicios del ano actual: {svc.get('actual_year') or 0}",
            f"- Servicios finalizados: {svc.get('finalizados') or 0}",
            f"- Finalizados pendientes de factura: {svc.get('pendientes_factura') or 0}",
            f"- Valor factura acumulado: {svc.get('valor_factura_total', 0):,.2f}",
            *(
                ["Nota: esta respuesta usa modo local porque el contexto vivo del backend no esta disponible."]
                if not has_context else []
            ),
        ])

    if any(word in q for word in ("comercial", "cotizacion", "precio")):
        com = context.get("comercial", {})
        return "\n".join([
            "Resumen comercial SOM:",
            f"- Cotizaciones registradas: {com.get('cotizaciones') or 0}",
            f"- Cotizaciones aprobadas: {com.get('cotizaciones_aprobadas') or 0}",
            f"- Precios activos: {com.get('precios_activos') or 0}",
            *(
                ["Nota: esta respuesta usa modo local porque el contexto vivo del backend no esta disponible."]
                if not has_context else []
            ),
        ])

    if any(word in q for word in ("puerto", "pais", "actividad")):
        rows = context.get("actividad_puertos", [])
        if not rows:
            return "No encontre actividad por puerto disponible en el contexto actual."
        return "Puertos con mayor actividad:\n" + "\n".join(
            f"- {r['puerto']}, {r['pais']}: {r['servicios']} servicios"
            for r in rows[:10]
        )

    if any(word in q for word in ("informe", "report", "certificado")):
        inf = context.get("informes", {})
        return "\n".join([
            "Resumen de informes SOM:",
            f"- Container reports: {inf.get('container_reports') or 0}",
            f"- Grain sampling: {inf.get('grain_sampling') or 0}",
            f"- Truck supervision: {inf.get('truck_supervision') or 0}",
            f"- Draft survey: {inf.get('draft_survey') or 0}",
            f"- Bunker: {inf.get('bunker') or 0}",
            f"- Crane inspection: {inf.get('crane') or 0}",
        ])

    stopwords = {"que", "es", "el", "la", "los", "las", "un", "una", "de", "del", "para", "en"}
    q_words = {word.strip(" ?.,:;") for word in q.split()} - stopwords
    for item in SOM_QA:
        item_words = {word.strip(" ?.,:;") for word in item["question"].lower().split()} - stopwords
        if q_words and len(q_words & item_words) >= 2:
            return item["answer"]

    return (
        "PORTIA puede ayudarte con consultas de SOM sobre finanzas, comercial, "
        "servicios, puertos, master data e informes. Intenta preguntar, por ejemplo: "
        "'resume el estado financiero', 'servicios pendientes de factura' o "
        "'puertos con mayor actividad'."
    )


def answer_som_portia(question: str, context: dict, qa: list[dict]) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "answer": _local_answer(question, context),
            "mode": "local",
            "sources": ["SOM_QA", "database_snapshot"],
        }

    system = """
You are PORTIA for ERP SOM.
You answer in Spanish unless the user asks otherwise.
You are a consultative ERP assistant for financial, commercial, services,
master data, ports, HR summaries and reports data.
You do not analyze maritime operations or give operational instructions.
You do not modify data.
Use only the provided ERP context and Q&A base. If data is missing, say it.
Be concise, executive and practical.
""".strip()

    payload = {
        "question": question,
        "database_snapshot": context,
        "qa_base": qa,
    }

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv("PORTIA_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
        )

        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            answer = _local_answer(question, context)

        return {
            "answer": answer,
            "mode": "openai",
            "sources": ["SOM_QA", "database_snapshot"],
        }
    except Exception as exc:
        return {
            "answer": _local_answer(question, context),
            "mode": "local-fallback",
            "sources": ["SOM_QA", "database_snapshot"],
            "warning": str(exc),
        }
