import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from collections import defaultdict

from api_client import (
    get_accounting_accounts_api,
    get_accounting_lines_api,
    get_accounting_periods_api,
    post_closing_tb_preview_api
)

from Modulos.Finanzas.sections.Accounting.reports.excel_diario import export_diario_excel
from Modulos.Finanzas.sections.Accounting.reports.export_diario_pdf import export_diario_pdf
from Modulos.Finanzas.sections.Accounting.reports.excel_mayor import export_mayor_excel
from Modulos.Finanzas.sections.Accounting.reports.excel_tb import export_tb_excel
from Modulos.Finanzas.sections.Accounting.reports.excel_esf import export_esf_excel
from Modulos.Finanzas.sections.Accounting.reports.excel_fc import export_fc_excel
from Modulos.Finanzas.sections.Accounting.reports.excel_account_analytic import (
    export_account_analytic_excel
)

# ✅ IMPORTS CORRECTOS (según tus funciones reales)
from Modulos.Finanzas.sections.Accounting.reports.excel_er import export_er_excel_from_er
from Modulos.Finanzas.sections.Accounting.reports.pdf_er import export_er_pdf_from_er

from Modulos.Finanzas.sections.Accounting.reports.build_er_from_lines import (
    build_er_from_lines
)

from Modulos.Finanzas.sections.Accounting.reports.build_esf_from_trial_balance import (
    build_esf_from_trial_balance
)
from Modulos.Finanzas.sections.Accounting.reports.excel_esf import (
    export_esf_excel_from_esf
)

from Modulos.Finanzas.sections.Accounting.reports.pdf_esf import export_esf_pdf_from_esf

from Modulos.Finanzas.sections.Accounting.reports.pdf_fc import (
    export_fc_pdf
)

from Modulos.Finanzas.sections.Accounting.reports.pdf_mayor import (
    export_mayor_pdf
)

from Modulos.Finanzas.sections.Accounting.reports.pdf_tb import (
    export_tb_pdf
)

ALL_MONTHS = [f"{month:02d}" for month in range(1, 13)]
ACCOUNT_TYPES = ["TODOS", "ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "COSTO", "GASTO"]


class PopupReportSelector(tk.Toplevel):
    """
    Selector de Reportes Contables

    ✔ Periodos y años desde accounting_lines.created_at
    ✔ Libro Diario desde líneas reales
    ✔ Estado de Resultados construido con build_er_from_lines
    ✔ ER NO usa closing
    ✔ BC y ESF sí usan closing
    ✔ Excel / PDF reciben el MISMO dataset correcto (ER dict)
    """

    def __init__(self, parent, ledger="0L"):
        super().__init__(parent)

        self.parent = parent
        self.ledger = ledger

        self.title("Reportes Contables")
        self.geometry("560x470")
        self.resizable(False, False)
        self.configure(bg="white")

        # ==================================================
        # Cargar líneas contables reales
        # ==================================================
        try:
            self.all_lines = get_accounting_lines_api()
        except Exception as e:
            messagebox.showerror(
                "Error API",
                f"No se pudieron cargar líneas contables:\n{e}"
            )
            self.destroy()
            return

        if not isinstance(self.all_lines, list):
            messagebox.showwarning(
                "Sin datos",
                "No existen líneas contables registradas."
            )
            self.destroy()
            return

        self.available_periods = self._extract_periods_from_lines()
        if not self.available_periods:
            messagebox.showwarning(
                "Sin periodos",
                "No se pudieron detectar periodos válidos desde created_at."
            )
            self.destroy()
            return

        # ==================================================
        # 🔥 FILTRO AVANZADO (SINGLE / RANGE)
        # ==================================================
        self.search_mode = tk.StringVar(value="SINGLE")  # SINGLE | RANGE

        self.period_from_year = tk.StringVar()
        self.period_from_month = tk.StringVar()
        self.period_to_year = tk.StringVar()
        self.period_to_month = tk.StringVar()
        self.account_type_var = tk.StringVar(value="TODOS")
        self.account_var = tk.StringVar(value="")
        self.account_map = {}

        # ==================================================
        # UI
        # ==================================================
        self._configure_styles()
        self._build_ui()

        # ==================================================
        # BINDS PARA RANGOS (AÑO → MESES)
        # ==================================================
        self.cmb_from_year.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_range_year_change(e, target="FROM")
        )
        self.cmb_to_year.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_range_year_change(e, target="TO")
        )

        # ==================================================
        # ESTADO INICIAL
        # ==================================================
        try:
            first_year = list(self.available_periods.keys())[0]

            # SINGLE
            self.cmb_year.set(str(first_year))
            self._on_year_change()

            # RANGE (preselección segura)
            self.period_from_year.set(str(first_year))
            self.period_to_year.set(str(first_year))
            self._on_range_year_change(target="FROM")
            self._on_range_year_change(target="TO")

        except Exception:
            pass

    # ==================================================
    # STYLES
    # ==================================================
    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure(
            "TRadiobutton",
            background="white",
            foreground="black",
            focuscolor="none"
        )
        style.map("TRadiobutton", background=[("active", "white")])

        style.configure(
            "TCombobox",
            fieldbackground="white",
            background="white",
            foreground="black"
        )

        style.configure(
            "TButton",
            background="white",
            foreground="black",
            focuscolor="none"
        )

    # ==================================================
    # HELPERS
    # ==================================================
    def _safe_parse_iso(self, value):
        if not value or not isinstance(value, str):
            return None

        s = value.strip()
        if not s:
            return None

        try:
            if " " in s and "T" not in s:
                s = s.replace(" ", "T", 1)
            return datetime.fromisoformat(s)
        except Exception:
            return None

    def _extract_periods_from_lines(self):
        periods = defaultdict(set)

        try:
            for value in get_accounting_periods_api() or []:
                text = str(value or "").strip()
                if len(text) == 7 and text[4] == "-":
                    periods[int(text[:4])].add(text[5:7])
        except Exception:
            pass

        for r in self.all_lines:
            if not isinstance(r, dict):
                continue

            period = str(r.get("period") or "").strip()
            if len(period) == 7 and period[4] == "-":
                periods[int(period[:4])].add(period[5:7])
                continue

            dt = self._safe_parse_iso(r.get("entry_date") or r.get("created_at"))
            if not dt:
                continue

            periods[dt.year].add(f"{dt.month:02d}")

        return {
            year: ALL_MONTHS
            for year, months in sorted(periods.items(), reverse=True)
        }

    def _line_period_tuple(self, row):
        if not isinstance(row, dict):
            return None
        period = str(row.get("period") or "").strip()
        if len(period) == 7 and period[4] == "-":
            try:
                return int(period[:4]), int(period[5:7])
            except Exception:
                return None
        dt = self._safe_parse_iso(row.get("entry_date") or row.get("created_at"))
        if dt:
            return dt.year, dt.month
        return None

    def _line_matches_account_type(self, row):
        selected = (self.account_type_var.get() or "TODOS").strip().upper()
        if selected in ("", "TODOS"):
            return True

        account_type = str(row.get("account_type") or "").strip().upper()
        if not account_type:
            code = str(row.get("account_code") or "").strip()
            if code.startswith("1"):
                account_type = "ACTIVO"
            elif code.startswith("2"):
                account_type = "PASIVO"
            elif code.startswith("3"):
                account_type = "PATRIMONIO"
            elif code.startswith("4"):
                account_type = "INGRESO"
            elif code.startswith("5"):
                account_type = "GASTO"
            elif code.startswith("6"):
                account_type = "COSTO"

        aliases = {
            "ACTIVO": {"ACTIVO", "ASSET"},
            "PASIVO": {"PASIVO", "LIABILITY"},
            "PATRIMONIO": {"PATRIMONIO", "EQUITY"},
            "INGRESO": {"INGRESO", "REVENUE", "INCOME"},
            "COSTO": {"COSTO", "COST"},
            "GASTO": {"GASTO", "EXPENSE"},
        }
        return account_type in aliases.get(selected, {selected})

    def _line_matches_account(self, row, account_filter):
        text = str(account_filter or "").strip().lower()
        if not text or text == "todos":
            return True
        code = str(row.get("account_code") or "").strip().lower()
        name = str(row.get("account_name") or "").strip().lower()
        label = f"{code} - {name}"
        return code == text or code.startswith(text) or text in name or text in label

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):

        tk.Label(
            self,
            text="Generación de Reportes",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="black"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # =========================
        # REPORTE
        # =========================
        report_frame = tk.LabelFrame(self, text="Reporte", bg="white", fg="black")
        report_frame.pack(fill="x", padx=20, pady=5)

        self.report_var = tk.StringVar(value="ASIENTOS")

        reports = [
            ("Asientos (Libro Diario)", "ASIENTOS"),
            ("Analítico de cuenta", "ANALITICO_CUENTA"),
            ("Detalle por tipo de cuenta", "DETALLE_TIPO"),
            ("Libro Mayor", "MAYOR"),
            ("Balance de Comprobación", "BC"),
            ("Estado de Situación Financiera", "ESF"),
            ("Estado de Resultados", "ER"),
            ("Flujo de Caja", "FC"),
        ]

        for i, (text, value) in enumerate(reports):
            ttk.Radiobutton(
                report_frame,
                text=text,
                value=value,
                variable=self.report_var
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=10, pady=4)

        # =========================
        # PERIODO / RANGO
        # =========================
        period_frame = tk.LabelFrame(self, text="Periodo", bg="white", fg="black")
        period_frame.pack(fill="x", padx=20, pady=10)

        # ---- modo ----
        ttk.Radiobutton(
            period_frame,
            text="Periodo único",
            variable=self.search_mode,
            value="SINGLE",
            command=self._toggle_period_mode
        ).grid(row=0, column=0, padx=10, sticky="w")

        ttk.Radiobutton(
            period_frame,
            text="Rango",
            variable=self.search_mode,
            value="RANGE",
            command=self._toggle_period_mode
        ).grid(row=0, column=1, padx=10, sticky="w")

        # ---- SINGLE ----
        tk.Label(period_frame, text="Año", bg="white").grid(row=1, column=0, padx=10, sticky="w")
        tk.Label(period_frame, text="Mes", bg="white").grid(row=1, column=2, padx=10, sticky="w")

        self.cmb_year = ttk.Combobox(
            period_frame,
            values=list(self.available_periods.keys()),
            width=8,
            state="readonly"
        )
        self.cmb_year.grid(row=1, column=1)
        self.cmb_year.bind("<<ComboboxSelected>>", self._on_year_change)

        self.cmb_month = ttk.Combobox(
            period_frame,
            values=[],
            width=8,
            state="readonly"
        )
        self.cmb_month.grid(row=1, column=3)

        # ---- RANGE ----
        tk.Label(period_frame, text="Desde", bg="white").grid(row=2, column=0, padx=10, sticky="w")

        self.cmb_from_year = ttk.Combobox(
            period_frame,
            values=list(self.available_periods.keys()),
            width=8,
            state="readonly",
            textvariable=self.period_from_year
        )
        self.cmb_from_year.grid(row=2, column=1)

        self.cmb_from_month = ttk.Combobox(
            period_frame,
            values=[],
            width=8,
            state="readonly",
            textvariable=self.period_from_month
        )
        self.cmb_from_month.grid(row=2, column=2)

        tk.Label(period_frame, text="Hasta", bg="white").grid(row=3, column=0, padx=10, sticky="w")

        self.cmb_to_year = ttk.Combobox(
            period_frame,
            values=list(self.available_periods.keys()),
            width=8,
            state="readonly",
            textvariable=self.period_to_year
        )
        self.cmb_to_year.grid(row=3, column=1)

        self.cmb_to_month = ttk.Combobox(
            period_frame,
            values=[],
            width=8,
            state="readonly",
            textvariable=self.period_to_month
        )
        self.cmb_to_month.grid(row=3, column=2)

        # =========================
        # TIPO DE CUENTA
        # =========================
        type_frame = tk.LabelFrame(self, text="Tipo de cuenta", bg="white", fg="black")
        type_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(type_frame, text="Filtrar por", bg="white").grid(row=0, column=0, padx=10, sticky="w")
        self.cmb_account_type = ttk.Combobox(
            type_frame,
            values=ACCOUNT_TYPES,
            width=18,
            state="readonly",
            textvariable=self.account_type_var
        )
        self.cmb_account_type.grid(row=0, column=1, padx=5, pady=6, sticky="w")
        tk.Label(
            type_frame,
            text="Útil para Balance de Comprobación por activo, pasivo, gasto, ingreso, etc.",
            bg="white",
            fg="#475569"
        ).grid(row=0, column=2, padx=10, sticky="w")

        tk.Label(type_frame, text="Cuenta", bg="white").grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")
        self.cmb_account = ttk.Combobox(
            type_frame,
            values=[],
            width=42,
            textvariable=self.account_var
        )
        self.cmb_account.grid(row=1, column=1, columnspan=2, padx=5, pady=(0, 6), sticky="w")
        self.cmb_account.bind("<Button-1>", self._lazy_load_accounts, add="+")
        self.cmb_account.bind("<FocusIn>", self._lazy_load_accounts, add="+")

        # =========================
        # FORMATO
        # =========================
        format_frame = tk.LabelFrame(self, text="Formato", bg="white", fg="black")
        format_frame.pack(fill="x", padx=20, pady=10)

        self.format_var = tk.StringVar(value="EXCEL")

        ttk.Radiobutton(
            format_frame,
            text="Excel",
            value="EXCEL",
            variable=self.format_var
        ).grid(row=0, column=0, padx=10, sticky="w")

        ttk.Radiobutton(
            format_frame,
            text="PDF",
            value="PDF",
            variable=self.format_var
        ).grid(row=0, column=1, padx=10, sticky="w")

        # =========================
        # BOTONES
        # =========================
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ttk.Button(
            btn_frame,
            text="Generar",
            command=self._on_generate
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

        # estado inicial
        self._toggle_period_mode()

    def _lazy_load_accounts(self, event=None):
        if self.account_map:
            return
        try:
            accounts = get_accounting_accounts_api(include_inactive=True)
        except Exception:
            accounts = []
        labels = []
        for acc in accounts or []:
            code = str(acc.get("account_code") or "").strip()
            name = str(acc.get("account_name") or "").strip()
            if not code:
                continue
            label = f"{code} - {name}" if name else code
            self.account_map[label] = code
            labels.append(label)
        self.cmb_account["values"] = sorted(labels, key=str.casefold)

    # ==================================================
    # EVENTS
    # ==================================================
    def _on_year_change(self, *_):
        y = self.cmb_year.get()
        if not y:
            self.cmb_month["values"] = []
            self.cmb_month.set("")
            return

        year = int(y)
        months = self.available_periods.get(year, [])
        self.cmb_month["values"] = months
        self.cmb_month.set(months[0] if months else "")


    def _toggle_period_mode(self):
        """
        Alterna entre búsqueda por periodo único (SINGLE)
        y por rango de periodos (RANGE).
        """
        mode = self.search_mode.get()

        if mode == "SINGLE":
            # ---- SINGLE habilitado ----
            self.cmb_year.configure(state="readonly")
            self.cmb_month.configure(state="readonly")

            # ---- RANGE deshabilitado ----
            self.cmb_from_year.configure(state="disabled")
            self.cmb_from_month.configure(state="disabled")
            self.cmb_to_year.configure(state="disabled")
            self.cmb_to_month.configure(state="disabled")

            # limpiar valores de rango
            self.period_from_year.set("")
            self.period_from_month.set("")
            self.period_to_year.set("")
            self.period_to_month.set("")

        else:
            # ---- RANGE habilitado ----
            self.cmb_year.configure(state="disabled")
            self.cmb_month.configure(state="disabled")

            self.cmb_from_year.configure(state="readonly")
            self.cmb_from_month.configure(state="readonly")
            self.cmb_to_year.configure(state="readonly")
            self.cmb_to_month.configure(state="readonly")

            # limpiar valores de single
            self.cmb_year.set("")
            self.cmb_month.set("")


    # ==================================================
    # ACTION
    # ==================================================
    def _on_generate(self):

        rows = []
        selected_type = (self.account_type_var.get() or "TODOS").strip()
        account_type_filter = None if selected_type in ("", "TODOS") else selected_type
        account_text = (self.account_var.get() or "").strip()
        account_code_filter = self.account_map.get(account_text)
        if not account_code_filter and account_text:
            account_code_filter = account_text.split(" - ", 1)[0].strip()

        # ==================================================
        # PERIODO / RANGO
        # ==================================================
        if self.search_mode.get() == "SINGLE":

            year = self.cmb_year.get()
            month = self.cmb_month.get()

            if not year or not month:
                messagebox.showerror(
                    "Periodo",
                    "Debe seleccionar año y mes disponibles."
                )
                return

            year = int(year)
            month = int(month)

            selected_period = f"{year}-{month:02d}"
            try:
                rows = get_accounting_lines_api(
                    period=selected_period,
                    account_type=account_type_filter,
                    account_code=account_code_filter
                )
            except Exception:
                rows = []
            if not rows:
                rows = [
                    r for r in self.all_lines
                    if self._line_period_tuple(r) == (year, month)
                    and self._line_matches_account_type(r)
                    and self._line_matches_account(r, account_code_filter)
                ]

            period_label_year = year
            period_label_month = month
            period_from_label = selected_period
            period_to_label = selected_period

        else:
            from_year = self.period_from_year.get()
            from_month = self.period_from_month.get()
            to_year = self.period_to_year.get()
            to_month = self.period_to_month.get()

            if not all([from_year, from_month, to_year, to_month]):
                messagebox.showerror(
                    "Rango",
                    "Debe seleccionar año y mes inicial y final."
                )
                return

            fy = int(from_year)
            fm = int(from_month)
            ty = int(to_year)
            tm = int(to_month)

            if (fy, fm) > (ty, tm):
                messagebox.showerror(
                    "Rango",
                    "El periodo inicial no puede ser mayor al final."
                )
                return

            from_period = f"{fy}-{fm:02d}"
            to_period = f"{ty}-{tm:02d}"
            try:
                rows = get_accounting_lines_api(
                    period_from=from_period,
                    period_to=to_period,
                    account_type=account_type_filter,
                    account_code=account_code_filter
                )
            except Exception:
                rows = []
            if not rows:
                rows = [
                    r for r in self.all_lines
                    if self._line_period_tuple(r) and (fy, fm) <= self._line_period_tuple(r) <= (ty, tm)
                    and self._line_matches_account_type(r)
                    and self._line_matches_account(r, account_code_filter)
                ]

            period_label_year = ty
            period_label_month = tm
            period_from_label = from_period
            period_to_label = to_period

        if not rows and self.report_var.get() != "ANALITICO_CUENTA":
            messagebox.showerror(
                "Reporte",
                "No hay datos para el periodo seleccionado."
            )
            return

        # ==================================================
        # REPORTE / FORMATO
        # ==================================================
        report = self.report_var.get()
        fmt = self.format_var.get()

        try:
            if report == "ANALITICO_CUENTA":
                if not account_code_filter:
                    messagebox.showerror("Cuenta", "Seleccione o escriba la cuenta para generar el analítico.")
                    return
                export_account_analytic_excel(
                    self.all_lines,
                    period_from=period_from_label,
                    period_to=period_to_label,
                    account_filter=account_code_filter,
                )

            if report == "ASIENTOS":
                if fmt == "EXCEL":
                    export_diario_excel(
                        rows,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )
                else:
                    export_diario_pdf(
                        rows,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )

            elif report == "DETALLE_TIPO":
                if fmt == "EXCEL":
                    export_diario_excel(
                        rows,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )
                else:
                    export_diario_pdf(
                        rows,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )

            elif report == "MAYOR":
                if fmt == "EXCEL":
                    export_mayor_excel(rows)
                else:
                    export_mayor_pdf(rows)

            elif report == "BC":
                opening_rows = [
                    r for r in self.all_lines
                    if self._line_period_tuple(r) and f"{self._line_period_tuple(r)[0]}-{self._line_period_tuple(r)[1]:02d}" < period_from_label
                    and self._line_matches_account_type(r)
                    and self._line_matches_account(r, account_code_filter)
                ]
                if fmt == "EXCEL":
                    from Modulos.Finanzas.sections.Accounting.reports.build_tb_from_lines import build_tb_from_lines
                    export_tb_excel(build_tb_from_lines(rows, opening_rows=opening_rows))
                else:
                    from Modulos.Finanzas.sections.Accounting.reports.build_tb_from_lines import build_tb_from_lines
                    export_tb_pdf(build_tb_from_lines(rows, opening_rows=opening_rows))

            elif report == "ESF":
                esf_rows = [
                    r for r in self.all_lines
                    if self._line_period_tuple(r) and f"{self._line_period_tuple(r)[0]}-{self._line_period_tuple(r)[1]:02d}" <= period_to_label
                    and self._line_matches_account(r, account_code_filter)
                ]
                esf_data = build_esf_from_trial_balance(esf_rows)
                if fmt == "EXCEL":
                    export_esf_excel_from_esf(esf_data)
                else:
                    export_esf_pdf_from_esf(esf_data)

            elif report == "ER":
                er_data = build_er_from_lines(rows)
                if fmt == "EXCEL":
                    export_er_excel_from_er(
                        er_data,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )
                else:
                    export_er_pdf_from_er(
                        er_data,
                        fiscal_year=period_label_year,
                        period=period_label_month
                    )

            elif report == "FC":
                if fmt == "EXCEL":
                    export_fc_excel(rows)
                else:
                    export_fc_pdf(rows)

            messagebox.showinfo(
                "Reporte",
                "Reporte generado correctamente."
            )
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_range_year_change(self, event=None, target="FROM"):
        """
        Actualiza los meses disponibles cuando cambia el año
        en los selectores de rango (FROM / TO).
        """
        if target == "FROM":
            year = self.cmb_from_year.get()
            cmb_month = self.cmb_from_month
            var = self.period_from_month
        else:
            year = self.cmb_to_year.get()
            cmb_month = self.cmb_to_month
            var = self.period_to_month

        if not year:
            cmb_month["values"] = []
            var.set("")
            return

        months = self.available_periods.get(int(year), [])
        cmb_month["values"] = months
        var.set(months[0] if months else "")

