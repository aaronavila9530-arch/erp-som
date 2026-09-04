import os
import sys

sys.path.insert(0, r"C:\Users\aaron\Documents\ERP-SOM\backend_api")

import database
from psycopg2.extras import RealDictCursor
from services.pdf.factura_preview_pdf import generar_factura_preview_pdf

INVOICE_NO = "00100001010000000012"
COMPANY = "MCI-CR"


def main():
    pdf_path = os.path.join("storage", "factura", "pdf", f"{INVOICE_NO}_MANDULEY_PREVIEW.pdf")
    pdf_path = generar_factura_preview_pdf(
        {
            "numero_documento": INVOICE_NO,
            "fecha_emision": "2026-09-01",
            "cliente": "Pandi Costa Rica, S,A",
            "buque_contenedor": "MANDULEY",
            "operacion": "DRAFT SURVEY / OFF HIRE BUNKER / WEATHER CONDITION",
            "periodo": "2026-08-16 a 2026-08-26",
            "moneda": "USD",
            "total": "5,586.44",
        },
        output_path=pdf_path,
    )
    conn = database.connect()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            UPDATE factura
               SET pdf_path = %s
             WHERE numero_factura = %s
               AND clave_electronica = %s
            """,
            (pdf_path, INVOICE_NO, "50601092600310196914700100001010000000012178086794"),
        )
        cur.execute(
            """
            UPDATE invoicing
               SET pdf_path = %s
             WHERE company_code = %s
               AND numero_documento = %s
            """,
            (pdf_path, COMPANY, INVOICE_NO),
        )
        conn.commit()
        print({"status": "ok", "pdf_path": pdf_path})
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
