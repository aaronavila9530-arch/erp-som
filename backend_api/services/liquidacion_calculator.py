from datetime import date


class CalculadoraLiquidacionCR:

    @staticmethod
    def calcular(
        salario_mensual,
        fecha_ingreso,
        fecha_salida,
        vacaciones_pendientes,
        con_responsabilidad=True
    ):
        dias_laborados = (fecha_salida - fecha_ingreso).days
        salario_diario = salario_mensual / 30

        # Aguinaldo proporcional
        aguinaldo = round((salario_mensual / 12) * ((fecha_salida.month - 1) / 12), 2)

        # Vacaciones
        vacaciones = round(vacaciones_pendientes * salario_diario, 2)

        cesantia = 0
        preaviso = 0

        if con_responsabilidad:
            # Cesantía (1 día por mes trabajado – simplificado MVP)
            meses = dias_laborados // 30
            cesantia = round(meses * salario_diario, 2)

            # Preaviso (1 mes si > 1 año)
            if meses >= 12:
                preaviso = round(salario_mensual, 2)

        total = round(aguinaldo + vacaciones + cesantia + preaviso, 2)

        return {
            "salario_mensual": salario_mensual,
            "aguinaldo": aguinaldo,
            "vacaciones": vacaciones,
            "cesantia": cesantia,
            "preaviso": preaviso,
            "total_liquidacion": total
        }
