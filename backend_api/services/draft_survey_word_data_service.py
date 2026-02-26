from psycopg2.extras import RealDictCursor


def get_draft_word_data_by_report_number(
    conn,
    draft_report_number: str
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT *
            FROM draft_survey_word_reports
            WHERE draft_report_number = %s
        """, (draft_report_number,))

        return cur.fetchone()

    finally:
        cur.close()