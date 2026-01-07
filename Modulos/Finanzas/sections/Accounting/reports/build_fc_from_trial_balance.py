from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_fc_from_trial_balance(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el ESTADO DE FLUJO DE EFECTIVO (Método Indirecto)
    a partir de accounting_lines / trial balance.

    ✔ Deriva fiscal_year y period desde created_at
    ✔ Falla si hay mezcla de periodos
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
    # DERIVAR Y VALIDAR PERIODO FISCAL
    # =====================================================
    fiscal_year = None
    period = None

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

        fiscal_year = dt.year
        period = dt.month
        break

    if fiscal_year is None or period is None:
        raise ValueError(
            "No se pudo determinar año y periodo fiscal desde created_at"
        )

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
                "El Flujo de Efectivo debe construirse por un solo mes fiscal."
            )

    period_label = f"{period:02d}/{fiscal_year}"

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

        acc_norm = account.replace(".", "")
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
