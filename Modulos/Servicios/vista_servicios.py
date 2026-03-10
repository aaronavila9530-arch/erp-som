import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog
import requests
import csv
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas  # para exportar PDF
import io
from datetime import datetime, date, timedelta
from openpyxl import Workbook

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


class VistaServicios(tk.Frame):

    def __init__(self, parent, filtros, on_back):
        super().__init__(parent, bg="white")
        self.filtros = filtros
        self.on_back = on_back
        self.page = 1
        self.page_size = 50
        self.total_items = 0

        # ============================================================
        # KPI SUPERIOR (similar a imagen 2)
        # ============================================================
        self._build_kpis()

        # ============================================================
        # TOOLBAR (Ver, Demoras, Eliminar, Exportar)
        # ============================================================
        self._build_toolbar()

        # ============================================================
        # TABLA
        # ============================================================
        self._build_table()

        # ============================================================
        # PAGINACIÓN
        # ============================================================
        self._build_pagination()

        # ============================================================
        # CARGAR DATOS
        # ============================================================
        self.load_data()

    # ======================= TOP KPI BAR ===========================
    def _build_kpis(self):

        self.kpi_bar = tk.Frame(self, bg="white", height=60)
        self.kpi_bar.pack(fill="x")

        def box(color, titulo):
            f = tk.Frame(self.kpi_bar, bg=color, height=60)
            f.pack(side="left", fill="both", expand=True)
            f.pack_propagate(False)

            tk.Label(
                f,
                text=titulo,
                bg=color,
                fg="white",
                font=("Segoe UI", 10, "bold")
            ).pack(pady=(8, 0))

            lbl = tk.Label(
                f,
                text="0",
                bg=color,
                fg="white",
                font=("Segoe UI", 15, "bold")
            )
            lbl.pack()

            return lbl

        # KPIs (orden y colores)
        self.kpi_servicios    = box("#005DAA", "Servicios")
        self.kpi_facturado    = box("#0077C0", "Facturado")
        self.kpi_paises       = box("#009CD6", "Países")
        self.kpi_confirmados  = box("#03B5D1", "Confirmados")
        self.kpi_cancelados   = box("#0A4A6E", "Cancelados")
        self.kpi_operaciones  = box("#04C7BE", "Operaciones")


    def _crear_kpi(self, parent, titulo, valor, col, color):
        frame = tk.Frame(parent, bg=color, height=70)
        frame.grid(row=0, column=col, sticky="nsew")

        tk.Label(
            frame,
            text=titulo.upper(),
            fg="white",
            bg=color,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 0))

        label = tk.Label(
            frame,
            text=valor,
            fg="white",
            bg=color,
            font=("Segoe UI", 16, "bold")
        )
        label.pack(anchor="w", padx=10)

        return label

    # =====================================================================
    # TOOLBAR FINAL — COLORES PASTEL DEFINITIVOS
    # =====================================================================
    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg="white")
        toolbar.pack(fill="x", padx=10, pady=5)

        # =======================================================
        # BOTÓN VOLVER (blanco con borde)
        # =======================================================
        tk.Button(
            toolbar, text="⬅ Volver",
            command=self.on_back,
            bg="white", fg="black",
            relief="solid", borderwidth=1,
            font=("Segoe UI", 9, "bold"),
            padx=10, pady=2
        ).pack(side="left", padx=5)

        # =======================================================
        # BOTONES PASTEL CON COLORES DEFINIDOS
        # =======================================================
        botones = [
            ("Generar Consecutivo","#A8D5B5", self.marcar_confirmado),
            ("Editar servicio",  "#86A9D9", self.editar_servicio),
            ("Finalizar Servicio", "#C9B7D9", self.finalizar_servicio),
            ("Ver",              "#CDE0F7", self.ver_servicio),
            ("Demoras",          "#F7D08A", self.ver_demoras),
            ("Cancelar",         "#D99A9A", self.cancelar_servicio),
            ("Eliminar",         "#E6C6C6", self.eliminar),
        ]

        for text, color, cmd in botones:
            tk.Button(
                toolbar,
                text=text,
                command=cmd,
                bg=color,
                fg="black",
                activebackground=color,
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9, "bold"),
                padx=10, pady=2,
                width=15
            ).pack(side="left", padx=5)

        # =======================================================
        # MENÚ EXPORTAR (igual que antes)
        # =======================================================
        export_btn = ttk.Menubutton(toolbar, text="Exportar ▼", width=15)
        menu = tk.Menu(export_btn, tearoff=0)
        menu.add_command(label="Exportar a CSV", command=self.export_csv)
        menu.add_command(label="Exportar a PDF", command=self.export_pdf)
        menu.add_command(label="Exportar a XML", command=self.export_xml)
        menu.add_command(label="Exportar a Excel", command=self.export_excel)
        export_btn["menu"] = menu
        export_btn.pack(side="left", padx=5)
					    
    # =====================================================================
    # TABLA
    # =====================================================================
    def _build_table(self):
        frame = tk.Frame(self, bg="white")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        # =============================================================
        # COLUMNAS VISIBLES (las que SÍ deben mostrarse en la tabla)
        # =============================================================
        self.columnas = [
            "consec","tipo","estado","num_informe","buque_contenedor","cliente",
            "contacto","detalle","continente","pais","puerto","operacion","surveyor",
            "honorarios","costo_operativo","costo_tarjetas","fecha_inicio","hora_inicio","fecha_fin",
            "hora_fin","demoras","duracion","factura","valor_factura","fecha_factura",
            "terminos_pago","fecha_vencimiento","dias_vencido"
        ]

        # =============================================================
        # COLUMNAS OCULTAS (para popup VER, pero NO visibles en tabla)
        # =============================================================
        self.columnas_ocultas = [
            "_consec_real",
            "razon_cancelacion",
            "comentario_cancelacion"
        ]

        # Todas las columnas para Treeview (visibles + ocultas)
        all_columns = self.columnas + self.columnas_ocultas

        # Crear tabla
        self.table = ttk.Treeview(frame, columns=all_columns, show="headings", height=20)

        # =============================================================
        # TAG PARA FILAS CON COSTOS FALTANTES
        # =============================================================
        self.table.tag_configure(
            "costos_faltantes",
            background="#FFD6D6"  # rojo pastel
        )

        # Dibujar SOLO las columnas visibles
        for col in self.columnas:
            self.table.heading(col, text=col.replace("_", " ").title())
            self.table.column(col, width=160, anchor="center")

        # Ocultar las columnas de cancelación
        for col in self.columnas_ocultas:
            self.table.heading(col, text="")
            self.table.column(col, width=0, stretch=False)

        # Scrollbars
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.table.xview)

        self.table.configure(yscroll=v_scroll.set, xscroll=h_scroll.set)

        # Posicionamiento
        self.table.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Click derecho
        self.table.bind("<Button-3>", self._menu_contextual)

    # =====================================================================
    # PAGINACIÓN
    # =====================================================================
    def _build_pagination(self):
        pag = tk.Frame(self, bg="white")
        pag.pack(fill="x", padx=10, pady=5)

        ttk.Button(pag, text="Anterior", command=self.pagina_anterior).pack(side="left")
        ttk.Button(pag, text="Siguiente", command=self.pagina_siguiente).pack(side="left")

        self.lbl_page = tk.Label(pag, text="Página 1", bg="white")
        self.lbl_page.pack(side="left", padx=10)



    # ============================================================
    # HELPERS UI: FECHA VENCIMIENTO + DÍAS VENCIDO
    # ============================================================
    def _calc_factura_ui(self, row: dict):
        """
        UI ONLY:
        - fecha_factura -> MM/DD/YYYY
        - fecha_vencimiento = fecha_factura + terminos_pago
        - dias_vencido = hoy - fecha_vencimiento (nunca negativo)
        """
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

                terminos_pago_int = int(float(terminos_pago_raw))

                fecha_venc_dt = fecha_factura_dt + timedelta(days=terminos_pago_int)

                fecha_factura_ui = fecha_factura_dt.strftime("%m/%d/%Y")
                fecha_vencimiento_ui = fecha_venc_dt.strftime("%m/%d/%Y")

                dias_calc = (date.today() - fecha_venc_dt).days
                dias_vencido_ui = dias_calc if dias_calc > 0 else 0

        except Exception:
            pass

        return fecha_factura_ui, fecha_vencimiento_ui, dias_vencido_ui

    # =====================================================================
    # CARGAR DATOS
    # =====================================================================
    def load_data(self):

        params = {"page": self.page, "page_size": self.page_size}
        params.update(self.filtros)

        resp = requests.get(
            f"{BASE_URL}/servicios",
            params=params,
            timeout=15
        ).json()

        self.total_items = resp.get("total", 0)
        data = resp.get("data", [])

        # ============================================================
        # ALERTA SERVICIOS EN OPERACIÓN SIN COSTOS
        # ============================================================
        servicios_incompletos = []

        for r in data:

            estado = str(r.get("estado") or "").strip()

            honorarios = float(r.get("honorarios") or 0)
            costo_operativo = float(r.get("costo_operativo") or 0)
            costo_tarjetas = float(r.get("costo_tarjetas") or 0)

            if estado == "En Operación":

                if honorarios == 0 or costo_operativo == 0 or costo_tarjetas == 0:
                    servicios_incompletos.append(r.get("consec"))

        if servicios_incompletos:

            messagebox.showwarning(
                "Servicios incompletos",
                "Existen servicios en estado 'En Operación' con valores faltantes en:\n\n"
                "• Honorarios\n"
                "• Costo Operativo\n"
                "• Costo Tarjetas\n\n"
                "Por favor complételos antes de continuar."
            )

        # ============================================================
        # LIMPIAR TABLA
        # ============================================================
        self.table.delete(*self.table.get_children())

        for idx, row in enumerate(data, start=1):

            # ============================================================
            # CALCULAR CAMPOS UI DE FACTURA
            # ============================================================
            (
                fecha_factura_ui,
                fecha_vencimiento_ui,
                dias_vencido_ui
            ) = self._calc_factura_ui(row)

            values = []

            for col in self.table["columns"]:

                if col == "consec":
                    val = idx

                elif col == "_consec_real":
                    val = row.get("consec")

                elif col == "fecha_factura":
                    val = fecha_factura_ui

                elif col == "fecha_vencimiento":
                    val = fecha_vencimiento_ui

                elif col == "dias_vencido":
                    val = dias_vencido_ui

                elif col == "demoras":
                    val = self.format_demoras(row.get("demoras"))

                elif col == "duracion":
                    val = self.calcular_duracion(row)

                else:
                    val = row.get(col, "")

                values.append(val)

            # ============================================================
            # DETECTAR COSTOS EN 0 O VACÍOS SOLO EN OPERACIÓN
            # ============================================================
            estado = str(row.get("estado") or "").strip()

            honorarios = float(row.get("honorarios") or 0)
            costo_operativo = float(row.get("costo_operativo") or 0)
            costo_tarjetas = float(row.get("costo_tarjetas") or 0)

            if estado == "En Operación" and honorarios == 0 and costo_operativo == 0 and costo_tarjetas == 0:
                self.table.insert(
                    "",
                    "end",
                    values=values,
                    tags=("costos_faltantes",)
                )
            else:
                self.table.insert(
                    "",
                    "end",
                    values=values
                )

        self.lbl_page.config(text=f"Página {self.page}")

        # ============================================================
        # KPIs
        # ============================================================

        total_operaciones = len(data)

        total_confirmados = len([
            r for r in data if r.get("estado") == "Confirmado"
        ])

        total_cancelados = len([
            r for r in data if r.get("estado") == "Cancelado"
        ])

        total_servicios = len([
            r for r in data
            if r.get("estado") in ("Confirmado", "Finalizado")
        ])

        paises_unicos = {
            r.get("pais") for r in data if r.get("pais")
        }

        total_facturado = sum(
            float(r.get("valor_factura") or 0) for r in data
        )

        self.kpi_operaciones.config(text=str(total_operaciones))
        self.kpi_confirmados.config(text=str(total_confirmados))
        self.kpi_cancelados.config(text=str(total_cancelados))
        self.kpi_servicios.config(text=str(total_servicios))
        self.kpi_paises.config(text=str(len(paises_unicos)))
        self.kpi_facturado.config(text=f"${total_facturado:,.2f}")

    # =====================================================================
    # PAGINACIÓN MÉTODOS
    # =====================================================================
    def pagina_anterior(self):
        if self.page > 1:
            self.page -= 1
            self.load_data()

    def pagina_siguiente(self):
        max_page = (self.total_items // self.page_size) + 1
        if self.page < max_page:
            self.page += 1
            self.load_data()

    # =====================================================================
    # EXPORTAR
    # =====================================================================
    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return

        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.table["columns"])
            for row in self.table.get_children():
                writer.writerow(self.table.item(row)["values"])

        messagebox.showinfo("CSV", "Exportación exitosa.")

    def export_pdf(self):
        file = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not file:
            return

        pdf = canvas.Canvas(file)
        y = 800

        pdf.setFont("Helvetica", 10)
        pdf.drawString(20, y, ", ".join(self.table["columns"]))
        y -= 20

        for row in self.table.get_children():
            pdf.drawString(20, y, ", ".join(str(x) for x in self.table.item(row)["values"]))
            y -= 15

        pdf.save()
        messagebox.showinfo("PDF", "Exportación exitosa.")

    def export_xml(self):
        file = filedialog.asksaveasfilename(defaultextension=".xml")
        if not file:
            return

        root = ET.Element("Servicios")

        for row in self.table.get_children():
            item = ET.SubElement(root, "Servicio")
            for col, val in zip(self.table["columns"], self.table.item(row)["values"]):
                ET.SubElement(item, col).text = str(val)

        tree = ET.ElementTree(root)
        tree.write(file, encoding="utf-8")

        messagebox.showinfo("XML", "Exportación exitosa.")

    def export_excel(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not file:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Servicios"

        # Encabezados EXACTOS como la tabla
        columns = self.table["columns"]
        ws.append(columns)

        # Filas EXACTAS como se ven en la tabla
        for row_id in self.table.get_children():
            ws.append(self.table.item(row_id)["values"])

        # Ajuste automático de ancho
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max_len + 2

        wb.save(file)
        messagebox.showinfo("Excel", "Exportación a Excel exitosa.")


    # =====================================================================
    # CONTEXT-MENU
    # =====================================================================
    def _menu_contextual(self, event):
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Seleccionar fila", command=lambda: self._select_row(event))
        menu.add_command(label="Seleccionar todo", command=self._select_all)
        menu.add_separator()
        menu.add_command(label="Exportar CSV", command=self.export_csv)
        menu.add_command(label="Exportar PDF", command=self.export_pdf)
        menu.add_command(label="Exportar XML", command=self.export_xml)
        menu.add_command(label="Exportar Excel", command=self.export_excel)
        menu.post(event.x_root, event.y_root)

    def _select_row(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self.table.selection_set(row)

    def _select_all(self):
        for row in self.table.get_children():
            self.table.selection_add(row)

    # ============================================================
    # GENERAR CONSECUTIVO (antes Confirmar)
    # ============================================================
    def marcar_confirmado(self):

        item = self.table.focus()
        if not item:
            messagebox.showwarning(
                "Sin selección",
                "Debe seleccionar un servicio."
            )
            return

        valores = self.table.item(item, "values")

        try:
            idx_consec_real = self.table["columns"].index("_consec_real")
            consec = valores[idx_consec_real]
        except (ValueError, IndexError):
            messagebox.showerror(
                "Error crítico",
                "No se pudo determinar el consecutivo real."
            )
            return

        if not consec:
            messagebox.showerror(
                "Error crítico",
                "El consecutivo está vacío."
            )
            return

        try:
            consec = int(consec)
        except (TypeError, ValueError):
            messagebox.showerror(
                "Error crítico",
                f"Consecutivo inválido: {consec}"
            )
            return

        from Modulos.Servicios.Popup_servicios.popup_generar_consecutivo import PopupGenerarConsecutivo

        PopupGenerarConsecutivo(
            self,
            consec,
            valores,
            callback=self.refresh
        )


    # ============================================================
    # EDITAR SERVICIO
    # ============================================================
    def editar_servicio(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning(
                "Sin selección",
                "Debe seleccionar un servicio."
            )
            return

        valores = self.table.item(item, "values")

        try:
            idx_consec_real = self.table["columns"].index("_consec_real")
            consec = valores[idx_consec_real]
        except (ValueError, IndexError):
            messagebox.showerror(
                "Error crítico",
                "No se pudo determinar el consecutivo real del servicio."
            )
            return

        if not consec:
            messagebox.showerror(
                "Error crítico",
                "El consecutivo del servicio está vacío."
            )
            return

        try:
            consec = int(consec)
        except (TypeError, ValueError):
            messagebox.showerror(
                "Error crítico",
                f"Consecutivo inválido: {consec}"
            )
            return

        from Modulos.Servicios.Popup_servicios.popup_editar_servicio import PopupEditarServicio
        PopupEditarServicio(self, consec, on_success=self.refresh)

    # ============================================================
    # FINALIZAR SERVICIO
    # ============================================================

    def finalizar_servicio(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning(
                "Sin selección",
                "Debe seleccionar un servicio."
            )
            return

        valores = self.table.item(item, "values")

        idx_consec_real = self.table["columns"].index("_consec_real")
        consec = valores[idx_consec_real]

        idx_honorarios = self.table["columns"].index("honorarios")
        idx_costos = self.table["columns"].index("costo_operativo")

        honorarios = valores[idx_honorarios]
        costos = valores[idx_costos]

        # 🔴 VALIDACIÓN OBLIGATORIA
        if not honorarios or not costos:
            messagebox.showerror(
                "Datos incompletos",
                "Debe ingresar Honorarios y Costo Operativo antes de finalizar."
            )
            return

        from Modulos.Servicios.Popup_servicios.popup_finalizar_servicio import PopupFinalizarServicio
        PopupFinalizarServicio(self, consec, on_success=self.refresh)

    # ============================================================
    # POPUP: VER SERVICIO (Versión real, no placeholder)
    # ============================================================
    def ver_servicio(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning("Sin selección", "Debe seleccionar un servicio.")
            return

        valores = self.table.item(item, "values")
        idx_consec_real = self.table["columns"].index("_consec_real")
        consec = valores[idx_consec_real]

        from Modulos.Servicios.Popup_servicios.popup_ver_servicio import PopupVerServicio
        PopupVerServicio(self, valores)

    # ============================================================
    # POPUP: DEMORAS
    # ============================================================
    def ver_demoras(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning("Sin selección", "Debe seleccionar un servicio.")
            return

        valores = self.table.item(item, "values")
        idx_consec_real = self.table["columns"].index("_consec_real")
        consec = valores[idx_consec_real]

        from Modulos.Servicios.Popup_servicios.popup_demoras import PopupDemoras
        PopupDemoras(self, consec, on_success=self.actualizar_fila)

    def actualizar_fila(self):
        """Actualiza una sola fila después de guardar demoras."""
        self.refresh()


    # ============================================================
    # POPUP: Cancelar
    # ============================================================

    def cancelar_servicio(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning("Sin selección", "Debe seleccionar un servicio.")
            return

        fila = self.table.item(item, "values")
        consec = fila[0]  # primera columna de la tabla

        from Modulos.Servicios.Popup_servicios.popup_cancelar_servicio import PopupCancelarServicio
        PopupCancelarServicio(self, consec, on_success=lambda: self.refresh())


    # ============================================================
    # POPUP: Eliminar
    # ============================================================

    def eliminar(self):
        item = self.table.focus()
        if not item:
            messagebox.showwarning("Sin selección", "Debe seleccionar un servicio.")
            return

        valores = self.table.item(item, "values")
        idx_consec_real = self.table["columns"].index("_consec_real")
        consec = valores[idx_consec_real]  # primer campo de la tabla

        # Popup de confirmación
        respuesta = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Está seguro de eliminar el servicio con consec {consec}?"
        )

        if not respuesta:
            return  # Cancelado por el usuario

        # Realizar eliminación en la API
        from api_client import delete_servicio
        resultado = delete_servicio(consec)

        # Verificar respuesta
        if resultado.get("status") == "ok":
            messagebox.showinfo("Eliminado", f"Servicio {consec} eliminado correctamente.")
            
            # Recargar tabla
            self.refresh()

        else:
            error_msg = resultado.get("error", "Error desconocido.")
            messagebox.showerror("Error", f"No se pudo eliminar el servicio:\n{error_msg}")


    # ============================================================
    # REFRESCAR TABLA DESPUÉS DE UNA ACCIÓN
    # ============================================================
    def refresh(self):
        """Vuelve a cargar los datos en la tabla usando los filtros actuales."""

        # 1. Limpiar tabla
        self.table.delete(*self.table.get_children())

        # 2. Llamar API
        import requests
        from api_client import BASE_URL

        params = self.filtros.copy()
        params["page"] = self.page
        params["page_size"] = 50

        try:
            r = requests.get(
                f"{BASE_URL}/servicios",
                params=params,
                timeout=15
            )
            data = r.json().get("data", [])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar los servicios:\n{e}"
            )
            return

        # 3. Insertar filas (incluye _consec_real correctamente)
        columnas_totales = self.columnas + self.columnas_ocultas

        for item in data:
            valores = []

            for col in columnas_totales:

                if col == "_consec_real":
                    valores.append(item.get("consec"))

                elif col == "demoras":
                    valores.append(self.format_demoras(item.get("demoras")))

                elif col == "duracion":
                    valores.append(self.calcular_duracion(item))

                else:
                    valores.append(item.get(col, ""))

            # ============================================================
            # DETECTAR COSTOS FALTANTES (MISMA LÓGICA QUE load_data)
            # ============================================================
            estado = str(item.get("estado") or "").strip()

            honorarios = float(item.get("honorarios") or 0)
            costo_operativo = float(item.get("costo_operativo") or 0)
            costo_tarjetas = float(item.get("costo_tarjetas") or 0)

            if estado == "En Operación" and honorarios == 0 and costo_operativo == 0 and costo_tarjetas == 0:
                self.table.insert(
                    "",
                    "end",
                    values=valores,
                    tags=("costos_faltantes",)
                )
            else:
                self.table.insert(
                    "",
                    "end",
                    values=valores
                )

        # 4. Página
        if hasattr(self, "label_pagina"):
            self.label_pagina.config(text=f"Página {self.page}")


        # ============================================================
        # 5. REFRESCAR KPIs (NUEVO — AQUÍ ESTABA FALTANDO)
        # ============================================================

        # Operaciones = total líneas
        total_operaciones = len(data)

        # Confirmados
        total_confirmados = len([
            r for r in data if r.get("estado") == "Confirmado"
        ])

        # Cancelados
        total_cancelados = len([
            r for r in data if r.get("estado") == "Cancelado"
        ])

        # Servicios = Confirmados + Finalizados
        total_servicios = len([
            r for r in data
            if r.get("estado") in ("Confirmado", "Finalizado")
        ])

        # Países únicos
        paises_unicos = {
            r.get("pais") for r in data if r.get("pais")
        }

        # Facturado
        total_facturado = sum(
            float(r.get("valor_factura") or 0) for r in data
        )

        # Actualizar KPIs
        self.kpi_operaciones.config(text=str(total_operaciones))
        self.kpi_confirmados.config(text=str(total_confirmados))
        self.kpi_cancelados.config(text=str(total_cancelados))
        self.kpi_servicios.config(text=str(total_servicios))
        self.kpi_paises.config(text=str(len(paises_unicos)))
        self.kpi_facturado.config(text=f"${total_facturado:,.2f}")

    # ============================================================
    # FORMATO / PARSE DE DEMORAS Y DURACION
    # ============================================================
    def format_demoras(self, minutos):
        """Convierte minutos (int/str) a '0D 4H 0M'."""
        try:
            m = int(float(minutos))
        except (ValueError, TypeError):
            return ""

        if m < 0:
            m = 0

        dias = m // (24 * 60)
        horas = (m % (24 * 60)) // 60
        mins = m % 60
        return f"{dias}D {horas}H {mins}M"

    def parse_demoras_to_minutes(self, valor):
        """
        Acepta:
        - 240 (int)
        - "240" (str)
        - "0D 4H 0M" (str)
        Devuelve minutos (int). Si no puede, devuelve 0.
        """
        if valor is None:
            return 0

        # Caso numérico directo
        try:
            return int(float(valor))
        except (ValueError, TypeError):
            pass

        # Caso texto tipo "0D 4H 0M"
        try:
            s = str(valor).upper().replace(" ", "")
            # Esperado: "0D4H0M"
            d = h = m = 0

            if "D" in s:
                d_part, s = s.split("D", 1)
                d = int(d_part) if d_part else 0
            if "H" in s:
                h_part, s = s.split("H", 1)
                h = int(h_part) if h_part else 0
            if "M" in s:
                m_part = s.split("M", 1)[0]
                m = int(m_part) if m_part else 0

            return (d * 24 * 60) + (h * 60) + m
        except Exception:
            return 0

    def calcular_duracion(self, item):
        """
        Duración = (fecha_fin + hora_fin) - (fecha_inicio + hora_inicio) - demoras
        Retorna string formateado 'XD YH ZM'. Si faltan fechas/horas, retorna "".
        """
        from datetime import datetime

        f_ini = (item.get("fecha_inicio") or "").strip()
        h_ini = (item.get("hora_inicio") or "").strip()
        f_fin = (item.get("fecha_fin") or "").strip()
        h_fin = (item.get("hora_fin") or "").strip()

        if not (f_ini and h_ini and f_fin and h_fin):
            return ""

        def _parse_dt(fecha: str, hora: str):
            # Soporta "HH:MM" y "HH:MM:SS"
            hora = (hora or "").strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(f"{fecha} {hora}", fmt)
                except ValueError:
                    continue
            return None

        ini = _parse_dt(f_ini, h_ini)
        fin = _parse_dt(f_fin, h_fin)
        if not ini or not fin:
            return ""

        total_min = int((fin - ini).total_seconds() // 60)
        if total_min < 0:
            total_min = 0

        demora_min = self.parse_demoras_to_minutes(item.get("demoras"))
        duracion_min = total_min - demora_min
        if duracion_min < 0:
            duracion_min = 0

        return self.format_demoras(duracion_min)
