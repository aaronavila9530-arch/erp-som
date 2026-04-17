import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


class FixIDs:

    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(DB_URL)
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise

    def process_table(self, table_name):
        try:
            print(f"\n🔧 Processing table: {table_name}")

            # ============================================
            # DELETE IDS 1,2,3
            # ============================================
            self.cursor.execute(f"""
                DELETE FROM {table_name}
                WHERE id IN (1, 2, 3);
            """)
            print("🗑️ Deleted IDs 1,2,3")

            # ============================================
            # UPDATE ID 4 -> 1
            # ============================================
            self.cursor.execute(f"""
                UPDATE {table_name}
                SET id = 1
                WHERE id = 4;
            """)
            print("✏️ Updated ID 4 → 1")

            # ============================================
            # RESET SEQUENCE (CRÍTICO)
            # ============================================
            self.cursor.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                    true
                );
            """)
            print("🔄 Sequence reset correctly")

        except Exception as e:
            print(f"❌ Error processing {table_name}: {e}")
            self.conn.rollback()
            raise

    def run(self):
        try:
            self.connect()

            # ============================================
            # PROCESS BOTH TABLES
            # ============================================
            self.process_table("container_reports")
            self.process_table("container_reports_flat")

            self.conn.commit()
            print("\n✅ All operations completed successfully")

        except Exception as e:
            print(f"\n❌ Transaction failed: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("🔒 Connection closed")


if __name__ == "__main__":
    FixIDs().run()