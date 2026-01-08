import psycopg2
import sys


# ============================================================
# DATABASE URL (Railway)
# ============================================================
DATABASE_URL = (
    "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)


# ============================================================
# SQL: LIMPIAR CONTENIDO DE TABLAS
# ============================================================
TRUNCATE_SQL = """
BEGIN;

TRUNCATE TABLE
    accounting_entries,
    accounting_lines,
    cash_app,
    cliente,
    cliente_credito,
    closing_batch_lines,
    closing_batches,
    closing_status,
    collections,
    disputa,
    dispute_history,
    dispute_management,
    empleados,
    factura,
    factura_detalle,
    incoming_payments,
    invoicing,
    payment_obligations,
    proveedor,
    servicios,
    serviciosmd,
    surveyor
RESTART IDENTITY CASCADE;

COMMIT;
"""


# ============================================================
# SQL: ELIMINAR TABLAS COMPLETAMENTE
# ============================================================
DROP_SQL = """
DROP TABLE IF EXISTS
    accounting_journal,
    disputes,
    factura_servicio
CASCADE;
"""


# ============================================================
# MAIN
# ============================================================
def main():
    try:
        print("🔌 Conectando a PostgreSQL (Railway)...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False

        with conn.cursor() as cur:
            print("🧹 Ejecutando TRUNCATE (limpieza total de datos)...")
            cur.execute(TRUNCATE_SQL)

            print("🗑️ Ejecutando DROP TABLE (eliminación de tablas)...")
            cur.execute(DROP_SQL)

        conn.commit()
        conn.close()

        print("✅ PROCESO FINALIZADO")
        print("✔️ Tablas limpiadas")
        print("✔️ IDs reiniciados")
        print("✔️ Tablas eliminadas correctamente")

    except Exception as e:
        print("❌ ERROR CRÍTICO")
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
