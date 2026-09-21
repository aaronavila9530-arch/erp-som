from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_esf_from_trial_balance(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el ESTADO DE SITUACIÓN FINANCIERA (ESF)
    a partir de accounting_lines / trial balance.

    ✔ Clasificación contable CR
    ✔ Deriva fiscal_year y periodo desde period o created_at
    ✔ Soporta mes único, rango de meses o periodo fiscal
    ✔ Incluye cuentas de resultado para lectura gerencial completa
    ✔ Salida lista para Excel / PDF
    ✔ Totalmente blindado
    """

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    if not isinstance(rows, list):
        raise ValueError("build_esf_from_trial_balance esperaba una LISTA de filas")

    if not rows:
        raise ValueError("No hay líneas contables para construir ESF")

    # =====================================================
    # DERIVAR PERIODO / RANGO
    # =====================================================
    periods = set()

    def _row_period(row):
        period_value = str(row.get("period") or "").strip()
        if len(period_value) == 7 and period_value[4] == "-":
            return period_value

        created_at = row.get("entry_date") or row.get("created_at")
        if not created_at:
            return None

        if isinstance(created_at, datetime):
            dt = created_at
        else:
            try:
                dt = datetime.fromisoformat(str(created_at).replace(" ", "T"))
            except Exception:
                return None

        return f"{dt.year}-{dt.month:02d}"

    for r in rows:
        if isinstance(r, dict):
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
    activo_corriente = defaultdict(float)
    activo_no_corriente = defaultdict(float)
    pasivo_corriente = defaultdict(float)
    pasivo_no_corriente = defaultdict(float)
    patrimonio = defaultdict(float)
    ingresos = defaultdict(float)
    costos = defaultdict(float)
    gastos = defaultdict(float)

    # =====================================================
    # PROCESAMIENTO DE LÍNEAS
    # =====================================================
    for r in rows:

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

        acc_norm = account.replace(".", "").replace("-", "")
        label = f"{account} - {name}"

        # =================================================
        # ACTIVO
        # =================================================
        if acc_norm.startswith("11"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                activo_corriente[label] += abs(monto)

        elif acc_norm.startswith("12"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                activo_no_corriente[label] += abs(monto)

        # =================================================
        # PASIVO
        # =================================================
        elif acc_norm.startswith("21"):
            monto = credit - debit
            if abs(monto) > 0.0001:
                pasivo_corriente[label] += abs(monto)

        elif acc_norm.startswith("22"):
            monto = credit - debit
            if abs(monto) > 0.0001:
                pasivo_no_corriente[label] += abs(monto)

        # =================================================
        # PATRIMONIO
        # =================================================
        elif acc_norm.startswith("3"):
            monto = credit - debit
            if abs(monto) > 0.0001:
                patrimonio[label] += abs(monto)

        # =================================================
        # RESULTADO DEL PERIODO
        # =================================================
        elif acc_norm.startswith("4"):
            monto = credit - debit
            if abs(monto) > 0.0001:
                ingresos[label] += abs(monto)

        elif acc_norm.startswith("5"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                gastos[label] += abs(monto)

        elif acc_norm.startswith("6"):
            monto = debit - credit
            if abs(monto) > 0.0001:
                costos[label] += abs(monto)

    # =====================================================
    # TOTALES
    # =====================================================
    total_activo_corriente = sum(activo_corriente.values())
    total_activo_no_corriente = sum(activo_no_corriente.values())
    total_activo = total_activo_corriente + total_activo_no_corriente

    total_pasivo_corriente = sum(pasivo_corriente.values())
    total_pasivo_no_corriente = sum(pasivo_no_corriente.values())
    total_pasivo = total_pasivo_corriente + total_pasivo_no_corriente

    total_patrimonio = sum(patrimonio.values())
    total_pasivo_patrimonio = total_pasivo + total_patrimonio
    total_ingresos = sum(ingresos.values())
    total_costos = sum(costos.values())
    total_gastos = sum(gastos.values())
    resultado_periodo = total_ingresos - total_costos - total_gastos

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

        # ACTIVO
        "activo_corriente": _fmt(activo_corriente),
        "total_activo_corriente": round(total_activo_corriente, 2),

        "activo_no_corriente": _fmt(activo_no_corriente),
        "total_activo_no_corriente": round(total_activo_no_corriente, 2),

        "total_activo": round(total_activo, 2),

        # PASIVO
        "pasivo_corriente": _fmt(pasivo_corriente),
        "total_pasivo_corriente": round(total_pasivo_corriente, 2),

        "pasivo_no_corriente": _fmt(pasivo_no_corriente),
        "total_pasivo_no_corriente": round(total_pasivo_no_corriente, 2),

        "total_pasivo": round(total_pasivo, 2),

        # PATRIMONIO
        "patrimonio": _fmt(patrimonio),
        "total_patrimonio": round(total_patrimonio, 2),

        # BALANCE
        "total_pasivo_patrimonio": round(total_pasivo_patrimonio, 2),
        "balance_ok": round(total_activo, 2) == round(total_pasivo_patrimonio, 2),
        "difference": round(total_activo - total_pasivo_patrimonio, 2),

        # RESULTADO / P&L DETAIL
        "ingresos": _fmt(ingresos),
        "total_ingresos": round(total_ingresos, 2),
        "costos": _fmt(costos),
        "total_costos": round(total_costos, 2),
        "gastos": _fmt(gastos),
        "total_gastos": round(total_gastos, 2),
        "resultado_periodo": round(resultado_periodo, 2),
    }
