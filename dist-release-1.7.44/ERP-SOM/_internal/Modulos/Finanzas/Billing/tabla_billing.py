import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import csv
import os

from api_client import BASE_URL, api_request
from Modulos.Finanzas.date_utils import to_long_english_date
from Modulos.Finanzas.export_formatting import normalize_invoice_text_columns
from Modulos.Finanzas.popups.popup_preview_factura import PopupPreviewFactura


class TablaBilling(tk.Frame):

    def __init__(self, parent, filtros):
        super().__init__(parent)

        self.filtros = filtros
        self.page = 1
        self.page_size = 50
        self.total_items = 0

        self._build_ui()
        self._load_data()

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):

        self.tree = ttk.Treeview(
            self,
            columns=(
                "id",
                "tipo_factura",
                "documento",
                "numero",
                "cliente",
                "fecha",
                "moneda",
                "total",
                "estado"
            ),
            show="headings",
            height=18
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("tipo_factura", text="Tipo")
        self.tree.heading("documento", text="Documento")
        self.tree.heading("numero", text="Número")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("moneda", text="Moneda")
        self.tree.heading("total", text="Total")
        self.tree.heading("estado", text="Estado")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("tipo_factura", width=90, anchor="center")
        self.tree.column("documento", width=100, anchor="center")
        self.tree.column("numero", width=110)
        self.tree.column("cliente", width=220)
        self.tree.column("fecha", width=100, anchor="center")
        self.tree.column("moneda", width=70, anchor="center")
        self.tree.column("total", width=110, anchor="e")
        self.tree.column("estado", width=100, anchor="center")

        self.tree.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.tree.bind(
            "<Double-1>",
            self._ver_factura_doble_click
        )

        # ==========================
        # MENÚ CONTEXTUAL EXPORTAR
        # ==========================
        self.menu_exportar = tk.Menu(
            self,
            tearoff=0
        )
        self.menu_exportar.add_command(
            label="Exportar CSV",
            command=self._exportar
        )
        self.menu_exportar.add_command(
            label="Exportar Excel",
            command=self._exportar_excel
        )

        self.tree.bind(
            "<Button-3>",
            self._mostrar_menu_exportar
        )

        # ================= BOTONES =================
        actions = tk.Frame(self)
        actions.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Button(
            actions,
            text="📄 Ver factura",
            command=self._ver_factura_btn
        ).pack(side="left", padx=5)

        ttk.Button(
            actions,
            text="⬇ Descargar PDF",
            command=self._descargar_pdf
        ).pack(side="left", padx=5)

        export_btn = ttk.Menubutton(
            actions,
            text="📤 Exportar ▼",
            direction="below"
        )
        export_btn.pack(side="left", padx=20)

        export_menu = tk.Menu(export_btn, tearoff=0)
        export_menu.add_command(label="Exportar CSV", command=self._exportar)
        export_menu.add_command(label="Exportar Excel", command=self._exportar_excel)
        export_btn["menu"] = export_menu

        # ================= PAGINACIÓN =================
        pag = tk.Frame(self)
        pag.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(pag, text="◀ Anterior", command=self._prev_page).pack(side="left")

        self.lbl_pagina = tk.Label(pag, text="Página 1")
        self.lbl_pagina.pack(side="left", padx=15)

        ttk.Button(pag, text="Siguiente ▶", command=self._next_page).pack(side="left")

    # ======================================================
    # DATA
    # ======================================================
    def _load_data(self):

        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            r = api_request(
                "GET",
                f"{BASE_URL}/billing/search",
                params={**self.filtros, "page": self.page, "page_size": self.page_size},
                timeout=15
            )
            r.raise_for_status()

            payload = r.json()

            # ----------------------------------------------
            # ORDENAR POR ID ASCENDENTE
            # ----------------------------------------------
            data = sorted(
                payload.get("data", []),
                key=lambda x: x.get("id") or 0
            )

            self.total_items = payload.get("total", len(data))

            for row in data:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("id"),
                        row.get("tipo_factura"),
                        row.get("tipo_documento"),
                        row.get("numero_documento"),
                        row.get("nombre_cliente"),
                        self._fmt_fecha(row.get("fecha_emision")),
                        row.get("moneda"),
                        row.get("total"),
                        row.get("estado")
                    )
                )

            total_pages = max(
                1,
                (self.total_items + self.page_size - 1) // self.page_size
            )

            self.lbl_pagina.config(
                text=f"Página {self.page} de {total_pages}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error Billing",
                str(e)
            )

    # ======================================================
    # VER FACTURA (MISMO POPUP QUE INVOICING)
    # ======================================================
    def _ver_factura_btn(self):

        values = self._get_selected()
        if not values:
            return

        tipo_factura = values[1]
        numero_factura = str(values[3])  # 🔑 driver

        # --------------------------------------------------
        # FACTURA ELECTRÓNICA → MENSAJE GTI
        # --------------------------------------------------
        if tipo_factura == "ELECTRONICA":
            messagebox.showinfo(
                "Factura electrónica",
                "Para ver factura, dirigirse a GTI"
            )
            return

        try:
            # 1️⃣ Cargar factura completa desde API
            r = api_request(
                "GET",
                f"{BASE_URL}/billing/{numero_factura}",
                timeout=15
            )
            r.raise_for_status()
            factura = r.json()

            # 2️⃣ Callback dummy (Billing es solo lectura)
            def _noop():
                pass

            # 3️⃣ Abrir EXACTAMENTE el mismo popup de Invoicing
            PopupPreviewFactura(self, factura, _noop)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la factura\n\n{e}"
            )

    # ======================================================
    # DOBLE CLICK = VER FACTURA
    # ======================================================
    def _ver_factura_doble_click(self, event):
        self._ver_factura_btn()

    # ======================================================
    # DESCARGAR PDF FACTURA
    # ======================================================
    def _descargar_pdf(self):

        values = self._get_selected()
        if not values:
            return

        tipo_factura = values[1]
        numero_factura = str(values[3])

        # --------------------------------------------------
        # FACTURA ELECTRÓNICA → MENSAJE GTI
        # --------------------------------------------------
        if tipo_factura == "ELECTRONICA":
            messagebox.showinfo(
                "Factura electrónica",
                "Para descargar factura, dirigirse a GTI"
            )
            return

        destino = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Factura_{numero_factura}.pdf"
        )
        if not destino:
            return

        try:
            r = api_request(
                "GET",
                f"{BASE_URL}/billing/pdf/{numero_factura}",
                timeout=30,
                stream=True
            )
            r.raise_for_status()

            with open(destino, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo(
                "OK",
                "Factura descargada correctamente"
            )

        except Exception as e:
            messagebox.showerror(
                "Error al descargar",
                str(e)
            )

    # ======================================================
    # PAGINACIÓN
    # ======================================================
    def _next_page(self):
        if self.page * self.page_size < self.total_items:
            self.page += 1
            self._load_data()

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_data()

    # ======================================================
    # EXPORTAR
    # ======================================================
    def _get_export_params(self):
        """
        Limpia filtros antes de exportar
        (defensa extra contra 422)
        """
        params = {
            k: v for k, v in self.filtros.items()
            if v not in (None, "", "ALL")
        }

        params["page"] = 1
        params["page_size"] = 10000

        return params


    def _exportar(self):

        try:
            r = api_request(
                "GET",
                f"{BASE_URL}/billing/search",
                params=self._get_export_params(),
                timeout=30
            )
            r.raise_for_status()

            data = r.json().get("data", [])
            if not data:
                messagebox.showinfo(
                    "Exportar",
                    "No hay datos para exportar"
                )
                return

            destino = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                initialfile="billing_export.csv"
            )
            if not destino:
                return

            with open(destino, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "Tipo Factura", "Documento", "Número",
                    "Cliente", "Fecha", "Moneda", "Total", "Estado"
                ])

                for row in data:
                    writer.writerow([
                        row.get("id"),
                        row.get("tipo_factura"),
                        row.get("tipo_documento"),
                        row.get("numero_documento"),
                        row.get("nombre_cliente"),
                        self._fmt_fecha(row.get("fecha_emision")),
                        row.get("moneda"),
                        row.get("total"),
                        row.get("estado")
                    ])

            messagebox.showinfo(
                "Exportar",
                "Archivo CSV exportado correctamente"
            )

        except Exception as e:
            messagebox.showerror(
                "Exportar",
                str(e)
            )


    def _exportar_excel(self):

        try:
            from openpyxl import Workbook

            r = api_request(
                "GET",
                f"{BASE_URL}/billing/search",
                params=self._get_export_params(),
                timeout=30
            )
            r.raise_for_status()

            data = r.json().get("data", [])
            if not data:
                messagebox.showinfo(
                    "Exportar",
                    "No hay datos para exportar"
                )
                return

            destino = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                initialfile="billing.xlsx"
            )
            if not destino:
                return

            wb = Workbook()
            ws = wb.active
            ws.title = "Billing"

            ws.append([
                "ID", "Tipo Factura", "Documento", "Número",
                "Cliente", "Fecha", "Moneda", "Total", "Estado"
            ])

            headers = list(ws[1])
            export_headers = [cell.value for cell in headers]
            if len(export_headers) >= 4:
                export_headers[3] = "numero_documento"

            for row in data:
                ws.append([
                    row.get("id"),
                    row.get("tipo_factura"),
                    row.get("tipo_documento"),
                    row.get("numero_documento"),
                    row.get("nombre_cliente"),
                        self._fmt_fecha(row.get("fecha_emision")),
                    row.get("moneda"),
                    row.get("total"),
                    row.get("estado")
                ])

            normalize_invoice_text_columns(ws, export_headers)

            wb.save(destino)

            messagebox.showinfo(
                "Exportar",
                "Archivo Excel generado correctamente"
            )

        except Exception as e:
            messagebox.showerror(
                "Exportar",
                str(e)
            )

    # ======================================================
    # HELPERS
    # ======================================================
    def _fmt_fecha(self, fecha):
        return to_long_english_date(fecha)

    def _get_selected(self):
        item = self.tree.focus()
        if not item:
            messagebox.showwarning(
                "Seleccione",
                "Debe seleccionar una factura"
            )
            return None
        return self.tree.item(item)["values"]

    # ======================================================
    # Handler
    # ======================================================

    def _mostrar_menu_exportar(self, event):
        try:
            self.menu_exportar.tk_popup(
                event.x_root,
                event.y_root
            )
        finally:
            self.menu_exportar.grab_release()

