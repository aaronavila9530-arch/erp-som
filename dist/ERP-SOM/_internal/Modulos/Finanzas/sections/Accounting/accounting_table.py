import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

from api_client import (
    get_accounting_ledger_api,
    post_accounting_reverse_entry_api,
    transition_accounting_entry_api,
)
from session_context import get_user, get_company_code
from Modulos.Finanzas.date_utils import to_long_english_date

PAGE_SIZE = 150  # líneas por página


class AccountingTable(tk.Frame):
    """
    Tabla contable (Libro diario / mayor)
    Alineada a UI nueva (periodos controlados por sistema, KPIs externos)
    """

    def __init__(self, parent):
        super().__init__(parent, bg="white")

        self.tree = None

        # ================= PAGINACIÓN =================
        self.all_rows = []
        self.current_page = 1
        self.total_pages = 1

        self.total_debit = 0.0
        self.total_credit = 0.0

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        columns = ("date", "entry", "status", "account", "detail", "debit", "credit")

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=18
        )

        headers = {
            "date": "Fecha",
            "entry": "Asiento",
            "status": "Estado",
            "account": "Cuenta contable",
            "detail": "Detalle",
            "debit": "Debe",
            "credit": "Haber"
        }

        widths = {
            "date": 90,
            "entry": 90,
            "status": 105,
            "account": 260,
            "detail": 340,
            "debit": 110,
            "credit": 110
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor="e" if col in ("debit", "credit") else "w"
            )

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ================= TAGS =================
        self.tree.tag_configure("separator", background="#f2f2f2")
        self.tree.tag_configure("debit", foreground="#003366")
        self.tree.tag_configure("credit", foreground="#7a0000")

        # ================= CONTEXT MENU =================
        self.menu = tk.Menu(self, tearoff=0)

        self.menu.add_command(
            label="📘 Mayorizar / Cierre contable",
            command=self._open_closing_wizard
        )
        self.menu.add_separator()
        self.menu.add_command(label="✏️ Ajustar asiento", command=self._edit_entry)
        self.menu.add_command(label="📨 Enviar a revisión", command=lambda: self._transition_entry("submit"))
        self.menu.add_command(label="✅ Aprobar", command=lambda: self._transition_entry("approve"))
        self.menu.add_command(label="📘 Contabilizar", command=lambda: self._transition_entry("post"))
        self.menu.add_command(label="🔁 Reversar asiento", command=self._reverse_entry)
        self.menu.add_separator()
        self.menu.add_command(label="📄 Exportar CSV", command=self.export_csv)
        self.menu.add_command(label="📊 Exportar Excel", command=self.export_excel)

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self._edit_entry())

        # ================= PAGINATION BAR =================
        nav = tk.Frame(self, bg="white")
        nav.grid(row=2, column=0, columnspan=2, sticky="e", pady=5)

        self.lbl_page = tk.Label(nav, text="Página 1 / 1", bg="white")
        self.lbl_page.pack(side="left", padx=10)

        ttk.Button(nav, text="◀ Anterior", command=self._prev_page).pack(side="left")
        ttk.Button(nav, text="Siguiente ▶", command=self._next_page).pack(side="left")

    # ============================================================
    # DATA LOAD
    # ============================================================
    def load_from_api(self, period=None, period_from=None, period_to=None, origin=None, account_code=None):

        self.all_rows.clear()
        self.current_page = 1
        self.total_debit = 0.0
        self.total_credit = 0.0

        entries = get_accounting_ledger_api(
            period=period,
            period_from=period_from,
            period_to=period_to,
            origin=origin,
            account_code=account_code
        )

        if not entries:
            self._render_page()
            return

        # El backend ya entrega el ledger por fecha/asiento descendente.
        # Mantener ese orden evita que la UI vuelva a poner primero asientos antiguos.
        entries = sorted(
            entries,
            key=lambda x: (
                str(x.get("entry_date") or ""),
                int(x.get("entry_id") or 0),
            ),
            reverse=True,
        )

        for entry in entries:
            entry_id = entry.get("entry_id")
            entry_date = to_long_english_date(entry.get("entry_date"))
            workflow_status = entry.get("workflow_status") or "POSTED"

            debit_lines = []
            credit_lines = []

            for line in entry.get("lines", []):
                debit = float(line.get("debit") or 0)
                credit = float(line.get("credit") or 0)

                row = {
                    "values": (
                        entry_date,
                        entry_id,
                        workflow_status,
                        f"{line.get('account_code')} {line.get('account_name')}".strip(),
                        line.get("line_description") or "",
                        f"{debit:,.2f}" if debit else "",
                        f"{credit:,.2f}" if credit else ""
                    ),
                    "debit": debit,
                    "credit": credit,
                    "tag": "debit" if debit else "credit"
                }

                if debit:
                    debit_lines.append(row)
                elif credit:
                    credit_lines.append(row)
                self.total_debit += debit
                self.total_credit += credit

            # 1️⃣ DEBE
            self.all_rows.extend(debit_lines)
            # 2️⃣ HABER
            self.all_rows.extend(credit_lines)

            # Separador visual solo si hubo líneas
            if debit_lines or credit_lines:
                self.all_rows.append({
                    "values": ("", "", "", "────────────", "", "", ""),
                    "debit": 0,
                    "credit": 0,
                    "tag": "separator"
                })

        self.total_pages = max(1, (len(self.all_rows) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._render_page()

    # ============================================================
    # RENDER PAGE
    # ============================================================
    def _render_page(self):

        self.tree.delete(*self.tree.get_children())
        start = (self.current_page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE

        for row in self.all_rows[start:end]:
            self.tree.insert("", "end", values=row["values"], tags=(row["tag"],))

        self.lbl_page.config(
            text=f"Página {self.current_page} / {self.total_pages}"
        )

    # ============================================================
    # PAGINATION EVENTS
    # ============================================================
    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._render_page()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_page()

    # ============================================================
    # CONTEXT MENU
    # ============================================================
    def _show_context_menu(self, event):
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                self.tree.selection_set(row_id)
                self.tree.focus(row_id)
                self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # ============================================================
    # CIERRE CONTABLE
    # ============================================================
    def _open_closing_wizard(self):
        from Modulos.Finanzas.sections.Accounting.popups.popup_closing_wizard import PopupClosingWizard
        PopupClosingWizard(self, company_code=get_company_code(), ledger="0L")

    # ============================================================
    # AJUSTES / REVERSOS
    # ============================================================
    def _selected_entry(self):
        item = self.tree.focus()
        if not item:
            return None, None
        values = self.tree.item(item, "values")
        if not values or values[3] == "────────────":
            return None, None
        try:
            return int(values[1]), values[2]
        except Exception:
            return None, None

    def _transition_entry(self, action):
        entry_id, current_status = self._selected_entry()
        if not entry_id:
            messagebox.showwarning("Accounting", "Seleccione una línea del asiento.")
            return
        labels = {"submit": "enviar a revisión", "approve": "aprobar", "post": "contabilizar"}
        if not messagebox.askyesno("Flujo contable", f"¿Desea {labels[action]} el asiento {entry_id}?"):
            return
        try:
            transition_accounting_entry_api(entry_id, action, get_user() or "unknown")
            messagebox.showinfo("Accounting", f"Asiento {entry_id} actualizado correctamente.")
            self.event_generate("<<ReloadAccounting>>")
        except Exception as exc:
            messagebox.showerror("Accounting", str(exc))

    def _edit_entry(self):
        item = self.tree.focus()
        if not item:
            return

        values = self.tree.item(item, "values")
        if not values or values[3] == "────────────":
            return

        try:
            entry_id = int(values[1])
        except Exception:
            return

        from Modulos.Finanzas.sections.Accounting.popups.popup_adjust_entry import PopupAdjustEntry
        PopupAdjustEntry(
            self,
            entry_id=entry_id,
            on_success=lambda: self.event_generate("<<ReloadAccounting>>")
        )

    def _reverse_entry(self):
        item = self.tree.focus()
        if not item:
            return

        values = self.tree.item(item, "values")
        try:
            entry_id = int(values[1])
        except Exception:
            return

        if not messagebox.askyesno(
            "Reversar asiento",
            f"¿Reversar asiento {entry_id}?"
        ):
            return

        post_accounting_reverse_entry_api(entry_id)
        messagebox.showinfo("Reversado", f"Asiento {entry_id} revertido.")
        self.event_generate("<<ReloadAccounting>>")

    # ============================================================
    # EXPORTS
    # ============================================================
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha", "Asiento", "Estado", "Cuenta", "Detalle", "Debe", "Haber"])
            for row in self.all_rows:
                if row["values"][3] != "────────────":
                    writer.writerow(row["values"])

        messagebox.showinfo("Exportar CSV", "Archivo generado.")

    def export_excel(self):
        from openpyxl import Workbook

        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.append(["Fecha", "Asiento", "Estado", "Cuenta", "Detalle", "Debe", "Haber"])

        for row in self.all_rows:
            if row["values"][3] != "────────────":
                ws.append(row["values"])

        wb.save(path)
        messagebox.showinfo("Exportar Excel", "Archivo generado.")

    # ============================================================
    # KPI
    # ============================================================
    def get_totals(self):
        return self.total_debit, self.total_credit
