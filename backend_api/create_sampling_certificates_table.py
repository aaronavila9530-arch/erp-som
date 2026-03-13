import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def create_table():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""

    CREATE TABLE IF NOT EXISTS sampling_certificates (

        id SERIAL PRIMARY KEY,

        report_no TEXT,
        port TEXT,
        country TEXT,
        customer TEXT,

        certificate_no TEXT,
        vessel TEXT,
        date TEXT,
        place TEXT,
        cargo TEXT,

        holds_inspected TEXT,

        hold_1_seal TEXT,
        hold_2_seal TEXT,
        hold_3_seal TEXT,
        hold_4_seal TEXT,
        hold_5_seal TEXT,
        hold_6_seal TEXT,
        hold_7_seal TEXT,
        hold_8_seal TEXT,
        hold_9_seal TEXT,
        hold_10_seal TEXT,

        observations TEXT,

        closing_date TEXT,
        closing_time TEXT,

        master TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        status TEXT DEFAULT 'draft'

    );

    """)

    conn.commit()
    cur.close()
    conn.close()

    print("TABLE sampling_certificates CREATED SUCCESSFULLY")


if __name__ == "__main__":
    create_table()