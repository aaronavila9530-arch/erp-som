import psycopg2
from psycopg2 import sql


# =========================================================
# DATABASE CONNECTION
# =========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


# =========================================================
# TABLES TO RESET
# =========================================================
TABLES = [
    "draft_survey_word_report",
    "draft_survey_ballast",
    "draft_survey",
    "general_draft_survey"
]


def reset_tables():
    conn = None
    cur = None

    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("🧨 Truncating tables and resetting identities...")

        query = sql.SQL("""
            TRUNCATE TABLE {} RESTART IDENTITY CASCADE;
        """).format(
            sql.SQL(", ").join(map(sql.Identifier, TABLES))
        )

        cur.execute(query)

        conn.commit()

        print("✅ Tables successfully reset.")
        print("📌 IDs restarted from 1.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:")
        print(str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    reset_tables()