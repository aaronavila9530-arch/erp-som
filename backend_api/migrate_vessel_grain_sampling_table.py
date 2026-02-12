import psycopg2

# ============================================================
# CONFIG
# ============================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# ============================================================
# MIGRATION SCRIPT
# ============================================================

def column_exists(cur, table, column):
    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
        AND column_name = %s
    """, (table, column))
    return cur.fetchone() is not None


def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🔍 Starting migration...")

        table = "vessel_grain_sampling_reports"

        # ====================================================
        # 1️⃣ RENAME products_table → products
        # ====================================================
        if column_exists(cur, table, "products_table"):
            print("🔄 Renaming products_table → products")
            cur.execute("""
                ALTER TABLE vessel_grain_sampling_reports
                RENAME COLUMN products_table TO products
            """)

        # ====================================================
        # 2️⃣ DROP old columns
        # ====================================================
        old_columns = ["times", "products_summary"]

        for col in old_columns:
            if column_exists(cur, table, col):
                print(f"🗑 Dropping column {col}")
                cur.execute(f"""
                    ALTER TABLE vessel_grain_sampling_reports
                    DROP COLUMN {col}
                """)

        # ====================================================
        # 3️⃣ ADD TIME FIELDS (1:1 Word)
        # ====================================================
        time_fields = [
            "arrival_buoy_time",
            "nor_tendered_time",
            "holds_opening_time",
            "surveyors_onboard_time",
            "seals_verification_time",
            "sampling_start_time",
            "sampling_end_time",
            "surveyors_disembark_time"
        ]

        for col in time_fields:
            if not column_exists(cur, table, col):
                print(f"➕ Adding column {col}")
                cur.execute(f"""
                    ALTER TABLE vessel_grain_sampling_reports
                    ADD COLUMN {col} TEXT
                """)

        # ====================================================
        # 4️⃣ ADD PRODUCT STRUCTURE FIELDS
        # ====================================================
        new_product_fields = [
            "products_header_line",
            "products_total"
        ]

        for col in new_product_fields:
            if not column_exists(cur, table, col):
                print(f"➕ Adding column {col}")
                cur.execute(f"""
                    ALTER TABLE vessel_grain_sampling_reports
                    ADD COLUMN {col} TEXT
                """)

        # ====================================================
        # 5️⃣ ADD DECLARATION / SIGNATURE FIELDS
        # ====================================================
        signature_fields = [
            "legal_text",
            "attachments",
            "surveyor_name",
            "surveyor_position"
        ]

        for col in signature_fields:
            if not column_exists(cur, table, col):
                print(f"➕ Adding column {col}")
                cur.execute(f"""
                    ALTER TABLE vessel_grain_sampling_reports
                    ADD COLUMN {col} TEXT
                """)

        # ====================================================
        # 6️⃣ Ensure products column exists (JSON safe)
        # ====================================================
        if not column_exists(cur, table, "products"):
            print("➕ Adding products column (JSONB)")
            cur.execute("""
                ALTER TABLE vessel_grain_sampling_reports
                ADD COLUMN products JSONB
            """)

        conn.commit()
        print("✅ Migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print("❌ Migration failed:", str(e))

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
