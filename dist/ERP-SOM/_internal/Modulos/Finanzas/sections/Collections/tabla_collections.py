import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from openpyxl import Workbook

from api_client import BASE_URL, api_request
from Modulos.Finanzas.date_utils import to_long_english_date
from Modulos.Finanzas.export_formatting import normalize_invoice_text_columns
from Modulos.Finanzas.sections.Collections.popups.popup_disputa import PopupDisputa
from Modulos.Finanzas.sections.Collections.popups.popup_pago import PopupPago
from Modulos.Finanzas.sections.Collections.docs.estado_cuenta_word import generar_estado_cuenta_word
from Modulos.Finanzas.sections.Collections.popups.popup_estado_cuenta import PopupEstadoCuenta

try:
    from Modulos.Finanzas.sections.Collections.docs.estado_cuenta_pdf import generar_estado_cuenta_pdf
except Exception:
    from Modulos.Finanzas.sections.Collections.docs import estado_cuenta_pdf as _estado_cuenta_pdf
    generar_estado_cuenta_pdf = (
        getattr(_estado_cuenta_pdf, "generar_estado_cuenta_pdf", None)
        or getattr(_estado_cuenta_pdf, "generar_estado_cuenta", None)
        or getattr(_estado_cuenta_pdf, "generar_pdf", None)
        or getattr(_estado_cuenta_pdf, "build_pdf", None)
    )
    if not callable(generar_estado_cuenta_pdf):
        raise


class TablaCollections(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.page = 1
        self.page_size = 50
        self.total_items = 0
        self.filtros = {}

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        actions = tk.Frame(self)
        actions.pack(fill="x", pady=5)

        ttk.Button(actions, text="📄 Ver factura", command=self._ver_factura).pack(side="left", padx=5)
        ttk.Button(actions, text="⚠ Disputar", command=self._disputar).pack(side="left", padx=5)
        ttk.Button(actions, text="💰 Aplicar pago / NC", command=self._pago).pack(side="left", padx=5)

        ttk.Button(
            actions,
            text="📄 Generar estado de cuenta",
            command=self._estado_cuenta
        ).pack(side="right", padx=5)

        export_btn = ttk.Menubutton(actions, text="📤 Exportar ▼", direction="below")
        export_btn.pack(side="right", padx=10)

        export_menu = tk.Menu(export_btn, tearoff=0)
        export_menu.add_command(label="Exportar CSV", command=self._export_csv)
        export_menu.add_command(label="Exportar Excel", command=self._export_excel)
        export_menu.add_separator()
        export_menu.add_command(label="Exportar PDF (Estado de Cuenta)", command=self._export_pdf)
        export_btn["menu"] = export_menu

        cols = (
            "codigo_cliente", "nombre_cliente",
            "tipo_factura", "tipo_documento", "numero_documento",
            "fecha_emision", "dias_credito", "fecha_vencimiento", "aging",
            "moneda",
            "total_factura", "saldo_pendiente",
            "num_informe", "buque", "operacion", "periodo",
            "estado", "disputada"
        )

        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            height=18
        )

        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=135, anchor="center")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # ================= PAGINACIÓN =================
        pag = tk.Frame(self, height=48)
        pag.pack(fill="x", side="bottom")
        pag.pack_propagate(False)

        ttk.Button(
                pag,
                text="◀ Anterior",
                width=14,
                command=self._prev
        ).pack(side="left", padx=6, pady=4, fill="y", expand=True)

        self.lbl_page = tk.Label(
                pag,
                text="Página 1",
                font=("Segoe UI", 10),
                anchor="center"
        )
        self.lbl_page.pack(side="left", padx=12, fill="y", expand=True)

        ttk.Button(
                pag,
                text="Siguiente ▶",
                width=14,
                command=self._next
        ).pack(side="left", padx=6, pady=4, fill="y", expand=True)


        # ================= ESTILOS DE FILAS =================
        self.tree.tag_configure(
            "overdue",
            background="#FADADD"  # rojo pastel
        )


    # ============================================================
    # DATA
    # ============================================================
    def buscar(self, filtros, on_kpis=None):
        self.filtros = filtros
        self.page = 1
        self._load_data(on_kpis)

    def _load_data(self, on_kpis=None):

        self.tree.delete(*self.tree.get_children())

        params = {
            **{k: v for k, v in self.filtros.items() if v is not None},
            "page": self.page,
            "page_size": self.page_size
        }

        try:
            r = api_request("GET", f"{BASE_URL}/collections/search", params=params, timeout=20)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar Collections\n\n{e}")
            return

        data = payload.get("data", [])
        self.total_items = payload.get("total", 0)

        data.sort(key=lambda x: int(x.get("aging_dias") or 0), reverse=True)

        for row in data:

            aging = int(row.get("aging_dias") or 0)

            tag = ()
            if aging > 1:
                tag = ("overdue",)

            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("codigo_cliente"),
                    row.get("nombre_cliente"),
                    row.get("tipo_factura"),
                    row.get("tipo_documento"),
                    row.get("numero_documento"),
                    to_long_english_date(row.get("fecha_emision")),
                    row.get("dias_credito"),
                    to_long_english_date(row.get("fecha_vencimiento")),
                    row.get("aging_dias"),
                    row.get("moneda"),
                    row.get("total"),
                    row.get("saldo_pendiente"),
                    row.get("num_informe"),
                    row.get("buque_contenedor"),
                    row.get("operacion"),
                    row.get("periodo_operacion"),
                    row.get("estado_factura"),
                    row.get("disputada")
                ),
                tags=tag
            )

        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
        self.lbl_page.config(text=f"Página {self.page} de {total_pages}")

        # ============================================================
        # KPIs — SOLO LO MOSTRADO EN PANTALLA
        # ============================================================
        total_ar = 0.0
        current = 0.0
        overdue = 0.0
        over_90 = 0.0

        for row in data:
            saldo = float(row.get("saldo_pendiente") or 0)
            aging = int(row.get("aging_dias") or 0)

            total_ar += saldo

            if aging < 1:
                current += saldo
            else:
                overdue += saldo

            if aging > 90:
                over_90 += saldo

        if on_kpis:
            on_kpis({
                "total_ar": total_ar,
                "current": current,
                "overdue": overdue,
                "over_90": over_90
            })

    # ============================================================
    # ESTADO DE CUENTA  ✅ ÚNICO MÉTODO MODIFICADO
    # ============================================================
    def _estado_cuenta(self):

        if not self.tree.get_children():
            messagebox.showwarning(
                "Estado de cuenta",
                "No hay información cargada para generar el estado de cuenta"
            )
            return

        facturas = []
        for item in self.tree.get_children():
            v = self.tree.item(item)["values"]
            facturas.append({
                "codigo_cliente": v[0],
                "nombre_cliente": v[1],
                "tipo_documento": v[3],
                "numero_documento": v[4],
                "fecha_emision": v[5],
                "dias_credito": v[6],
                "fecha_vencimiento": v[7],
                "aging_dias": v[8],
                "total": v[10],
                "saldo_pendiente": v[11],
                "num_informe": v[12],
                "buque_contenedor": v[13],
                "operacion": v[14],
                "estado_factura": v[16]
            })

        nombre_cliente = facturas[0]["nombre_cliente"]

        total_ar = 0.0
        overdue = 0.0
        buckets = {
            "CURRENT": 0.0,
            "1-30": 0.0,
            "31-60": 0.0,
            "61-90": 0.0,
            "90+": 0.0
        }

        for f in facturas:

            tipo = f.get("tipo_documento")
            estado = f.get("estado_factura")
            aging = int(f.get("aging_dias") or 0)

            if tipo == "FACTURA":
                monto = float(f.get("saldo_pendiente") or 0)
            elif tipo == "NOTA_CREDITO" and estado != "APLICADA":
                monto = float(f.get("total") or 0)
            else:
                continue

            total_ar += monto

            if aging <= 0:
                buckets["CURRENT"] += monto
            elif aging <= 30:
                buckets["1-30"] += monto
                overdue += monto
            elif aging <= 60:
                buckets["31-60"] += monto
                overdue += monto
            elif aging <= 90:
                buckets["61-90"] += monto
                overdue += monto
            else:
                buckets["90+"] += monto
                overdue += monto

        resumen_kpis = {
            "total_ar": total_ar,
            "overdue": overdue,
            "buckets": buckets
        }

        # ========================================================
        # CALLBACK – CONTRATO 100 % ALINEADO CON EL POPUP
        # ========================================================
        def _on_confirm(idioma, formato, datos_bancarios):

            if formato == "PDF":
                generar_estado_cuenta_pdf(
                    idioma=idioma,
                    cliente=nombre_cliente,
                    resumen_kpis=resumen_kpis,
                    facturas=facturas,
                    datos_bancarios=datos_bancarios
                )
            else:
                generar_estado_cuenta_word(
                    idioma=idioma,
                    cliente=nombre_cliente,
                    resumen_kpis=resumen_kpis,
                    facturas=facturas,
                    datos_bancarios=datos_bancarios
                )

            return True  # 🔑 permite que el popup se cierre

        PopupEstadoCuenta(self, on_confirm=_on_confirm)

    # ============================================================
    # RESTO DEL ARCHIVO (SIN CAMBIOS)
    # ============================================================

    def _ver_factura(self):

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una factura")
            return

        row = self.tree.item(selected[0])["values"]

        tipo_factura = row[2]          # ELECTRONICA / MANUAL
        tipo_documento = row[3]        # FACTURA / NOTA_CREDITO
        numero_documento = row[4]

        if tipo_documento != "FACTURA":
            messagebox.showinfo(
                "Información",
                "Solo es posible visualizar Facturas"
            )
            return

        # ================= FACTURA ELECTRÓNICA =================
        if tipo_factura == "ELECTRONICA":
            messagebox.showinfo(
                "Factura electrónica",
                "Para ver la factura electrónica debe dirigirse a GTI."
            )
            return

        # ================= FACTURA MANUAL =================
        pdf_path = f"/tmp/pdf/Factura_{numero_documento}.pdf"

        try:
            import os
            import webbrowser

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"No se encontró el archivo:\n{pdf_path}")

            webbrowser.open(pdf_path)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la factura\n\n{e}"
            )

    def _disputar(self):

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una factura")
            return

        row = self.tree.item(selected[0])["values"]

        tipo_documento = row[3]

        if tipo_documento != "FACTURA":
            messagebox.showwarning(
                "No permitido",
                "Solo se pueden disputar Facturas"
            )
            return

        PopupDisputa(
            self,
            row_data=row,
            on_success=lambda: self._load_data()
        )

    def _pago(self):

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una factura")
            return

        row = self.tree.item(selected[0])["values"]

        tipo_documento = row[3]
        estado = row[16]

        if tipo_documento != "FACTURA":
            messagebox.showwarning(
                "No permitido",
                "Solo se puede aplicar pago a Facturas"
            )
            return

        if estado not in ("PENDIENTE", "VENCIDA", "PENDIENTE_PAGO"):
            messagebox.showwarning(
                "No permitido",
                "La factura no tiene saldo pendiente"
            )
            return

        PopupPago(
            self,
            row_data=row,
            on_success=lambda: self._load_data()
        )

    def _next(self):

        total_pages = max(
            1,
            (self.total_items + self.page_size - 1) // self.page_size
        )

        if self.page < total_pages:
            self.page += 1
            self._load_data()

    def _prev(self):

        if self.page > 1:
            self.page -= 1
            self._load_data()

    def _export_csv(self):

        if not self.tree.get_children():
            messagebox.showwarning("Exportar", "No hay datos para exportar")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        headers = self.tree["columns"]

        try:
            with open(path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item)["values"])

            messagebox.showinfo(
                "Exportar",
                "Archivo CSV generado correctamente"
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _export_excel(self):

        if not self.tree.get_children():
            messagebox.showwarning("Exportar", "No hay datos para exportar")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Collections"

        headers = self.tree["columns"]
        ws.append(headers)

        for item in self.tree.get_children():
            ws.append(self.tree.item(item)["values"])

        normalize_invoice_text_columns(ws, headers)

        try:
            wb.save(path)
            messagebox.showinfo(
                "Exportar",
                "Archivo Excel generado correctamente"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _export_pdf(self):

        if not self.tree.get_children():
            messagebox.showwarning(
                "Exportar PDF",
                "No hay información cargada para generar el PDF"
            )
            return

        # Reutiliza exactamente el mismo flujo
        self._estado_cuenta()
