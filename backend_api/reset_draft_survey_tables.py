import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():

    print("Connecting to database...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        print("Deleting Draft Survey data...")

        # =====================================================
        # DELETE DATA (ORDER IMPORTANT FOR FK)
        # =====================================================

        cur.execute("DELETE FROM draft_survey_ballast;")
        print("draft_survey_ballast cleared")

        cur.execute("DELETE FROM draft_survey_word_report;")
        print("draft_survey_word_report cleared")

        cur.execute("DELETE FROM draft_survey;")
        print("draft_survey cleared")

        cur.execute("DELETE FROM general_draft_survey;")
        print("general_draft_survey cleared")

        # =====================================================
        # RESET SEQUENCES
        # =====================================================

        print("Resetting sequences...")

        cur.execute("ALTER SEQUENCE draft_survey_ballast_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE draft_survey_word_report_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE draft_survey_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE general_draft_survey_id_seq RESTART WITH 1;")

        conn.commit()

        print("✅ Draft Survey tables reset successfully")

    except Exception as e:

        conn.rollback()
        print("❌ ERROR:", e)

    finally:

        cur.close()
        conn.close()
        print("Connection closed")


if __name__ == "__main__":
    main()