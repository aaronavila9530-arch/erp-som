import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


from tkinter import filedialog
import csv
from openpyxl import Workbook

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_db_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker

from api_client import (
    get_invoice_to_pay_search_api,
    get_invoice_to_pay_kpis_api
)


class InvoiceToPayUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self._build_ui()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build_ui(self):

        # ================= HEADER =================
        tk.Label(
            self,
            text="Invoice to Pay",
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="w", padx=15, pady=(5, 2))

        # ================= FILTROS =================
        filter_frame = tk.LabelFrame(self, text="Filtros")
        filter_frame.pack(fill="x", padx=15, pady=10)

        # ---- Combobox dinámicos ----
        self.cmb_obligation = ttk.Combobox(filter_frame, width=22, state="readonly")
        self.cmb_payee = ttk.Combobox(filter_frame, width=28, state="readonly")
        self.cmb_status = ttk.Combobox(filter_frame, width=16, state="readonly")

        self.cmb_obligation.set("")
        self.cmb_payee.set("")
        self.cmb_status.set("")

        self.cmb_obligation.grid(row=0, column=0, padx=5, pady=5)
        self.cmb_payee.grid(row=0, column=1, padx=5, pady=5)
        self.cmb_status.grid(row=0, column=2, padx=5, pady=5)

        # ---- Fechas factura ----
        tk.Label(filter_frame, text="Fecha factura").grid(row=1, column=0, sticky="w", padx=5)

        self.fecha_factura_from = self._date_filter(filter_frame, row=1, column=1, sticky="w")
        self.fecha_factura_to = self._date_filter(filter_frame, row=1, column=1, sticky="e")

        # ---- Fechas vencimiento ----
        tk.Label(filter_frame, text="Fecha vencimiento").grid(row=2, column=0, sticky="w", padx=5)

        self.fecha_venc_from = self._date_filter(filter_frame, row=2, column=1, sticky="w")
        self.fecha_venc_to = self._date_filter(filter_frame, row=2, column=1, sticky="e")

        # ---- Último pago ----
        tk.Label(filter_frame, text="Último pago").grid(row=3, column=0, sticky="w", padx=5)

        self.fecha_pago_from = self._date_filter(filter_frame, row=3, column=1, sticky="w")
        self.fecha_pago_to = self._date_filter(filter_frame, row=3, column=1, sticky="e")

        ttk.Button(filter_frame, text="Buscar", command=self._on_search).grid(row=0, column=4, padx=10)
        ttk.Button(filter_frame, text="Limpiar", command=self._on_clear).grid(row=0, column=5)

        # ================= CONTENEDOR LAZY (OCULTO) =================
        self.lazy_container = tk.Frame(self)
        # ❗ NO pack aquí

        # ================= KPIs =================
        kpi_frame = tk.Frame(self.lazy_container)
        kpi_frame.pack(fill="x", padx=15, pady=5)

        self.kpi_pending, self.lbl_pending = self._kpi_card(kpi_frame, "Pending Payables", "0.00", "#005b9f")
        self.kpi_paid, self.lbl_paid = self._kpi_card(kpi_frame, "Paid Amount", "0.00", "#00a884")
        self.kpi_dpo, self.lbl_dpo = self._kpi_card(kpi_frame, "Avg Payment Days", "0", "#6c757d")
        self.kpi_overdue, self.lbl_overdue = self._kpi_card(kpi_frame, "Overdue Amount", "0.00", "#dc3545")

        for card in (self.kpi_pending, self.kpi_paid, self.kpi_dpo, self.kpi_overdue):
            card.pack(side="left", padx=8)

        # ================= ALERTAS =================
        alert_frame = tk.Frame(self.lazy_container)
        alert_frame.pack(fill="x", padx=15, pady=(2, 2))

        self.lbl_alert_upcoming = tk.Label(
            alert_frame, text="🟡 No hay pagos próximos", fg="#b58900", font=("Segoe UI", 9, "bold")
        )
        self.lbl_alert_upcoming.pack(side="left", padx=5)

        self.lbl_alert_overdue = tk.Label(
            alert_frame, text="🔴 No hay pagos vencidos", fg="#dc322f", font=("Segoe UI", 9, "bold")
        )
        self.lbl_alert_overdue.pack(side="left", padx=20)

        # ================= ACCIONES =================
        action_frame = tk.Frame(self.lazy_container)
        action_frame.pack(fill="x", padx=15, pady=(5, 10))

        btn_exportar = ttk.Menubutton(action_frame, text="📤 Exportar", direction="below")
        btn_exportar.pack(side="left", padx=5)

        export_menu = tk.Menu(btn_exportar, tearoff=0)
        btn_exportar["menu"] = export_menu

        export_menu.add_command(label="Exportar a CSV", command=self._export_csv)
        export_menu.add_command(label="Exportar a Excel", command=self._export_excel)

        ttk.Button(action_frame, text="➕ Registrar obligación manual", command=self._on_manual_obligation).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📄 Cargar factura PDF / XML", command=self._on_upload_invoice).pack(side="left", padx=5)
        ttk.Button(action_frame, text="💰 Aplicar pago", command=self._on_apply_payment).pack(side="right", padx=5)
        ttk.Button(action_frame, text="🗑️ Eliminar", command=self._on_delete_obligation).pack(side="right", padx=5)

        # ================= TABLA =================
        table_container = tk.Frame(self.lazy_container)
        table_container.pack(fill="both", expand=True, padx=15, pady=5)

        table_frame = tk.Frame(table_container)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=(
            "id","beneficiario","obligacion","referencia","fecha_factura","fecha_vencimiento",
            "buque","pais","operacion","moneda","total","saldo","ultimo_pago","estado"
        ), show="headings", height=16)

        self.tree.heading("id", text="")
        self.tree.column("id", width=0, stretch=False)

        for col in self.tree["columns"][1:]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="center")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)



        # ================= MENÚ CONTEXTUAL (CLICK DERECHO) =================
        self.context_menu = tk.Menu(self, tearoff=0)

        self.context_menu.add_command(
            label="📋 Copiar fila seleccionada",
            command=self._copy_selected_row
        )

        self.context_menu.add_command(
            label="📋 Copiar todo",
            command=self._copy_all_rows
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="📤 Exportar a CSV",
            command=self._export_csv
        )

        self.context_menu.add_command(
            label="📤 Exportar a Excel",
            command=self._export_excel
        )

        # Bind click derecho
        self.tree.bind(
            "<Button-3>",
            self._show_context_menu
        )

        self.tree.tag_configure(
            "OVERDUE",
            background="#ffe5e5",
            foreground="#a10000"
        )

    # ============================================================
    # SEARCH + KPIs + ALERTAS
    # ============================================================
    def _on_search(self):

        # Mostrar sección lazy solo al buscar
        if not self.lazy_container.winfo_ismapped():
            self.lazy_container.pack(fill="both", expand=True)

        self.tree.delete(*self.tree.get_children())

        rows = get_invoice_to_pay_search_api(
            obligation_type=self.cmb_obligation.get() or None,
            payee=self.cmb_payee.get() or None,
            status=None if self.cmb_status.get() in ("", "ALL") else self.cmb_status.get(),

            issue_date_from=to_db_date(self.fecha_factura_from.get()) or None,
            issue_date_to=to_db_date(self.fecha_factura_to.get()) or None,

            due_date_from=to_db_date(self.fecha_venc_from.get()) or None,
            due_date_to=to_db_date(self.fecha_venc_to.get()) or None,

            payment_date_from=to_db_date(self.fecha_pago_from.get()) or None,
            payment_date_to=to_db_date(self.fecha_pago_to.get()) or None
        )

        self._load_dynamic_filters(rows)

        for row in rows:

            tags = [row["status"]]

            # ------------------------------------------------------------
            # 🔴 MARCAR OBLIGACIONES VENCIDAS VISUALMENTE
            # ------------------------------------------------------------
            try:
                if (
                    row["status"] == "PENDING"
                    and row.get("due_date")
                    and date.fromisoformat(row["due_date"]) < date.today()
                ):
                    tags.append("OVERDUE")
            except Exception:
                pass

            self.tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["payee_name"],
                    row["obligation_type"],
                    row["referencia"],
                    to_long_english_date(row.get("issue_date")) if row.get("issue_date") else "",
                    to_long_english_date(row.get("due_date")) if row.get("due_date") else "",
                    row["vessel"],
                    row["country"],
                    row["operation"],
                    row["currency"],
                    row["total"],
                    row["balance"],
                    to_long_english_date(row.get("last_payment_date")) if row.get("last_payment_date") else "",
                    row["status"]
                ),
                tags=tuple(tags)
            )

        kpi = get_invoice_to_pay_kpis_api()

        self.lbl_pending.config(
            text=f"{kpi.get('pending', 0):,.2f}"
        )

        self.lbl_paid.config(
            text=f"{kpi.get('paid', 0):,.2f}"
        )

        self.lbl_dpo.config(
            text=f"{int(kpi.get('dpo') or 0):,}"
        )

        self.lbl_overdue.config(
            text=f"{kpi.get('overdue_amount', 0):,.2f}"
        )

        upcoming = kpi.get("upcoming", 0)
        overdue = kpi.get("overdue", 0)

        self.lbl_alert_upcoming.config(
            text=f"🟡 {upcoming} pagos próximos"
            if upcoming else "🟡 No hay pagos próximos"
        )

        self.lbl_alert_overdue.config(
            text=f"🔴 {overdue} pagos vencidos"
            if overdue else "🔴 No hay pagos vencidos"
        )

    # ============================================================
    # APPLY PAYMENT
    # ============================================================
    def _on_apply_payment(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una obligación.")
            return

        values = self.tree.item(selected, "values")

        try:
            obligation = {
                "id": int(values[0]),                 # id
                "payee": values[1],                   # beneficiario
                "reference": values[3],               # referencia ✅
                "currency": values[9],                # moneda ✅
                "balance": float(values[11])          # saldo ✅
            }
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo leer la obligación seleccionada:\n{e}"
            )
            return

        if obligation["balance"] <= 0:
            messagebox.showinfo("Info", "La obligación ya está pagada.")
            return

        from Modulos.Finanzas.sections.InvoiceToPay.popup_apply_payment import (
            PopupApplyPayment
        )

        PopupApplyPayment(
            self,
            obligation_data=obligation,
            on_success=self._on_search
        )

    # ============================================================
    # REGISTRAR OBLIGACIÓN MANUAL
    # ============================================================
    def _on_manual_obligation(self):
        from Modulos.Finanzas.sections.InvoiceToPay.popup_registrar_obligacion import (
            PopupRegistrarObligacion
        )

        PopupRegistrarObligacion(
            self,
            on_success=self._on_search
        )

    # ============================================================
    # CARGAR FACTURA PDF / XML
    # ============================================================
    def _on_upload_invoice(self):
        from Modulos.Finanzas.sections.InvoiceToPay.popup_upload_invoice import (
            PopupUploadInvoice
        )

        PopupUploadInvoice(
            self,
            on_success=self._on_search
        )

    def _on_clear(self):
        self.cmb_obligation.set("")
        self.cmb_payee.set("")
        self.cmb_status.set("")

        self.fecha_factura_from.delete(0, tk.END)
        self.fecha_factura_to.delete(0, tk.END)

        self.fecha_venc_from.delete(0, tk.END)
        self.fecha_venc_to.delete(0, tk.END)

        self.fecha_pago_from.delete(0, tk.END)
        self.fecha_pago_to.delete(0, tk.END)

        self.tree.delete(*self.tree.get_children())

    # ============================================================
    # KPI CARD
    # ============================================================
    def _kpi_card(self, parent, title, value, bg):
        frame = tk.Frame(parent, bg=bg, width=220, height=90)
        frame.pack_propagate(False)

        tk.Label(
            frame,
            text=title,
            bg=bg,
            fg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="nw", padx=10, pady=(8, 0))

        lbl_value = tk.Label(
            frame,
            text=value,
            bg=bg,
            fg="white",
            font=("Segoe UI", 20, "bold")
        )
        lbl_value.pack(expand=True)

        return frame, lbl_value

    def _date_filter(self, parent, row, column, sticky):
        frame = tk.Frame(parent)
        frame.grid(row=row, column=column, padx=5, pady=3, sticky=sticky)

        entry = ttk.Entry(frame, width=12)
        entry.pack(side="left")

        ttk.Button(
            frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, entry, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(3, 0))

        return entry


    # ============================================================
    # EXPORTAR CSV
    # ============================================================
    def _export_csv(self):
        if not self.tree.get_children():
            messagebox.showwarning("Atención", "No hay datos para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )

        if not file_path:
            return

        headers = [
            "Beneficiario",
            "Obligación",
            "Referencia",
            "Fecha factura",
            "Fecha vencimiento",
            "Buque",
            "País",
            "Operación",
            "Moneda",
            "Total",
            "Saldo",
            "Último pago",
            "Estado"
        ]

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(headers)

                for item in self.tree.get_children():
                    values = self.tree.item(item, "values")
                    writer.writerow(values[1:])  # omitimos ID

            messagebox.showinfo("Exportar", "Archivo CSV exportado correctamente.")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo exportar CSV:\n{e}"
            )

    # ============================================================
    # EXPORTAR EXCEL
    # ============================================================
    def _export_excel(self):
        if not self.tree.get_children():
            messagebox.showwarning("Atención", "No hay datos para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )

        if not file_path:
            return

        headers = [
            "Beneficiario",
            "Obligación",
            "Referencia",
            "Fecha factura",
            "Fecha vencimiento",
            "Buque",
            "País",
            "Operación",
            "Moneda",
            "Total",
            "Saldo",
            "Último pago",
            "Estado"
        ]

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Invoice To Pay"

            # Encabezados
            ws.append(headers)

            # Datos
            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                ws.append(list(values[1:]))  # omitimos ID

            # Ajuste automático de ancho de columnas
            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = max_length + 2

            wb.save(file_path)

            messagebox.showinfo("Exportar", "Archivo Excel exportado correctamente.")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo exportar Excel:\n{e}"
            )


    def _show_context_menu(self, event):
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                self.tree.selection_set(row_id)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    def _copy_selected_row(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning(
                "Atención",
                "No hay ninguna fila seleccionada."
            )
            return

        values = self.tree.item(selected, "values")

        # Convertir fila a texto tabulado (Excel friendly)
        text = "\t".join(str(v) for v in values[1:])  # omitimos ID

        self.clipboard_clear()
        self.clipboard_append(text)

        messagebox.showinfo(
            "Copiar",
            "Fila copiada al portapapeles."
        )


    def _copy_all_rows(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning(
                "Atención",
                "No hay datos para copiar."
            )
            return

        lines = []

        for item in items:
            values = self.tree.item(item, "values")
            lines.append("\t".join(str(v) for v in values[1:]))  # omitimos ID

        text = "\n".join(lines)

        self.clipboard_clear()
        self.clipboard_append(text)

        messagebox.showinfo(
            "Copiar",
            "Todos los datos fueron copiados al portapapeles."
        )



    # ============================================================
    # CARGAR FILTROS DINÁMICOS DESDE LA TABLA
    # ============================================================
    def _load_dynamic_filters(self, rows):

        obligations = set()
        payees = set()
        statuses = set()

        for row in rows:
            if row.get("obligation_type"):
                obligations.add(row["obligation_type"])

            if row.get("payee_name"):
                payees.add(row["payee_name"])

            if row.get("status"):
                statuses.add(row["status"].upper())

        # --------------------------------------------------------
        # ORDENAR FILTROS
        # --------------------------------------------------------
        obligations = sorted(obligations)
        payees = sorted(payees)

        # --------------------------------------------------------
        # STATUS: FORZAR ALL + ESTADOS VÁLIDOS
        # --------------------------------------------------------
        final_statuses = ["ALL"]

        if "PENDING" in statuses:
            final_statuses.append("PENDING")

        if "PAID" in statuses:
            final_statuses.append("PAID")

        # --------------------------------------------------------
        # ASIGNAR A COMBOBOX
        # --------------------------------------------------------
        self.cmb_obligation["values"] = obligations
        self.cmb_payee["values"] = payees
        self.cmb_status["values"] = final_statuses

    # ============================================================
    # ELIMINAR OBLIGACIÓN
    # ============================================================
    def _on_delete_obligation(self):

        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning(
                "Atención",
                "Seleccione una obligación para eliminar."
            )
            return

        values = self.tree.item(selected, "values")
        obligation_id = int(values[0])
        referencia = values[3]

        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Está seguro de eliminar la obligación:\n\n{referencia}?"
        )

        if not confirm:
            return

        from api_client import delete_invoice_to_pay_api

        result = delete_invoice_to_pay_api(obligation_id)

        if result.get("status") != "ok":
            messagebox.showerror(
                "Error",
                f"No se pudo eliminar la obligación:\n{result.get('error')}"
            )
            return

        # Eliminar visualmente la fila
        self.tree.delete(selected)

        # Refrescar todo
        self._on_search()

        messagebox.showinfo(
            "Eliminado",
            "La obligación fue eliminada correctamente."
        )
