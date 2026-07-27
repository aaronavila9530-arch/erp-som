import calendar
import os
import tkinter as tk
from datetime import date
from tkinter import ttk, filedialog, messagebox

from api_client import download_monthly_financial_report_api, get_accounting_periods_api


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
