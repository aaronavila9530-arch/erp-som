import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("🧱 Creando tabla container_reports_flat...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS container_reports_flat (
            id SERIAL PRIMARY KEY,

            -- ===============================
            -- IDENTIDAD DEL INFORME
            -- ===============================
            report_code VARCHAR(30) NOT NULL,
            status VARCHAR(20) DEFAULT 'DRAFT',
            -- DRAFT | SUBMITTED | UNDER_REVIEW | APPROVED | REJECTED

            client_name VARCHAR(255) NOT NULL,
            job_reference VARCHAR(100),
            purpose_of_inspection VARCHAR(100),

            -- ===============================
            -- INSPECCIÓN
            -- ===============================
            inspection_date DATE NOT NULL,
            inspection_place VARCHAR(255),
            country VARCHAR(100),
            weather_conditions VARCHAR(100),

            surveyor_name VARCHAR(255),
            surveyor_company VARCHAR(255),

            -- ===============================
            -- CONTENEDOR
            -- ===============================
            container_number VARCHAR(20) NOT NULL,
            container_iso VARCHAR(10),
            container_size VARCHAR(10),
            container_owner VARCHAR(100),
            container_operator VARCHAR(100),
            seal_number VARCHAR(50),
            csc_status VARCHAR(50),
            container_condition VARCHAR(20),
            -- GOOD | FAIR | POOR

            -- ===============================
            -- DAÑO / HALLAZGO (1 por fila)
            -- ===============================
            damage_area VARCHAR(50),
            damage_description TEXT,
            severity VARCHAR(20),
            -- MINOR | MODERATE | SEVERE

            probable_cause VARCHAR(50),
            -- HANDLING | TRANSPORT | UNKNOWN

            damage_age VARCHAR(20),
            -- FRESH | OLD | UNDETERMINED

            structural BOOLEAN DEFAULT FALSE,
            affects_integrity BOOLEAN DEFAULT FALSE,

            -- ===============================
            -- FOTO (SIMPLIFICADO)
            -- ===============================
            link_picture TEXT,

            -- ===============================
            -- TEXTO DEL INFORME
            -- ===============================
            executive_summary TEXT,
            general_observations TEXT,
            assessment_opinion TEXT,
            conclusion TEXT,
            recommendations TEXT,

            -- ===============================
            -- SISTEMA
            -- ===============================
            created_by VARCHAR(100),
            reviewed_by VARCHAR(100),
            approved_by VARCHAR(100),

            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla container_reports_flat creada correctamente.")
    print("🚢 Módulo de informes de contenedor listo para integrarse.")


if __name__ == "__main__":
    main()
