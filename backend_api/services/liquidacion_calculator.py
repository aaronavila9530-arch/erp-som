from datetime import date


class CalculadoraLiquidacionCR:
    CESANTIA_DIAS_POR_ANO = [
        19.5, 20.0, 20.5, 21.0, 21.24, 21.5, 22.0, 22.0,
    ]

    @staticmethod
    def _months_between(fecha_ingreso, fecha_salida):
        return max(0, (fecha_salida.year - fecha_ingreso.year) * 12 + fecha_salida.month - fecha_ingreso.month)

    @staticmethod
    def _preaviso_dias(meses):
        if meses < 3:
            return 0
        if meses < 6:
            return 7
        if meses < 12:
            return 15
        return 30

    @classmethod
    def _cesantia_dias(cls, meses):
        if meses < 3:
            return 0
        if meses < 6:
            return 7
        if meses < 12:
            return 14

        anos = min(meses // 12, 8)
        fraccion_meses = meses % 12
        dias = sum(cls.CESANTIA_DIAS_POR_ANO[:anos])
        if fraccion_meses and anos < 8:
            dias += cls.CESANTIA_DIAS_POR_ANO[anos] * (fraccion_meses / 12)
        return dias

    @staticmethod
    def _aguinaldo_proporcional(salario_mensual, fecha_salida):
        inicio_aguinaldo = date(fecha_salida.year - 1, 12, 1)
        fin_aguinaldo = fecha_salida
        dias = max(0, (fin_aguinaldo - inicio_aguinaldo).days + 1)
        return round((salario_mensual * 12 / 365) * dias / 12, 2)

    @staticmethod
    def calcular(
        salario_mensual,
        fecha_ingreso,
        fecha_salida,
        vacaciones_pendientes,
        con_responsabilidad=True,
        con_orden_patronal=True
    ):
        if fecha_salida < fecha_ingreso:
            raise ValueError("La fecha de salida no puede ser anterior a la fecha de ingreso")

        salario_mensual = float(salario_mensual or 0)
        vacaciones_pendientes = float(vacaciones_pendientes or 0)
        dias_laborados = max(0, (fecha_salida - fecha_ingreso).days + 1)
        meses = CalculadoraLiquidacionCR._months_between(fecha_ingreso, fecha_salida)
        salario_diario = salario_mensual / 30

        aguinaldo = CalculadoraLiquidacionCR._aguinaldo_proporcional(salario_mensual, fecha_salida)
        vacaciones = round(vacaciones_pendientes * salario_diario, 2)

        cesantia = 0
        preaviso = 0
        cesantia_dias = 0
        preaviso_dias = 0

        if con_responsabilidad:
            cesantia_dias = CalculadoraLiquidacionCR._cesantia_dias(meses)
            preaviso_dias = CalculadoraLiquidacionCR._preaviso_dias(meses)
            cesantia = round(cesantia_dias * salario_diario, 2)
            preaviso = round(preaviso_dias * salario_diario, 2)

        total = round(aguinaldo + vacaciones + cesantia + preaviso, 2)

        return {
            "salario_mensual": salario_mensual,
            "fecha_ingreso": fecha_ingreso.isoformat(),
            "fecha_salida": fecha_salida.isoformat(),
            "dias_laborados": dias_laborados,
            "meses_laborados": meses,
            "con_responsabilidad": bool(con_responsabilidad),
            "orden_patronal": "CON ORDEN PATRONAL" if con_orden_patronal else "SIN ORDEN PATRONAL",
            "salario_diario": round(salario_diario, 2),
            "aguinaldo": aguinaldo,
            "vacaciones_dias": vacaciones_pendientes,
            "vacaciones": vacaciones,
            "cesantia_dias": round(cesantia_dias, 2),
            "cesantia": cesantia,
            "preaviso_dias": round(preaviso_dias, 2),
            "preaviso": preaviso,
            "total_liquidacion": total,
            "nota_legal": (
                "Estimacion basada en reglas generales de Costa Rica. "
                "Validar salario promedio, pagos variables, vacaciones reales, causal de salida y documentacion laboral."
            )
        }
