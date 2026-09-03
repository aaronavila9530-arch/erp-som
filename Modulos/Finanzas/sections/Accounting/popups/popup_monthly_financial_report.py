import calendar
import os
import sys
import tkinter as tk
from datetime import date
from tkinter import ttk, filedialog, messagebox

from api_client import (
    download_monthly_financial_report_api,
    get_accounting_periods_api,
    get_monthly_financial_obligations_preview_api,
    save_monthly_financial_obligations_preview_api,
)


def _local_obligations_preview(year, month):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
    backend_dir = os.path.join(root_dir, "backend_api")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from database import connect
    from reports.monthly_financial_report import build_monthly_obligation_preview

    conn = connect()
    try:
        return build_monthly_obligation_preview(conn, year, month)
    finally:
        conn.close()


def _local_save_obligations_preview(year, month, rows):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
    backend_dir = os.path.join(root_dir, "backend_api")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from database import connect
    from reports.monthly_financial_report import save_monthly_obligations
    from session_context import get_user

    conn = connect()
    try:
        return save_monthly_obligations(conn, year, month, rows, get_user())
    finally:
        conn.close()


class PopupMonthlyFinancialReport(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reportes financieros ejecutivos")
        self.geometry("470x250")
        self.resizable(False, False)
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()

        self.periods = self._load_periods()
        self.period_var = tk.StringVar(value=self.periods[-1])
        self.format_var = tk.StringVar(value="PDF")

        self._build()

    def _load_periods(self):
        today_period = date.today().strftime("%Y-%m")
        try:
            periods = get_accounting_periods_api()
        except Exception:
            periods = []

        clean = []
        for period in periods or []:
            value = str(period or "").strip()
            if len(value) == 7 and value[4] == "-" and value <= today_period:
                clean.append(value)
        return sorted(set(clean)) or [today_period]

    def _build(self):
        tk.Label(
            self,
            text="Reporte financiero ejecutivo",
            font=("Segoe UI", 14, "bold"),
            bg="white"
        ).pack(anchor="w", padx=18, pady=(14, 4))

        tk.Label(
            self,
            text="Genera PDF o Word con dashboard ejecutivo, graficos, ratios y analisis mensual.",
            bg="white",
            fg="#555"
        ).pack(anchor="w", padx=18, pady=(0, 12))

        form = tk.Frame(self, bg="white")
        form.pack(fill="x", padx=18)

        tk.Label(form, text="Periodo", bg="white").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(
            form,
            textvariable=self.period_var,
            values=self.periods,
            width=18,
            state="readonly"
        ).grid(row=0, column=1, sticky="w", pady=6)

        tk.Label(form, text="Formato", bg="white").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(form, textvariable=self.format_var, values=["PDF", "Word"], width=12, state="readonly").grid(row=1, column=1, sticky="w", pady=6)

        buttons = tk.Frame(self, bg="white")
        buttons.pack(fill="x", padx=18, pady=18)

        ttk.Button(buttons, text="Generar", command=self._generate).pack(side="right", padx=5)
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right", padx=5)

    def _generate(self):
        try:
            year_text, month_text = self.period_var.get().split("-", 1)
            year = int(year_text)
            month = int(month_text)
        except Exception:
            messagebox.showwarning("Reporte", "Seleccione un periodo valido.")
            return

        if not self._confirm_obligations(year, month):
            return

        fmt = self.format_var.get()
        extension = ".docx" if fmt == "Word" else ".pdf"
        filename = f"MSL_Financial_Report_{calendar.month_name[month]}_{year}{extension}"
        save_path = filedialog.asksaveasfilename(
            title="Guardar reporte financiero ejecutivo",
            defaultextension=extension,
            initialfile=filename,
            filetypes=[("Word", "*.docx")] if fmt == "Word" else [("PDF", "*.pdf")]
        )
        if not save_path:
            return

        self.configure(cursor="watch")
        self.update_idletasks()
        result = download_monthly_financial_report_api(year, month, fmt, save_path)
        self.configure(cursor="")

        if result.get("status") != "ok":
            messagebox.showerror("Reporte", f"No se pudo generar el reporte:\n{result.get('error')}")
            return

        final_path = result.get("path") or save_path
        if final_path != save_path:
            messagebox.showinfo(
                "Reporte",
                "El archivo original estaba bloqueado por Windows.\n"
                f"Se guardo una copia en:\n{final_path}"
            )

        if messagebox.askyesno("Reporte", "Reporte generado correctamente. Desea abrirlo?"):
            try:
                os.startfile(final_path)
            except Exception:
                pass
        self.destroy()

    def _confirm_obligations(self, year, month):
        try:
            payload = get_monthly_financial_obligations_preview_api(year, month)
            rows = payload.get("data", []) if isinstance(payload, dict) else []
        except Exception as exc:
            try:
                payload = _local_obligations_preview(year, month)
                rows = payload.get("data", []) if isinstance(payload, dict) else []
            except Exception as local_exc:
                messagebox.showerror(
                    "Obligaciones",
                    "No se pudo cargar el preliminar por API ni por conexión local:\n"
                    f"API: {exc}\nLocal: {local_exc}",
                    parent=self
                )
                return False

        win = tk.Toplevel(self)
        win.title("Preliminar de obligaciones mensuales")
        win.geometry("960x620")
        win.transient(self)
        win.grab_set()
        result = {"accepted": False}

        tk.Label(
            win,
            text="Revise y ajuste las obligaciones pendientes del mes antes de generar el reporte.",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(10, 4))

        cols = ("incluir", "payee_name", "concept", "issue_date", "currency", "amount")
        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=8)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        labels = {
            "incluir": "Incluir",
            "payee_name": "Proveedor",
            "concept": "Concepto",
            "issue_date": "Fecha factura",
            "currency": "Moneda",
            "amount": "Monto",
        }
        widths = {"incluir": 70, "payee_name": 260, "concept": 210, "issue_date": 110, "currency": 80, "amount": 120}
        for col in cols:
            tree.heading(col, text=labels[col])
            tree.column(col, width=widths[col], anchor="e" if col == "amount" else "w")
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        def _on_tree_wheel(event):
            tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        tree.bind("<MouseWheel>", _on_tree_wheel)

        editable_rows = []
        for row in rows:
            item = dict(row)
            item["accepted"] = bool(item.get("accepted", True))
            editable_rows.append(item)

        def money_text(value):
            try:
                return f"{float(value or 0):,.2f}"
            except Exception:
                return "0.00"

        def refresh():
            tree.delete(*tree.get_children())
            for idx, row in enumerate(editable_rows):
                tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        "Si" if row.get("accepted", True) else "No",
                        row.get("payee_name") or "",
                        row.get("concept") or "",
                        row.get("issue_date") or row.get("due_date") or "",
                        row.get("currency") or "USD",
                        money_text(row.get("amount")),
                    )
                )

        form = ttk.LabelFrame(win, text="Editar linea seleccionada", padding=8)
        form.pack(fill="x", padx=12, pady=(0, 8))
        include_var = tk.BooleanVar(value=True)
        payee_var = tk.StringVar()
        concept_var = tk.StringVar()
        issue_var = tk.StringVar()
        currency_var = tk.StringVar(value="USD")
        amount_var = tk.StringVar()

        ttk.Checkbutton(form, text="Incluir", variable=include_var).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(form, textvariable=payee_var, width=30).grid(row=0, column=1, padx=4)
        ttk.Entry(form, textvariable=concept_var, width=28).grid(row=0, column=2, padx=4)
        ttk.Entry(form, textvariable=issue_var, width=12).grid(row=0, column=3, padx=4)
        ttk.Combobox(form, textvariable=currency_var, values=["USD", "CRC"], width=8, state="readonly").grid(row=0, column=4, padx=4)
        ttk.Entry(form, textvariable=amount_var, width=14).grid(row=0, column=5, padx=4)

        def selected_index():
            sel = tree.selection()
            return int(sel[0]) if sel else None

        def load_selected(_event=None):
            idx = selected_index()
            if idx is None:
                return
            row = editable_rows[idx]
            include_var.set(bool(row.get("accepted", True)))
            payee_var.set(str(row.get("payee_name") or ""))
            concept_var.set(str(row.get("concept") or ""))
            issue_var.set(str(row.get("issue_date") or row.get("due_date") or ""))
            currency_var.set(str(row.get("currency") or "USD"))
            amount_var.set(money_text(row.get("amount")))

        def apply_selected():
            idx = selected_index()
            if idx is None:
                messagebox.showwarning("Obligaciones", "Seleccione una linea.", parent=win)
                return
            try:
                amount = float(amount_var.get().replace(",", ""))
            except Exception:
                messagebox.showwarning("Obligaciones", "Monto invalido.", parent=win)
                return
            editable_rows[idx].update({
                "accepted": include_var.get(),
                "payee_name": payee_var.get().strip(),
                "concept": concept_var.get().strip(),
                "issue_date": issue_var.get().strip() or None,
                "due_date": None,
                "currency": currency_var.get().strip() or "USD",
                "amount": amount,
            })
            refresh()

        def add_row():
            new_index = len(editable_rows)
            editable_rows.append({
                "accepted": True,
                "payee_name": "Nuevo proveedor",
                "concept": "Obligacion mensual",
                "issue_date": f"{year}-{month:02d}-01",
                "due_date": None,
                "currency": "USD",
                "amount": 0,
                "source": "MANUAL",
            })
            refresh()
            tree.selection_set(str(new_index))
            tree.focus(str(new_index))
            tree.see(str(new_index))
            load_selected()

        def accept():
            try:
                try:
                    save_monthly_financial_obligations_preview_api(year, month, editable_rows)
                except Exception:
                    _local_save_obligations_preview(year, month, editable_rows)
            except Exception as exc:
                messagebox.showerror("Obligaciones", f"No se pudieron guardar obligaciones:\n{exc}", parent=win)
                return
            result["accepted"] = True
            win.destroy()

        tree.bind("<<TreeviewSelect>>", load_selected)
        actions = ttk.Frame(win)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(actions, text="Agregar linea", command=add_row).pack(side="left")
        ttk.Button(actions, text="Aplicar edición", command=apply_selected).pack(side="left", padx=6)
        ttk.Button(actions, text="Cancelar", command=win.destroy).pack(side="right")
        ttk.Button(actions, text="Aceptar y generar", command=accept).pack(side="right", padx=6)

        refresh()
        if editable_rows:
            tree.selection_set("0")
            load_selected()
        self.wait_window(win)
        return result["accepted"]
