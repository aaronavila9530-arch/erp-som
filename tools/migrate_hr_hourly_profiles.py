import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend_api")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import connect
from routers.hr_ot_log import _ensure_ot_log_schema


PROFILES = [
    {
        "match": "%manfred%",
        "jornada": "POR HORA",
        "salario": 600000,
        "horas": 150,
    },
    {
        "match": "%erasmo%",
        "jornada": "POR HORA",
        "salario": 425000,
        "horas": 60,
    },
]


def main():
    conn = connect()
    try:
        _ensure_ot_log_schema(conn)
        cur = conn.cursor()
        updated = []
        for profile in PROFILES:
            cur.execute(
                """
                UPDATE empleados
                SET jornada = %s,
                    salario = %s,
                    pago = COALESCE(NULLIF(pago, ''), 'MENSUAL'),
                    horas_contratadas = %s
                WHERE lower(concat_ws(' ', nombre, apellidos)) LIKE %s
                  AND COALESCE(estado, 'Activo') = 'Activo'
                RETURNING id, usuario, nombre, apellidos, jornada, salario, horas_contratadas
                """,
                (
                    profile["jornada"],
                    profile["salario"],
                    profile["horas"],
                    profile["match"],
                ),
            )
            updated.extend(cur.fetchall() or [])
        conn.commit()
        print(f"Updated employees: {len(updated)}")
        for row in updated:
            print(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
