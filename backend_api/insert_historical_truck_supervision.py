import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("HISTORICAL_DATABASE_URL")


REPORTS = [
    {
        "consec": 433,
        "cert_no": "2182-1505-2026",
        "vessel_name": "MV ASTRO ANTARES",
        "report_date": "2026-05-23",
        "arrival_date": "2026-05-23",
        "inspection_date": "2026-05-23",
        "supervision_completed_date": "2026-05-23",
        "flag_port_registry": "MARSHALL ISLANDS",
        "grt": "34624",
        "nrt": "19725",
        "imo_no": "9767065",
        "build_year": "2017",
        "captain": "Kovalyov Kostyantyn",
        "chief_officer": "Buryndin Andriy",
        "process_text": (
            "Se destacan cinco inspectores en la zona del Descanso de Puesto 4. "
            "Un inspector en Filtro 1 revisa boletas de El Surco, SPC, fichas y placas. "
            "Tres o cuatro inspectores por bodega identifican camiones de carga de maiz, "
            "registran bodega, ficha, transporte, hora de entrada y salida a tolva. "
            "Bodegas 2, 4 y 5: maiz amarillo; bodega 3: frijol de soya; bodega 1: DDGS."
        ),
        "findings_documental_text": (
            "Se identificaron inconsistencias documentales relacionadas con productos "
            "declarados en boletas, diferencias entre boletas El Surco/SPC y unidades devueltas."
        ),
        "findings_operational_text": (
            "Se mantuvo control operativo por ficha, guia y placa durante la supervision de descarga."
        ),
        "incidents_text": "Unidades devueltas por inconsistencias documentales y diferencias de producto declarado.",
    },
    {
        "consec": 429,
        "cert_no": "2176-2404-2026",
        "vessel_name": "MV PMS ENZIAN",
        "report_date": "2026-04-30",
        "arrival_date": "2026-04-30",
        "inspection_date": "2026-04-30",
        "supervision_completed_date": "2026-04-30",
        "flag_port_registry": "MARSHALL ISLANDS",
        "grt": "34619",
        "nrt": "20170",
        "imo_no": "9711420",
        "build_year": "2015",
        "captain": "SYDOROV SERGY",
        "chief_officer": "ROLIK DMYTRO",
        "process_text": (
            "Se destacan cinco inspectores en la zona del Descanso de Puesto 4. "
            "Un inspector en Filtro 1 revisa boletas de El Surco, SPC, fichas y placas. "
            "Inspectores por bodega registran ficha, transporte y horarios. "
            "Bodegas 1, 3 y 5: maiz amarillo; bodega 4: frijol de soya; bodega 2: DDGS."
        ),
        "findings_documental_text": (
            "Placa 159130: guia El Surco 1608 sin firma ni sello. Chofer 144308: "
            "presenta guia incorrecta. Guia El Surco 01256 sin sello ni firma. "
            "Placa 147480: guia El Surco 228 sin sello."
        ),
        "findings_operational_text": "Numeracion de guias El Surco atipicamente baja; se cuestionan rangos definidos.",
        "incidents_text": "Unidades devueltas por falta de sello y guias incorrectas.",
    },
    {
        "consec": 425,
        "cert_no": "2169-0704-2026",
        "vessel_name": "MV GREAT 61",
        "report_date": "2026-04-22",
        "arrival_date": "2026-04-22",
        "inspection_date": "2026-04-22",
        "supervision_completed_date": "2026-04-22",
        "flag_port_registry": "SINGAPORE",
        "grt": "34584",
        "nrt": "20215",
        "imo_no": "9731365",
        "build_year": "2015",
        "captain": "ALPER GULDU",
        "chief_officer": "MUSTAFA KETENCI",
        "process_text": (
            "Se destacan cinco inspectores en la zona del Descanso de Puesto 4. "
            "Un inspector en Filtro 1 revisa documentacion de El Surco, SPC, fichas y placas. "
            "Bodegas 2, 3 y 4: maiz amarillo; bodegas 1 y 5: frijol de soya."
        ),
        "findings_documental_text": (
            "Inconsistencias de informacion en nombres/datos. Placas 146889 y 178931 "
            "con diferencias entre boletas. Placas 18413, 162488, 138271, 169440 y 25194 "
            "con guias sin sello. Guia 7354 devuelta por nombres incorrectos y sin reingreso."
        ),
        "findings_operational_text": (
            "Falta de trazabilidad en reingresos. Chofer 168811 ingreso con boleta de entrada "
            "en lugar de boleta SPC. Ingreso excepcional de 15 camiones graneleros sin ficha."
        ),
        "incidents_text": (
            "Multiples devoluciones por documentacion incompleta o invalida, guia no reingresada, "
            "documentacion incorrecta e ingreso masivo excepcional sin ficha."
        ),
    },
    {
        "consec": 416,
        "cert_no": "2159-0203-2026",
        "vessel_name": "MV ULTRA UNITY",
        "report_date": "2026-07-03",
        "arrival_date": "2026-07-03",
        "inspection_date": "2026-07-03",
        "supervision_completed_date": "2026-07-03",
        "flag_port_registry": "Panama",
        "grt": "36278",
        "nrt": "21173",
        "imo_no": "1070179",
        "build_year": "2025",
        "captain": "Caalim Alexander Diaz",
        "chief_officer": "Mark Anthony Hanzon Saclauso",
        "process_text": (
            "Supervision de camiones de maiz amarillo, destilado y soya. Cinco inspectores "
            "en Descanso de Puesto 4; Filtro 1 revisa boletas, fichas y placas. "
            "Bodegas 1, 4 y 5: maiz amarillo; bodega 3: DDG; bodega 2: frijol de soya."
        ),
        "findings_documental_text": (
            "Inconsistencias en documentacion presentada por transportistas, principalmente "
            "boletas sin sello o firma, diferencias entre documentos y errores de informacion."
        ),
        "findings_operational_text": "Control operativo mediante guia de pesaje, guia El Surco, ficha y placa.",
        "incidents_text": "Unidades con documentacion incompleta o inconsistente durante la operacion.",
    },
    {
        "consec": 406,
        "cert_no": "2151-1102-2026",
        "vessel_name": "MV PAN ORION",
        "report_date": "2026-02-11",
        "arrival_date": "2026-02-10",
        "inspection_date": "2026-02-11",
        "supervision_completed_date": "2026-02-14",
        "flag_port_registry": "Panama",
        "grt": "36,551",
        "nrt": "21,565",
        "imo_no": "9855848",
        "build_year": "2020",
        "captain": "CHO SEONGHYEUN",
        "chief_officer": "OMONGOS KETH JOLLY VIER CALUNDOD",
        "process_text": (
            "Cinco inspectores ubicados en zona de descanso. Un filtro primario identifica "
            "fichas, boletas y placas antes de salida a cargar. Tres inspectores por bodega "
            "registran ingreso individual a bodega. Un inspector lleva tracking de informacion."
        ),
        "findings_documental_text": "Supervision de camiones mediante verificacion de guia de pesaje y guia El Surco.",
        "findings_operational_text": (
            "Maiz amarillo en bodegas 1, 3 y 4 por MANEJOS y AEGRA; destilado y soya "
            "controlados segun distribucion operativa del buque."
        ),
        "incidents_text": "No se registran incidentes criticos en la informacion historica cargada.",
    },
]


def ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vessel_truck_supervision_reports (
            id SERIAL PRIMARY KEY,
            cert_no TEXT UNIQUE,
            customer TEXT,
            port TEXT,
            country TEXT,
            report_date DATE,
            vessel_name TEXT,
            flag_port_registry TEXT,
            grt TEXT,
            nrt TEXT,
            imo_no TEXT,
            build_year TEXT,
            captain TEXT,
            chief_officer TEXT,
            arrival_date DATE,
            inspection_date DATE,
            supervision_completed_date DATE,
            process_text TEXT,
            conclusion_text TEXT,
            findings_documental_text TEXT,
            findings_operational_text TEXT,
            incidents_text TEXT,
            status TEXT DEFAULT 'Created',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    columns = {
        "cert_no": "TEXT",
        "customer": "TEXT",
        "port": "TEXT",
        "country": "TEXT",
        "report_date": "DATE",
        "vessel_name": "TEXT",
        "flag_port_registry": "TEXT",
        "grt": "TEXT",
        "nrt": "TEXT",
        "imo_no": "TEXT",
        "build_year": "TEXT",
        "captain": "TEXT",
        "chief_officer": "TEXT",
        "arrival_date": "DATE",
        "inspection_date": "DATE",
        "supervision_completed_date": "DATE",
        "process_text": "TEXT",
        "conclusion_text": "TEXT",
        "findings_documental_text": "TEXT",
        "findings_operational_text": "TEXT",
        "incidents_text": "TEXT",
        "status": "TEXT",
        "created_at": "TIMESTAMP DEFAULT NOW()",
        "updated_at": "TIMESTAMP DEFAULT NOW()",
    }
    cur.execute("ALTER TABLE vessel_truck_supervision_reports ADD COLUMN IF NOT EXISTS id SERIAL")
    for col, ddl in columns.items():
        cur.execute(f"ALTER TABLE vessel_truck_supervision_reports ADD COLUMN IF NOT EXISTS {col} {ddl}")
    cur.execute(
        """
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='public'
          AND table_name='vessel_truck_supervision_reports'
          AND constraint_type='PRIMARY KEY'
        LIMIT 1
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE vessel_truck_supervision_reports ADD PRIMARY KEY (id)")
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_vessel_truck_supervision_cert_no "
        "ON vessel_truck_supervision_reports(cert_no)"
    )


def main():
    if not DATABASE_URL:
        raise RuntimeError("HISTORICAL_DATABASE_URL is required")

    conn = psycopg2.connect(DATABASE_URL)
    result = []
    try:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=RealDictCursor)
        ensure_schema(cur)

        for report in REPORTS:
            conclusion = (
                "La operacion fue supervisada mediante control documental y operativo de camiones, "
                "verificando guias, fichas, placas y flujo de ingreso/salida conforme a los "
                "procedimientos aplicados para EL SURCO."
            )
            payload = {
                **report,
                "customer": "EL SURCO",
                "port": "Caldera",
                "country": "Costa Rica",
                "conclusion_text": conclusion,
                "status": "Created",
            }
            payload.pop("consec")

            cur.execute("SELECT id FROM vessel_truck_supervision_reports WHERE cert_no=%s", (report["cert_no"],))
            existing = cur.fetchone()
            if existing:
                report_id = existing["id"]
                cur.execute(
                    """
                    UPDATE vessel_truck_supervision_reports
                    SET customer=%(customer)s, port=%(port)s, country=%(country)s,
                        report_date=%(report_date)s, vessel_name=%(vessel_name)s,
                        flag_port_registry=%(flag_port_registry)s, grt=%(grt)s,
                        nrt=%(nrt)s, imo_no=%(imo_no)s, build_year=%(build_year)s,
                        captain=%(captain)s, chief_officer=%(chief_officer)s,
                        arrival_date=%(arrival_date)s, inspection_date=%(inspection_date)s,
                        supervision_completed_date=%(supervision_completed_date)s,
                        process_text=%(process_text)s, conclusion_text=%(conclusion_text)s,
                        findings_documental_text=%(findings_documental_text)s,
                        findings_operational_text=%(findings_operational_text)s,
                        incidents_text=%(incidents_text)s, status=%(status)s,
                        updated_at=NOW()
                    WHERE cert_no=%(cert_no)s
                    """,
                    payload,
                )
                action = "updated"
            else:
                cols = list(payload.keys())
                sql_cols = ", ".join(cols)
                sql_vals = ", ".join([f"%({c})s" for c in cols])
                cur.execute(
                    f"""
                    INSERT INTO vessel_truck_supervision_reports ({sql_cols}, created_at, updated_at)
                    VALUES ({sql_vals}, NOW(), NOW())
                    RETURNING id
                    """,
                    payload,
                )
                report_id = cur.fetchone()["id"]
                action = "inserted"

            cur.execute(
                """
                UPDATE servicios
                SET tipo='Buque',
                    cliente='EL SURCO',
                    buque_contenedor=%s,
                    continente='América',
                    pais='Costa Rica',
                    puerto='Caldera',
                    operacion='LOGISTICS SUPERVISION',
                    detalle='Truck Supervision',
                    status_informe='Created',
                    num_informe=%s
                WHERE consec=%s
                """,
                (report["vessel_name"], report["cert_no"], report["consec"]),
            )

            result.append({"cert_no": report["cert_no"], "id": report_id, "consec": report["consec"], "action": action})

        conn.commit()
        print(json.dumps({"ok": True, "reports": result}, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
