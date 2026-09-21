from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_fc_from_trial_balance(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el ESTADO DE FLUJO DE EFECTIVO (Método Indirecto)
    a partir de accounting_lines / trial balance.

    ✔ Deriva periodo desde period, entry_date o created_at
    ✔ Soporta mes único, rango de meses o periodo fiscal
    ✔ Construcción 100% desde accounting_lines
    ✔ Salida lista para Excel / PDF
    ✔ Totalmente blindado
    """

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    if not isinstance(rows, list):
        raise ValueError("build_fc_from_trial_balance esperaba una LISTA de filas")

    if not rows:
        raise ValueError("No hay líneas contables para construir Flujo de Efectivo")

    # =====================================================
    # DERIVAR PERIODO / RANGO
    # =====================================================
    periods = set()

    def _row_period(row):
        period_value = str(row.get("period") or "").strip()
        if len(period_value) == 7 and period_value[4] == "-":
            return period_value

        date_value = row.get("entry_date") or row.get("created_at")
        if not date_value:
            return None
        if isinstance(date_value, datetime):
            dt = date_value
        else:
            try:
                dt = datetime.fromisoformat(str(date_value).replace(" ", "T"))
            except Exception:
                return None
        return f"{dt.year}-{dt.month:02d}"

    for r in rows:
        if not isinstance(r, dict):
            continue
        period_value = _row_period(r)
        if period_value:
            periods.add(period_value)

    if not periods:
        raise ValueError(
            "No se pudo determinar periodo fiscal desde period, entry_date o created_at"
        )

    sorted_periods = sorted(periods)
    first_period = sorted_periods[0]
    last_period = sorted_periods[-1]
    fiscal_year = int(last_period[:4])
    period = int(last_period[5:7])
    period_label = (
        first_period
        if first_period == last_period
        else f"{first_period} a {last_period}"
    )

    # =====================================================
    # ACUMULADORES
    # =====================================================
    operacion = defaultdict(float)
    inversion = defaultdict(float)
    financiamiento = defaultdict(float)

    # =====================================================
    # PROCESAMIENTO DE LÍNEAS
    # =====================================================
    for r in rows:

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

        acc_norm = account.replace(".", "").replace("-", "")
        label = f"{account} - {name}"

        # =================================================
        # OPERACIÓN
        # =================================================
        # Activos corrientes, pasivos corrientes, resultados
        if acc_norm.startswith(("11", "21", "4", "5", "6", "7")):
            monto = debit - credit
            if abs(monto) > 0.0001:
                operacion[label] += monto

        # =================================================
        # INVERSIÓN
        # =================================================
        # Activos no corrientes
        elif acc_norm.startswith("12"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                inversion[label] += monto

        # =================================================
        # FINANCIAMIENTO
        # =================================================
        # Pasivos largo plazo y patrimonio
        elif acc_norm.startswith(("22", "3")):
            monto = credit - debit
            if abs(monto) > 0.0001:
                financiamiento[label] += monto

    # =====================================================
    # TOTALES
    # =====================================================
    neto_operacion = sum(operacion.values())
    neto_inversion = sum(inversion.values())
    neto_financiamiento = sum(financiamiento.values())

    variacion_efectivo = (
        neto_operacion + neto_inversion + neto_financiamiento
    )

    # =====================================================
    # FORMATO FINAL
    # =====================================================
    def _fmt(d: Dict[str, float]):
        return [
            {"label": k, "amount": round(v, 2)}
            for k, v in sorted(d.items())
        ]

    return {
        # METADATA
        "fiscal_year": fiscal_year,
        "period": period,
        "period_label": period_label,

        # OPERACIÓN
        "operacion": _fmt(operacion),
        "neto_operacion": round(neto_operacion, 2),

        # INVERSIÓN
        "inversion": _fmt(inversion),
        "neto_inversion": round(neto_inversion, 2),

        # FINANCIAMIENTO
        "financiamiento": _fmt(financiamiento),
        "neto_financiamiento": round(neto_financiamiento, 2),

        # EFECTIVO
        "variacion_efectivo": round(variacion_efectivo, 2),
        "efectivo_inicio": 0.0,   # se puede mejorar luego
        "efectivo_final": round(variacion_efectivo, 2),
    }
