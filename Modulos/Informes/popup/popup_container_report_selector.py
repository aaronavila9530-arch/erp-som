import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_container_report_filters_api,
    get_container_report_months_api,
    get_container_report_vessels_api,
    get_container_reports_by_servicio_api
)


class PopupContainerReportSelector(tk.Toplevel):
    """
    POPUP — Container Report Selector
    Selección controlada de servicios con num_informe
    """

    def __init__(self, parent, on_select):
        super().__init__(parent)

        self.parent = parent
        self.on_select = on_select

        self.title("Select Service Report")
        self.geometry("900x480")
        self.transient(parent)
        self.grab_set()

        # =====================================================
        # STATE
        # =====================================================
        self.client_var = tk.StringVar()
        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.vessel_var = tk.StringVar()

        # =====================================================
        # BUILD UI
        # =====================================================
        self._build_filters()
        self._build_actions()
        self._build_table()

        # =====================================================
        # LOAD BASE FILTERS
        # =====================================================
        self._load_base_filters()

    # =========================================================
    # UI — FILTERS
    # =========================================================
    def _build_filters(self):

        frm = ttk.LabelFrame(self, text="Filters")
        frm.pack(fill="x", padx=10, pady=10)

        ttk.Label(frm, text="Client").grid(row=0, column=0, sticky="w")
        self.cb_client = ttk.Combobox(
            frm, textvariable=self.client_var, width=28, state="readonly"
        )
        self.cb_client.grid(row=0, column=1, padx=5)

        ttk.Label(frm, text="Year").grid(row=0, column=2, sticky="w")
        self.cb_year = ttk.Combobox(
            frm, textvariable=self.year_var, width=10, state="readonly"
        )
        self.cb_year.grid(row=0, column=3, padx=5)

        ttk.Label(frm, text="Month").grid(row=1, column=0, sticky="w")
        self.cb_month = ttk.Combobox(
            frm, textvariable=self.month_var, width=10, state="readonly"
        )
        self.cb_month.grid(row=1, column=1, padx=5)

        ttk.Label(frm, text="Vessel / Container").grid(row=1, column=2, sticky="w")
        self.cb_vessel = ttk.Combobox(
            frm, textvariable=self.vessel_var, width=28, state="readonly"
        )
        self.cb_vessel.grid(row=1, column=3, padx=5)

        self.cb_client.bind("<<ComboboxSelected>>", self._on_client_year_change)
        self.cb_year.bind("<<ComboboxSelected>>", self._on_client_year_change)
        self.cb_month.bind("<<ComboboxSelected>>", self._on_month_change)

    # =========================================================
    # UI — ACTIONS
    # =========================================================
    def _build_actions(self):

        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(
            frm,
            text="🔍 Search",
            command=self._search_reports
        ).pack(side="left")

        ttk.Button(
            frm,
            text="Use selected report",
            command=self._confirm_selection
        ).pack(side="right")

    # =========================================================
    # UI — TABLE
    # =========================================================
    def _build_table(self):

        self.tree = ttk.Treeview(
            self,
            columns=("num", "client", "vessel", "year", "month"),
            show="headings",
            height=12
        )

        self.tree.heading("num", text="Report Number")
        self.tree.heading("client", text="Client")
        self.tree.heading("vessel", text="Vessel / Container")
        self.tree.heading("year", text="Year")
        self.tree.heading("month", text="Month")

        self.tree.column("num", width=180)
        self.tree.column("client", width=200)
        self.tree.column("vessel", width=200)
        self.tree.column("year", width=80, anchor="center")
        self.tree.column("month", width=80, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # =========================================================
    # DATA — LOAD BASE FILTERS
    # =========================================================
    def _load_base_filters(self):

        data = get_container_report_filters_api()

        self.cb_client["values"] = data.get("clientes", [])
        self.cb_year["values"] = [str(y) for y in data.get("anios", [])]

    # =========================================================
    # DATA — CLIENT / YEAR CHANGE
    # =========================================================
    def _on_client_year_change(self, event=None):

        self.cb_month["values"] = []
        self.cb_vessel["values"] = []
        self.month_var.set("")
        self.vessel_var.set("")

        if not all([self.client_var.get(), self.year_var.get()]):
            return

        months = get_container_report_months_api(
            cliente=self.client_var.get(),
            anio=int(self.year_var.get())
        )

        self.cb_month["values"] = [str(m) for m in months]

    # =========================================================
    # DATA — MONTH CHANGE
    # =========================================================
    def _on_month_change(self, event=None):

        self.cb_vessel["values"] = []
        self.vessel_var.set("")

        if not all([
            self.client_var.get(),
            self.year_var.get(),
            self.month_var.get()
        ]):
            return

        vessels = get_container_report_vessels_api(
            cliente=self.client_var.get(),
            anio=int(self.year_var.get()),
            mes=int(self.month_var.get())
        )

        self.cb_vessel["values"] = vessels

    # =========================================================
    # DATA — SEARCH REPORTS
    # =========================================================
    def _search_reports(self):

        self.tree.delete(*self.tree.get_children())

        if not all([
            self.client_var.get(),
            self.year_var.get(),
            self.month_var.get(),
            self.vessel_var.get()
        ]):
            messagebox.showwarning(
                "Search",
                "Please complete all filters before searching."
            )
            return

        resp = get_container_reports_by_servicio_api(
            cliente=self.client_var.get(),
            buque_contenedor=self.vessel_var.get(),
            anio=int(self.year_var.get()),
            mes=int(self.month_var.get())
        )

        for r in resp.get("data", []):
            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("num_informe"),
                    self.client_var.get(),
                    self.vessel_var.get(),
                    self.year_var.get(),
                    self.month_var.get()
                )
            )

    # =========================================================
    # CONFIRM SELECTION
    # =========================================================
    def _confirm_selection(self):

        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Select",
                "Please select a report."
            )
            return

        value = self.tree.item(sel[0], "values")[0]

        if callable(self.on_select):
            self.on_select(value)

        self.destroy()
