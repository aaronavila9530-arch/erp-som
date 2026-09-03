def ensure_employee_hours_policy_columns(cur):
    for ddl in (
        "ALTER TABLE empleados ADD COLUMN IF NOT EXISTS horas_contratadas NUMERIC(10,2)",
        "ALTER TABLE empleados ADD COLUMN IF NOT EXISTS horas_tope_ordinario NUMERIC(10,2)",
        "ALTER TABLE empleados ADD COLUMN IF NOT EXISTS horas_tope_maximo NUMERIC(10,2)",
        "ALTER TABLE empleados ADD COLUMN IF NOT EXISTS tarifa_hora_extra NUMERIC(12,2)",
        "ALTER TABLE empleados ADD COLUMN IF NOT EXISTS pago_minimo_garantizado BOOLEAN DEFAULT FALSE",
    ):
        cur.execute(ddl)
