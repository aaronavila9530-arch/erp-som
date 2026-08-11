from backend_api.database import connect


def count_if_exists(cur, table, where="TRUE"):
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public' AND table_name=%s
        )
        """,
        (table,),
    )
    if not cur.fetchone()[0]:
        return None
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}")
    return cur.fetchone()[0]


def main():
    conn = connect()
    try:
        cur = conn.cursor()
        print("fixed_assets", count_if_exists(cur, "fixed_assets"))
        print("schedule", count_if_exists(cur, "fixed_asset_depreciation_schedule"))
        print(
            "aux_entities_import",
            count_if_exists(
                cur,
                "accounting_auxiliary_entities",
                "source_table='fixed_assets_import_2025' OR created_by='SYSTEM_IMPORT_ACTIVOS_2025'",
            ),
        )
        print(
            "aux_docs_import",
            count_if_exists(
                cur,
                "accounting_auxiliary_documents",
                "source_table='fixed_assets_import_2025' OR created_by='SYSTEM_IMPORT_ACTIVOS_2025'",
            ),
        )
        cur.execute("SELECT rate, rate_date, source FROM exchange_rate WHERE rate_date=DATE '2024-12-31'")
        print("tc_2024_12_31", cur.fetchall())
        if count_if_exists(cur, "fixed_assets"):
            cur.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(original_amount),0), COALESCE(SUM(value_crc),0),
                       COALESCE(SUM(accumulated_depreciation_crc),0), COALESCE(SUM(book_value_crc),0)
                FROM fixed_assets
                WHERE source_file='Activos e Inventario MSL FY2025.xlsx'
                """
            )
            print("totals", cur.fetchone())
            cur.execute(
                """
                SELECT asset_code, description, original_amount, exchange_rate, value_crc,
                       monthly_depreciation_crc, book_value_crc
                FROM fixed_assets
                WHERE source_file='Activos e Inventario MSL FY2025.xlsx'
                ORDER BY asset_code
                LIMIT 5
                """
            )
            print("sample", cur.fetchall())
    finally:
        conn.close()


if __name__ == "__main__":
    main()
