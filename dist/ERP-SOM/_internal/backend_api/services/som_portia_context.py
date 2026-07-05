from datetime import datetime


def _fetch_one(cursor, query, params=None):
    try:
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        if not row:
            return None
        return row[0] if len(row) == 1 else row
    except Exception:
        try:
            cursor.connection.rollback()
        except Exception:
            pass
        return None


def _fetch_all(cursor, query, params=None):
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall() or []
    except Exception:
        try:
            cursor.connection.rollback()
        except Exception:
            pass
        return []


def _money(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def build_som_portia_context(db):
    cursor = db.cursor()
    year = datetime.now().year

    servicios = {
        "total": _fetch_one(cursor, "SELECT COUNT(*) FROM servicios"),
        "actual_year": _fetch_one(
            cursor,
            """
            SELECT COUNT(*)
            FROM servicios
            WHERE COALESCE(fecha_inicio::text, num_informe::text, '') LIKE %s
               OR RIGHT(COALESCE(num_informe::text, ''), 4) = %s
            """,
            (f"%{year}%", str(year)),
        ),
        "finalizados": _fetch_one(
            cursor,
            "SELECT COUNT(*) FROM servicios WHERE UPPER(COALESCE(estado,'')) = 'FINALIZADO'",
        ),
        "pendientes_factura": _fetch_one(
            cursor,
            """
            SELECT COUNT(*)
            FROM servicios
            WHERE UPPER(COALESCE(estado,'')) = 'FINALIZADO'
              AND COALESCE(factura::text, '') = ''
            """,
        ),
        "valor_factura_total": _money(
            _fetch_one(cursor, "SELECT COALESCE(SUM(valor_factura),0) FROM servicios")
        ),
    }

    finanzas = {
        "facturado_total": _money(
            _fetch_one(cursor, "SELECT COALESCE(SUM(total),0) FROM invoicing")
        ),
        "cuentas_por_cobrar": _money(
            _fetch_one(cursor, "SELECT COALESCE(SUM(saldo_pendiente),0) FROM collections")
        ),
        "pagos_recibidos": _money(
            _fetch_one(cursor, "SELECT COALESCE(SUM(monto),0) FROM incoming_payments")
        ),
        "cuentas_por_pagar_pendientes": _money(
            _fetch_one(
                cursor,
                """
                SELECT COALESCE(SUM(balance),0)
                FROM payment_obligations
                WHERE UPPER(COALESCE(status,'')) IN ('PENDING','PARTIAL')
                """,
            )
        ),
    }

    comercial = {
        "cotizaciones": _fetch_one(cursor, "SELECT COUNT(*) FROM public.cotizaciones"),
        "cotizaciones_aprobadas": _fetch_one(
            cursor,
            """
            SELECT COUNT(*)
            FROM public.cotizaciones
            WHERE UPPER(COALESCE(status,'')) = 'APROBADO'
            """,
        ),
        "precios_activos": _fetch_one(
            cursor,
            """
            SELECT COUNT(*)
            FROM servicios_precios
            WHERE COALESCE(activo, TRUE) = TRUE
            """,
        ),
    }

    master_data = {
        "clientes": _fetch_one(cursor, "SELECT COUNT(*) FROM cliente"),
        "proveedores": _fetch_one(cursor, "SELECT COUNT(*) FROM proveedor"),
        "empleados": _fetch_one(cursor, "SELECT COUNT(*) FROM empleados"),
        "surveyors": _fetch_one(cursor, "SELECT COUNT(*) FROM surveyor"),
        "paises": _fetch_one(cursor, "SELECT COUNT(*) FROM pais"),
        "puertos": _fetch_one(cursor, "SELECT COUNT(*) FROM puerto"),
    }

    informes = {
        "container_reports": _fetch_one(cursor, "SELECT COUNT(*) FROM container_reports"),
        "grain_sampling": _fetch_one(cursor, "SELECT COUNT(*) FROM vessel_grain_sampling"),
        "truck_supervision": _fetch_one(cursor, "SELECT COUNT(*) FROM vessel_truck_supervision"),
        "draft_survey": _fetch_one(cursor, "SELECT COUNT(*) FROM draft_survey"),
        "bunker": _fetch_one(cursor, "SELECT COUNT(*) FROM vessel_bunker_reports"),
        "crane": _fetch_one(cursor, "SELECT COUNT(*) FROM vessel_crane_inspection_reports"),
    }

    top_clientes_ar = [
        {"cliente": row[0], "saldo": _money(row[1])}
        for row in _fetch_all(
            cursor,
            """
            SELECT nombre_cliente, COALESCE(SUM(saldo_pendiente),0) saldo
            FROM collections
            GROUP BY nombre_cliente
            ORDER BY saldo DESC
            LIMIT 8
            """,
        )
    ]

    actividad_puertos = [
        {"pais": row[0], "puerto": row[1], "servicios": int(row[2] or 0)}
        for row in _fetch_all(
            cursor,
            """
            SELECT pais, puerto, COUNT(*) total
            FROM servicios
            WHERE COALESCE(puerto,'') <> ''
            GROUP BY pais, puerto
            ORDER BY total DESC
            LIMIT 10
            """,
        )
    ]

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "year": year,
        "servicios": servicios,
        "finanzas": finanzas,
        "comercial": comercial,
        "master_data": master_data,
        "informes": informes,
        "top_clientes_ar": top_clientes_ar,
        "actividad_puertos": actividad_puertos,
    }
