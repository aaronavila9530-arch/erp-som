def calcular_planilla(salario_bruto):
    """
    Calcula deducciones y cargas sociales Costa Rica.
    """

    # Obrero
    obrero = {
        "SEM": round(salario_bruto * 0.055, 2),
        "IVM": round(salario_bruto * 0.0433, 2),
        "BPO": round(salario_bruto * 0.01, 2)
    }

    total_obrero = round(sum(obrero.values()), 2)

    # Patronal
    patronal = {
        "SEM": round(salario_bruto * 0.0925, 2),
        "IVM": round(salario_bruto * 0.0558, 2),
        "BPO": round(salario_bruto * 0.0025, 2),
        "ASIGNACIONES_FAMILIARES": round(salario_bruto * 0.05, 2),
        "IMAS": round(salario_bruto * 0.005, 2),
        "INA": round(salario_bruto * 0.015, 2),
        "LPT_BPO": round(salario_bruto * 0.0025, 2),
        "LPT_FCL": round(salario_bruto * 0.015, 2),
        "LPT_FPC": round(salario_bruto * 0.02, 2),
        "LPT_INS": round(salario_bruto * 0.01, 2)
    }

    total_patronal = round(sum(patronal.values()), 2)

    salario_neto = round(salario_bruto - total_obrero, 2)

    return {
        "salario_bruto": salario_bruto,
        "obrero": obrero,
        "total_obrero": total_obrero,
        "patronal": patronal,
        "total_patronal": total_patronal,
        "salario_neto": salario_neto
    }
