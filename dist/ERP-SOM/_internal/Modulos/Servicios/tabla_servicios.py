from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from datetime import datetime, date, timedelta
from Modulos.Servicios.date_utils import to_long_english_date
from api_client import BASE_URL, api_request


class TablaServiciosUI(BasePaginatedTable):

    def __init__(self, parent, on_back=None):
        super().__init__(parent, title="Servicios", on_back=on_back)

        # ============================================================
        # LISTA DE COLUMNAS (NO SE DIBUJAN AQUÍ)
        # ============================================================
        self.cols = [
            "consec", "tipo", "estado", "num_informe",
            "buque_contenedor", "cliente", "contacto", "detalle",
            "continente", "pais", "puerto",
            "operacion", "surveyor", "honorarios", "costo_operativo",
            "fecha_inicio", "hora_inicio",
            "fecha_fin", "hora_fin", "demoras", "duracion",
            "factura", "valor_factura", "fecha_factura",
            "terminos_pago", "fecha_vencimiento", "dias_vencido",
            "razon_cancelacion", "comentario_cancelacion"
        ]

        self.columnas_creadas = False

    # ===============================================
    # API PAGINADA REAL
    # ===============================================
    def load_data(self):

        # ============================================================
        # CREAR COLUMNAS SOLO LA PRIMERA VEZ
        # ============================================================
        if not self.columnas_creadas:
            self.table["columns"] = self.cols

            for col in self.cols:
                self.table.heading(col, text=col.replace("_", " ").title())
                self.table.column(col, width=140, anchor="center")

            self.columnas_creadas = True

        # ============================================================
        # PARAMETROS DE PAGINACIÓN Y FILTROS
        # ============================================================
        params = {
            "page": self.page,
            "page_size": self.page_size
        }

        if hasattr(self, "filtros"):
            params.update(self.filtros)

        # ============================================================
        # LLAMADA API
        # ============================================================
        resp = api_request(
            "GET",
            f"{BASE_URL}/servicios",
            params=params,
            timeout=15
        ).json()

        self.total_items = resp.get("total", 0)
        data = resp.get("data", [])

        # ============================================================
        # LIMPIAR TABLA Y CARGAR REGISTROS
        # ============================================================
        self.table.delete(*self.table.get_children())

        for row in data:

            # ========================================================
            # 🔢 CÁLCULO FECHA VENCIMIENTO Y DÍAS VENCIDO (UI ONLY)
            # ========================================================
            fecha_factura_raw = str(row.get("fecha_factura") or "").strip()
            terminos_pago_raw = str(row.get("terminos_pago") or "").strip()

            fecha_factura_ui = fecha_factura_raw
            fecha_vencimiento_ui = ""
            dias_vencido_ui = ""

            try:
                if fecha_factura_raw and terminos_pago_raw:

                    # Acepta "YYYY-MM-DD" o "YYYY-MM-DD HH:MM:SS"
                    fecha_factura_dt = datetime.strptime(
                        fecha_factura_raw[:10],
                        "%Y-%m-%d"
                    ).date()

                    # Termino pago: "30", "30.0", 30, etc.
                    terminos_pago_int = int(float(terminos_pago_raw))

                    fecha_venc_dt = fecha_factura_dt + timedelta(days=terminos_pago_int)

                    fecha_factura_ui = to_long_english_date(fecha_factura_dt)
                    fecha_vencimiento_ui = to_long_english_date(fecha_venc_dt)

                    dias_calc = (date.today() - fecha_venc_dt).days
                    dias_vencido_ui = dias_calc if dias_calc > 0 else 0

            except Exception:
                # Si algo falla, dejamos vacíos los calculados (sin romper la tabla)
                fecha_factura_ui = fecha_factura_raw
                fecha_vencimiento_ui = ""
                dias_vencido_ui = ""

            # ========================================================
            # INSERTAR FILA (UNA SOLA VEZ)
            # ========================================================
            vals = []

            for c in self.cols:
                if c == "fecha_factura":
                    vals.append(fecha_factura_ui)
                elif c == "fecha_vencimiento":
                    vals.append(fecha_vencimiento_ui)
                elif c in ("fecha_inicio", "fecha_fin"):
                    vals.append(to_long_english_date(row.get(c, "")))
                elif c == "dias_vencido":
                    vals.append(dias_vencido_ui)
                else:
                    vals.append(row.get(c, ""))

            self.table.insert("", "end", values=tuple(vals))

        # Actualizar texto de página
        self.lbl_page.config(text=f"Página {self.page}")
