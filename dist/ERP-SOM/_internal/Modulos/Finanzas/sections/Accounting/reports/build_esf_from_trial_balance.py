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
    ✔ Deriva fiscal_year y period desde created_at
    ✔ Falla si hay mezcla de periodos
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
    # DERIVAR Y VALIDAR PERIODO FISCAL
    # =====================================================
    fiscal_year = None
    period = None

    for r in rows:
        if not isinstance(r, dict):
            continue

        created_at = r.get("created_at")
        if not created_at:
            continue

        # created_at puede ser str o datetime
        if isinstance(created_at, datetime):
            dt = created_at
        else:
            try:
                dt = datetime.fromisoformat(str(created_at))
            except Exception:
                continue

        fiscal_year = dt.year
        period = dt.month
        break

    if fiscal_year is None or period is None:
        raise ValueError(
            "No se pudo determinar año y periodo fiscal desde created_at"
        )

    # Validar que TODAS las líneas pertenezcan al mismo periodo
    for r in rows:
        created_at = r.get("created_at")
        if not created_at:
            continue

        if isinstance(created_at, datetime):
            dt = created_at
        else:
            try:
                dt = datetime.fromisoformat(str(created_at))
            except Exception:
                continue

        if dt.year != fiscal_year or dt.month != period:
            raise ValueError(
                "Las líneas contables contienen múltiples periodos. "
                "ESF debe construirse por un solo mes fiscal."
            )

    period_label = f"{period:02d}/{fiscal_year}"

    # =====================================================
    # ACUMULADORES
    # =====================================================
    activo_corriente = defaultdict(float)
    activo_no_corriente = defaultdict(float)
    pasivo_corriente = defaultdict(float)
    pasivo_no_corriente = defaultdict(float)
    patrimonio = defaultdict(float)

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

        acc_norm = account.replace(".", "")
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
    }
