import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_draft_survey_filters_api,
    get_full_draft_survey_api
)

from Modulos.Informes.Vessel_Draft_Survey.draft_survey_form import (
    DraftSurveyForm
)


class PopupDraftSurveySelector(tk.Toplevel):
    """
    POPUP — Draft Survey Selector (Cascade Filters)

    • Combobox en cascada
    • Botón Buscar
    • Tabla de resultados
    • Botón Limpiar
    • Botón Cargar Draft
    """

    def __init__(self, parent, on_select=None):
        super().__init__(parent)

        self.parent = parent
        self.on_select = on_select  # 🔥 mantener compatibilidad

        self.title("Select Existing Draft Survey")
        self.geometry("1000x650")
        self.transient(parent)
        self.grab_set()

        self._build_filters()
        self._build_table()
        self._build_buttons()

        self._load_initial_filters()

    # =========================================================
    # BUILD FILTERS
    # =========================================================
    def _build_filters(self):

        frame = ttk.LabelFrame(self, text="Filters")
        frame.pack(fill="x", padx=10, pady=10)

        self.vars = {
            "continent": tk.StringVar(),
            "country": tk.StringVar(),
            "year": tk.StringVar(),
            "month": tk.StringVar(),
            "port": tk.StringVar(),
            "client": tk.StringVar(),
        }

        labels = {
            "continent": "Continent",
            "country": "Country",
            "year": "Year",
            "month": "Month",
            "port": "Port",
            "client": "Client"
        }

        self.comboboxes = {}

        for col, key in enumerate(self.vars):

            ttk.Label(frame, text=labels[key]).grid(row=0, column=col, padx=5, pady=5)

            cb = ttk.Combobox(
                frame,
                textvariable=self.vars[key],
                state="readonly",
                width=15
            )
            cb.grid(row=1, column=col, padx=5, pady=5)

            cb.bind("<<ComboboxSelected>>", lambda e, k=key: self._cascade(k))

            self.comboboxes[key] = cb

    # =========================================================
    # BUILD TABLE
    # =========================================================
    def _build_table(self):

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "num_informe",
            "continent",
            "country",
            "year",
            "month",
            "port",
            "client"
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=15
        )

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=130)

        self.tree.pack(fill="both", expand=True)

    # =========================================================
    # BUILD BUTTONS
    # =========================================================
    def _build_buttons(self):

        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            frame,
            text="Buscar",
            command=self._search
        ).pack(side="left", padx=5)

        ttk.Button(
            frame,
            text="Limpiar Filtros",
            command=self._clear_filters
        ).pack(side="left", padx=5)

        ttk.Button(
            frame,
            text="Cargar Draft",
            command=self._load_selected
        ).pack(side="right", padx=5)

    # =========================================================
    # LOAD INITIAL FILTERS
    # =========================================================
    def _load_initial_filters(self):

        data = get_draft_survey_filters_api()

        if not data:
            return

        for key in self.vars:
            values = data.get(f"{key}s", [])
            self.comboboxes[key]["values"] = values

    # =========================================================
    # CASCADE LOGIC
    # =========================================================
    def _cascade(self, changed_key):

        filters = {
            key: var.get() or None
            for key, var in self.vars.items()
        }

        data = get_draft_survey_filters_api(**filters)

        if not data:
            return

        for key in self.vars:
            if key != changed_key:
                values = data.get(f"{key}s", [])
                self.comboboxes[key]["values"] = values

    # =========================================================
    # SEARCH
    # =========================================================
    def _search(self):

        filters = {
            key: var.get() or None
            for key, var in self.vars.items()
        }

        data = get_draft_survey_filters_api(**filters)

        if not data:
            messagebox.showwarning("No Results", "No data found.")
            return

        self.tree.delete(*self.tree.get_children())

        reports = data.get("draft_reports", [])

        if not reports:
            messagebox.showinfo("Result", "No draft reports found.")
            return

        for report in reports:
            self.tree.insert(
                "",
                "end",
                values=(
                    report,
                    filters["continent"],
                    filters["country"],
                    filters["year"],
                    filters["month"],
                    filters["port"],
                    filters["client"]
                )
            )

    # =========================================================
    # CLEAR FILTERS
    # =========================================================
    def _clear_filters(self):

        for var in self.vars.values():
            var.set("")

        self.tree.delete(*self.tree.get_children())
        self._load_initial_filters()

    # =========================================================
    # LOAD SELECTED
    # =========================================================
    def _load_selected(self):

        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning("Selection", "Please select a draft report.")
            return

        values = self.tree.item(selected)["values"]
        draft_report_number = values[0]

        # 🔵 SI HAY CALLBACK → usarlo (flujo antiguo)
        if self.on_select:
            self.on_select(draft_report_number)
            self.destroy()
            return

        # 🟢 SI NO HAY CALLBACK → flujo automático unified
        try:
            data = get_full_draft_survey_api(str(draft_report_number))

            if not data:
                messagebox.showerror(
                    "Error",
                    "No se pudo obtener la información del Draft."
                )
                return

            self.destroy()

            for widget in self.parent.winfo_children():
                widget.destroy()

            form = DraftSurveyForm(
                self.parent,
                mode="edit",
                draft_report_number=str(draft_report_number)
            )

            form.set_payload(data)
            form.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el Draft:\n{e}"
            )