from collections import defaultdict
from typing import List, Dict, Any

TAX_RATE_CR = 0.30  # Impuesto sobre la renta Costa Rica (30%)


def build_er_from_lines(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construye el Estado de Resultados (ER) a partir de accounting_lines.

    CLASIFICACIÓN CONTABLE (CR):

    INGRESOS
    - 4.x.x.x  → credit - debit

    COSTOS
    - 5.1.x.x → debit - credit

    GASTOS OPERATIVOS
    - 5.2.x.x → debit - credit

    OTROS
    - 6.x.x.x → debit - credit

    IMPUESTO
    - 30% sobre utilidad antes de impuestos (si es positiva)
    """

    # =====================================================
    # VALIDACIÓN FUERTE DE ENTRADA
    # =====================================================
    if not isinstance(rows, list):
        raise ValueError("build_er_from_lines esperaba una LISTA de filas (rows)")

    ingresos = defaultdict(float)
    costos = defaultdict(float)
    gastos_operativos = defaultdict(float)
    otros = defaultdict(float)

    # =====================================================
    # PROCESAMIENTO DE LÍNEAS CONTABLES
    # =====================================================
    for idx, r in enumerate(rows):

        # 🔒 Blindaje total por fila
        if not isinstance(r, dict):
            continue

        account = str(r.get("account_code") or "").strip()
        name = str(r.get("account_name") or "SIN NOMBRE").strip()

        try:
            debit = float(r.get("debit") or 0)
        except Exception:
            debit = 0.0

        try:
            credit = float(r.get("credit") or 0)
        except Exception:
            credit = 0.0

        if not account:
            continue

        # Normalizamos para soportar 5.1 / 5.1.01 / 51xx / etc.
        acc_norm = account.replace(".", "")

        # ---------------- INGRESOS (4xxx) ----------------
        if acc_norm.startswith("4"):
            monto = credit - debit
            if abs(monto) > 0.0001:
                ingresos[f"{account} - {name}"] += monto

        # ---------------- COSTOS (5.1xx) ----------------
        elif acc_norm.startswith("51"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                costos[f"{account} - {name}"] += monto

        # ---------------- GASTOS OPERATIVOS (5.2xx) ----------------
        elif acc_norm.startswith("52"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                gastos_operativos[f"{account} - {name}"] += monto

        # ---------------- OTROS (6xxx) ----------------
        elif acc_norm.startswith("6"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                otros[f"{account} - {name}"] += monto

        # Cualquier otro grupo NO entra en ER
        else:
            continue

    # =====================================================
    # TOTALES
    # =====================================================
    total_ingresos = sum(ingresos.values())
    total_costos = sum(costos.values())
    total_gastos_operativos = sum(gastos_operativos.values())
    total_otros = sum(otros.values())

    utilidad_bruta = total_ingresos - total_costos
    utilidad_operativa = utilidad_bruta - total_gastos_operativos
    utilidad_antes_impuestos = utilidad_operativa - total_otros

    impuesto_renta = (
        utilidad_antes_impuestos * TAX_RATE_CR
        if utilidad_antes_impuestos > 0
        else 0.0
    )

    utilidad_neta = utilidad_antes_impuestos - impuesto_renta

    # =====================================================
    # FORMATO FINAL (EXCEL / PDF)
    # =====================================================
    def _fmt(d: Dict[str, float]):
        return [
            {"label": k, "amount": round(v, 2)}
            for k, v in sorted(d.items())
        ]

    return {
        # INGRESOS
        "ingresos": _fmt(ingresos),
        "total_ingresos": round(total_ingresos, 2),

        # COSTOS
        "costos": _fmt(costos),
        "total_costos": round(total_costos, 2),

        # UTILIDAD BRUTA
        "utilidad_bruta": round(utilidad_bruta, 2),

        # GASTOS OPERATIVOS
        "gastos_operativos": _fmt(gastos_operativos),
        "total_gastos_operativos": round(total_gastos_operativos, 2),

        # UTILIDAD OPERATIVA
        "utilidad_operativa": round(utilidad_operativa, 2),

        # OTROS
        "otros": _fmt(otros),
        "total_otros": round(total_otros, 2),

        # RESULTADOS FINALES
        "utilidad_antes_impuestos": round(utilidad_antes_impuestos, 2),
        "impuesto_renta": round(impuesto_renta, 2),
        "utilidad_neta": round(utilidad_neta, 2),
    }
