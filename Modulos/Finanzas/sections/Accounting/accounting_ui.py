import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from api_client import (
    get_exchange_rate_today_api,
    get_accounting_accounts_api,
    get_accounting_iva_api,
    get_accounting_periods_api
)
from Modulos.Finanzas.date_utils import to_long_english_date
from Modulos.Finanzas.sections.Accounting.accounting_table import AccountingTable
from Modulos.Finanzas.sections.Accounting.popups.popup_report_selector import PopupReportSelector


class AccountingUI(tk.Frame):
    """
    ACCOUNTING
    Libro diario / mayor
    """

    def __init__(self, parent):
        super().__init__(parent, bg="white")
        self.pack(fill="both", expand=True)

        self.table = None

        # ================= ESTADO =================
        self.kpi_debit_var = tk.StringVar(value="0.00")
        self.kpi_credit_var = tk.StringVar(value="0.00")
        self.kpi_iva_var = tk.StringVar(value="0.00")

        self.tc_rate_var = tk.StringVar(value="")
        self.tc_date_var = tk.StringVar(value="")

        self.account_map = {}
        self.accounts_loaded = False

        self.periods = self._build_period_list()
        self.current_period = self.periods[-1]


        # ================= FILTRO AVANZADO =================
        self.search_mode = tk.StringVar(value="SINGLE")  # SINGLE | RANGE
        self.period_from = tk.StringVar()
        self.period_to = tk.StringVar()


        self._build_ui()
        self._check_month_open_alert()

        self.bind("<<ReloadAccounting>>", lambda e: self._reload_table_only())

        # Estado inicial: periodo único
        self._toggle_period_mode()


    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):
        tk.Label(
            self,
            text="Accounting",
            font=("Segoe UI", 16, "bold"),
            bg="white"
        ).pack(anchor="w", padx=15, pady=(5, 2))

        # ================= TC =================
        tc_frame = tk.LabelFrame(self, text="Tipo de Cambio BCCR", bg="white")
        tc_frame.pack(fill="x", padx=15, pady=(5, 10))

        tk.Label(tc_frame, text="TC", bg="white").grid(row=0, column=0, padx=5)
        tk.Entry(
            tc_frame,
            textvariable=self.tc_rate_var,
            width=12,
            state="readonly",
            justify="right"
        ).grid(row=0, column=1)

        tk.Label(tc_frame, text="Fecha", bg="white").grid(row=0, column=2, padx=5)
        tk.Entry(
            tc_frame,
            textvariable=self.tc_date_var,
            width=12,
            state="readonly",
            justify="center"
        ).grid(row=0, column=3)

        ttk.Button(
            tc_frame,
            text="Buscar TC",
            command=self._on_fetch_tc
        ).grid(row=0, column=4, padx=10)

        # ================= FILTROS =================
        filter_frame = tk.LabelFrame(self, text="Filtros contables", bg="white")
        filter_frame.pack(fill="x", padx=15, pady=10)

        # -------- MODO DE BÚSQUEDA --------
        tk.Label(filter_frame, text="Buscar por", bg="white").grid(row=0, column=0, sticky="w")

        ttk.Radiobutton(
            filter_frame,
            text="Periodo",
            variable=self.search_mode,
            value="SINGLE",
            command=self._toggle_period_mode
        ).grid(row=0, column=1, padx=5)

        ttk.Radiobutton(
            filter_frame,
            text="Rango",
            variable=self.search_mode,
            value="RANGE",
            command=self._toggle_period_mode
        ).grid(row=0, column=2, padx=5)

        # -------- PERIODO ÚNICO --------
        tk.Label(filter_frame, text="Periodo", bg="white").grid(row=0, column=3)
        self.cmb_period = ttk.Combobox(
            filter_frame,
            values=self.periods,
            width=10,
            state="readonly"
        )
        self.cmb_period.grid(row=0, column=4, padx=5)
        self.cmb_period.set(self.current_period)

        # -------- RANGO --------
        tk.Label(filter_frame, text="Desde", bg="white").grid(row=0, column=5)
        self.cmb_period_from = ttk.Combobox(
            filter_frame,
            values=self.periods,
            width=10,
            state="readonly",
            textvariable=self.period_from
        )
        self.cmb_period_from.grid(row=0, column=6, padx=5)

        tk.Label(filter_frame, text="Hasta", bg="white").grid(row=0, column=7)
        self.cmb_period_to = ttk.Combobox(
            filter_frame,
            values=self.periods,
            width=10,
            state="readonly",
            textvariable=self.period_to
        )
        self.cmb_period_to.grid(row=0, column=8, padx=5)

        # -------- ORIGEN --------
        tk.Label(filter_frame, text="Origen", bg="white").grid(row=1, column=0)
        self.cmb_source = ttk.Combobox(
            filter_frame,
            values=["TODOS", "ITP", "COLLECTIONS", "INVOICING", "MANUAL", "CASH_APP"],
            width=15,
            state="readonly"
        )
        self.cmb_source.grid(row=1, column=1, columnspan=2, padx=5)
        self.cmb_source.set("TODOS")

        # -------- CUENTA --------
        tk.Label(filter_frame, text="Cuenta", bg="white").grid(row=1, column=3)
        self.cmb_account = ttk.Combobox(
            filter_frame,
            values=["TODOS"],
            width=35,
            state="readonly"
        )
        self.cmb_account.grid(row=1, column=4, columnspan=3, padx=5)
        self.cmb_account.set("TODOS")
        self.cmb_account.bind("<Button-1>", self._lazy_load_accounts)

        # -------- BOTONES --------
        ttk.Button(
            filter_frame,
            text="Buscar",
            command=self._on_search
        ).grid(row=1, column=7, padx=10)

        export_btn = ttk.Menubutton(filter_frame, text="Exportar")
        export_menu = tk.Menu(export_btn, tearoff=0)
        export_menu.add_command(label="CSV", command=self._export_csv)
        export_menu.add_command(label="Excel", command=self._export_excel)
        export_btn["menu"] = export_menu
        export_btn.grid(row=1, column=8, padx=5)

        ttk.Button(
            filter_frame,
            text="Financial Report mensual",
            command=self._open_monthly_financial_report
        ).grid(row=1, column=9, padx=5)

        # ================= ACCIONES =================
        actions_btn = ttk.Menubutton(filter_frame, text="Acciones")
        actions_menu = tk.Menu(actions_btn, tearoff=0)

        actions_menu.add_command(
            label="📘 Mayorizar / Cierre contable",
            command=self._open_closing_wizard
        )

        actions_menu.add_separator()

        actions_menu.add_command(
            label="Asiento manual",
            command=self._open_manual_entry
        )

        actions_menu.add_command(
            label="Catálogo maestro de cuentas",
            command=self._open_chart_of_accounts
        )


        actions_menu.add_command(
            label="✏️ Ajustar asiento",
            command=self._adjust_selected_entry
        )

        actions_menu.add_command(
            label="🔁 Reversar asiento",
            command=self._reverse_selected_entry
        )

        actions_menu.add_separator()

        # -------- Declaraciones --------
        declarations_menu = tk.Menu(actions_menu, tearoff=0)

        declarations_menu.add_command(
            label="D-150 – Impuesto al Valor Agregado",
            command=self._open_d150
        )

        declarations_menu.add_command(
            label="D-101 – Declaración de Renta",
            command=lambda: messagebox.showinfo(
                "Pendiente",
                "D-101 aún no implementado."
            )
        )

        declarations_menu.add_command(
            label="D-270 – Gastos sin comprobante",
            command=lambda: messagebox.showinfo(
                "Pendiente",
                "D-270 aún no implementado."
            )
        )

        actions_menu.add_cascade(
            label="Declaraciones",
            menu=declarations_menu
        )

        # -------- Reportes --------
        reports_menu = tk.Menu(actions_menu, tearoff=0)

        reports_menu.add_command(
            label="Asientos",
            command=lambda: self._open_report("Asientos")
        )
        reports_menu.add_command(
            label="Libro Mayor",
            command=lambda: self._open_report("Libro Mayor")
        )
        reports_menu.add_command(
            label="Balance de Comprobación",
            command=lambda: self._open_report("Balance de Comprobación")
        )
        reports_menu.add_command(
            label="Estado de Situación Financiera",
            command=lambda: self._open_report("Estado de Situación Financiera")
        )
        reports_menu.add_command(
            label="Estado de Resultados",
            command=lambda: self._open_report("Estado de Resultados")
        )
        reports_menu.add_command(
            label="Flujo de Caja",
            command=lambda: self._open_report("Flujo de Caja")
        )
        reports_menu.add_separator()
        reports_menu.add_command(
            label="Financial Report mensual",
            command=self._open_monthly_financial_report
        )

        actions_menu.add_cascade(
            label="Reportes",
            menu=reports_menu
        )

        actions_btn["menu"] = actions_menu
        actions_btn.grid(row=1, column=10, padx=5)


        # ================= KPI =================
        kpi_frame = tk.Frame(self, bg="white")
        kpi_frame.pack(fill="x", padx=15)

        self._draw_kpi(kpi_frame, "Total Debe", self.kpi_debit_var, 0)
        self._draw_kpi(kpi_frame, "Total Haber", self.kpi_credit_var, 1)
        self._draw_kpi(kpi_frame, "IVA", self.kpi_iva_var, 2)

        self.lazy_container = tk.Frame(self, bg="white")

    # ============================================================
    # REPORTES
    # ============================================================
    def _open_report(self, report_name: str):
        popup = PopupReportSelector(
            self,
            ledger="0L"
        )

        report_map = {
            "Asientos": "ASIENTOS",
            "Libro Mayor": "MAYOR",
            "Balance de Comprobación": "BC",
            "Estado de Situación Financiera": "ESF",
            "Estado de Resultados": "ER",
            "Flujo de Caja": "FC"
        }

        code = report_map.get(report_name)
        if code:
            popup.report_var.set(code)

    def _open_monthly_financial_report(self):
        from Modulos.Finanzas.sections.Accounting.popups.popup_monthly_financial_report import (
            PopupMonthlyFinancialReport
        )
        PopupMonthlyFinancialReport(self)

    # ============================================================
    # HELPERS (ÚNICA ADICIÓN)
    # ============================================================
    def _build_period_list(self):
        """
        Construye lista de periodos YYYY-MM desde la DB.
        Solo muestra periodos con movimientos contables reales.
        """
        today_period = date.today().strftime("%Y-%m")
        periods = []
        try:
            periods = get_accounting_periods_api()
        except Exception:
            periods = []

        clean = []
        for period in periods or []:
            value = str(period or "").strip()
            if len(value) == 7 and value[4] == "-" and value <= today_period:
                clean.append(value)

        clean = sorted(set(clean))
        return clean or [today_period]


    def _on_fetch_tc(self):
        """
        Obtiene el tipo de cambio del día desde BCCR vía API
        y actualiza los campos TC y Fecha.
        """
        try:
            data = get_exchange_rate_today_api()

            self.tc_rate_var.set(f"{float(data['rate']):,.2f}")
            self.tc_date_var.set(to_long_english_date(data["date"]))

        except Exception as e:
            messagebox.showerror(
                "Tipo de Cambio",
                f"Error obteniendo tipo de cambio:\n{str(e)}"
            )
            self.tc_rate_var.set("")
            self.tc_date_var.set("")

    def _lazy_load_accounts(self, event=None):
        """
        Carga el catálogo contable SOLO una vez
        al hacer click en el combobox de cuentas.
        """
        if self.accounts_loaded:
            return

        try:
            accounts = get_accounting_accounts_api()

            values = ["TODOS"]
            for acc in accounts:
                label = f"{acc['account_code']} - {acc['account_name']}"
                values.append(label)
                self.account_map[label] = acc["account_code"]

            self.cmb_account["values"] = values
            self.accounts_loaded = True

        except Exception as e:
            messagebox.showerror(
                "Cuentas contables",
                f"Error cargando cuentas:\n{str(e)}"
            )


    def _on_search(self):
        """
        Ejecuta la búsqueda contable según filtros seleccionados
        y carga la tabla de asientos / mayor.
        """

        if not self.tc_rate_var.get():
            messagebox.showwarning(
                "Tipo de cambio requerido",
                "Debe obtener el Tipo de Cambio antes de continuar."
            )
            return

        # ============================================================
        # 🔥 SINCRONIZAR ASIENTOS ANTES DE CONSULTAR LEDGER
        # ============================================================
        try:
            from api_client import (
                post_accounting_sync_collections_api,
                post_accounting_sync_cash_app_api,
                post_accounting_sync_itp_api,
                post_accounting_sync_payroll_api 
            )

            post_accounting_sync_collections_api()
            post_accounting_sync_cash_app_api()
            post_accounting_sync_itp_api()
            post_accounting_sync_payroll_api() 

        except Exception as e:
            messagebox.showerror(
                "Sincronización contable",
                f"Error sincronizando asientos:\n{str(e)}"
            )
            return

        # ============================================================
        # FILTROS COMUNES
        # ============================================================
        origin = None
        if self.cmb_source.get() != "TODOS":
            origin = self.cmb_source.get()

        account_code = None
        if self.cmb_account.get() != "TODOS":
            account_code = self.account_map.get(self.cmb_account.get())

        # ============================================================
        # PERIODO / RANGO (BACKEND SAFE)
        # ============================================================
        period = None

        if self.search_mode.get() == "SINGLE":
            period = self.cmb_period.get()

        else:
            period_from = self.period_from.get()
            period_to = self.period_to.get()

            if not period_from or not period_to:
                messagebox.showwarning(
                    "Rango incompleto",
                    "Debe seleccionar período inicial y final."
                )
                return

            if period_from > period_to:
                messagebox.showwarning(
                    "Rango inválido",
                    "El período inicial no puede ser mayor al final."
                )
                return

            # 🔥 RANGO REAL:
            # NO enviamos period → backend devuelve TODOS los periodos
            period = None

        # ============================================================
        # TABLA
        # ============================================================
        if not self.lazy_container.winfo_ismapped():
            self.lazy_container.pack(fill="both", expand=True, padx=15, pady=5)
            self.table = AccountingTable(self.lazy_container)
            self.table.pack(fill="both", expand=True)
        else:
            # 🔒 CLEAR BLINDADO (SIN TOCAR AccountingTable)
            if hasattr(self.table, "tree"):
                self.table.tree.delete(*self.table.tree.get_children())

        self.table.load_from_api(
            period=period,
            period_from=period_from if self.search_mode.get() == "RANGE" else None,
            period_to=period_to if self.search_mode.get() == "RANGE" else None,
            origin=origin,
            account_code=account_code
        )

        # ============================================================
        # KPIs
        # ============================================================
        debit, credit = self.table.get_totals()
        self.kpi_debit_var.set(f"{debit:,.2f}")
        self.kpi_credit_var.set(f"{credit:,.2f}")

        # ============================================================
        # IVA (ÚLTIMO PERIODO DEL RANGO)
        # ============================================================
        try:
            iva_period = (
                self.cmb_period.get()
                if self.search_mode.get() == "SINGLE"
                else self.period_to.get()
            )
            iva = get_accounting_iva_api(iva_period)
            self.kpi_iva_var.set(f"{iva.get('iva_total', 0):,.2f}")
        except Exception:
            self.kpi_iva_var.set("0.00")


    def _toggle_period_mode(self):
        """
        Alterna entre búsqueda por periodo único y rango
        """
        if self.search_mode.get() == "SINGLE":
            self.cmb_period.configure(state="readonly")
            self.cmb_period_from.configure(state="disabled")
            self.cmb_period_to.configure(state="disabled")
        else:
            self.cmb_period.configure(state="disabled")
            self.cmb_period_from.configure(state="readonly")
            self.cmb_period_to.configure(state="readonly")

    # ============================================================
    # EXPORTS
    # ============================================================
    def _export_csv(self):
        """
        Exporta la tabla actual a CSV.
        """
        if not self.table:
            messagebox.showwarning(
                "Exportar",
                "No hay datos cargados para exportar."
            )
            return

        try:
            self.table.export_csv()
        except Exception as e:
            messagebox.showerror(
                "Exportar CSV",
                f"Error exportando CSV:\n{str(e)}"
            )

    def _export_excel(self):
        """
        Exporta la tabla actual a Excel.
        """
        if not self.table:
            messagebox.showwarning(
                "Exportar",
                "No hay datos cargados para exportar."
            )
            return

        try:
            self.table.export_excel()
        except Exception as e:
            messagebox.showerror(
                "Exportar Excel",
                f"Error exportando Excel:\n{str(e)}"
            )

    def _open_closing_wizard(self):
        """
        Abre el wizard de cierre contable.
        """
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_closing_wizard import (
                PopupClosingWizard
            )

            PopupClosingWizard(
                self,
                company_code="MSL-CR",
                ledger="0L"
            )

        except Exception as e:
            messagebox.showerror(
                "Cierre contable",
                f"Error abriendo cierre contable:\n{str(e)}"
            )

    # ============================================================
    # ACTIONS — ASIENTOS
    # ============================================================

    # ============================================================
    # ASIENTO MANUAL
    # ============================================================
    def _open_manual_entry(self):
        """
        Abre el popup para crear un asiento contable manual.
        """

        try:

            from Modulos.Finanzas.sections.Accounting.popups.popup_manual_entry import PopupManualEntry

            PopupManualEntry(
                self,
                on_success=lambda: self.event_generate("<<ReloadAccounting>>")
            )

        except Exception as e:

            messagebox.showerror(
                "Asiento manual",
                f"Error abriendo popup:\n{str(e)}"
            )

    def _open_chart_of_accounts(self):
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_chart_of_accounts import PopupChartOfAccounts
            PopupChartOfAccounts(self)
        except Exception as exc:
            messagebox.showerror("Catálogo contable", str(exc))


    def _adjust_selected_entry(self):
        """
        Abre popup de ajuste del asiento seleccionado.
        """
        if not self.table:
            messagebox.showwarning(
                "Ajustar asiento",
                "No hay asientos cargados."
            )
            return

        try:
            self.table._edit_entry()
        except Exception as e:
            messagebox.showerror(
                "Ajustar asiento",
                str(e)
            )

    def _reverse_selected_entry(self):
        """
        Reversa el asiento seleccionado.
        """
        if not self.table:
            messagebox.showwarning(
                "Reversar asiento",
                "No hay asientos cargados."
            )
            return

        try:
            self.table._reverse_entry()
        except Exception as e:
            messagebox.showerror(
                "Reversar asiento",
                str(e)
            )

    # ============================================================
    # DECLARACIONES
    # ============================================================
    def _open_d150(self):
        """
        Abre el popup de declaración D-150.
        """
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_d150 import PopupD150
            PopupD150(self, period=self.cmb_period.get())
        except Exception as e:
            messagebox.showerror(
                "D-150",
                f"Error abriendo D-150:\n{str(e)}"
            )

    # ============================================================
    # HELPERS UI
    # ============================================================
    def _reload_table_only(self):
        """
        Recarga la tabla contable sin reconstruir UI.
        """
        if self.table:
            self.table.load_from_api(
                period=self.cmb_period.get()
            )

    def _check_month_open_alert(self):
        """
        Muestra alerta al inicio del mes contable.
        """
        if date.today().day <= 2:
            messagebox.showinfo(
                "Revisión contable",
                "Inicio de mes detectado.\n\n"
                "Revise los asientos del periodo anterior antes del cierre."
            )

    def _draw_kpi(self, parent, title, var, col):
        """
        Dibuja un KPI simple en pantalla.
        """
        frame = tk.LabelFrame(parent, text=title, bg="white")
        frame.grid(row=0, column=col, padx=10, sticky="w")

        tk.Label(
            frame,
            textvariable=var,
            font=("Segoe UI", 12, "bold"),
            bg="white"
        ).pack(padx=15, pady=5)



    # ============================================================
    # (RESTO DEL ARCHIVO SIN CAMBIOS)
    # ============================================================
