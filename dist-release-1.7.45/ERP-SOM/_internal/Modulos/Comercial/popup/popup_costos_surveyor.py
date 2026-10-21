# ============================================================
# POPUP — COSTOS POR SURVEYOR (PARETO 80/20)
# ============================================================

import tkinter as tk
from tkinter import ttk, Menu, filedialog, messagebox
import csv
import pandas as pd
from datetime import datetime


class PopupCostosSurveyor(tk.Toplevel):
    """
    Popup ejecutivo para análisis de costos por Surveyor
    con Pareto 80/20
    """

    def __init__(self, parent, data, filters=None):
        super().__init__(parent)

        self.parent = parent
        self.data_original = data or []
        self.data = list(self.data_original)
        self.filters = filters or {}

        self.title("Costos por Surveyor — Pareto 80/20")
        self.geometry("1100x600")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ================= VARIABLES =================
        self.surveyor_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()

        self.year_mode_var = tk.StringVar(value="EXACTO")
        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()

        # 🔹 NUEVO: Quarter
        self.quarter_var = tk.StringVar()

        # ---------------- HEADER ----------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=6)

        ttk.Label(
            header,
            text="Costos por Surveyor — Pareto 80/20",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")

        # ---------------- SUBTITLE ----------------
        self.subtitle_lbl = ttk.Label(
            self,
            text=self._build_filter_text(),
            font=("Segoe UI", 9),
            foreground="#555"
        )
        self.subtitle_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        # ---------------- FILTER BAR ----------------
        filter_bar = ttk.LabelFrame(self, text="Filtros")
        filter_bar.pack(fill="x", padx=10, pady=6)

        # ---- LOCAL FILTERS (DATA) ----
        fields = [
            ("Surveyor", self.surveyor_var, self._unique("surveyor")),
            ("Continente", self.continente_var, self._unique("continente")),
            ("País", self.pais_var, self._unique("pais")),
            ("Puerto", self.puerto_var, self._unique("puerto")),
        ]

        col = 0
        for lbl, var, values in fields:
            ttk.Label(filter_bar, text=lbl).grid(row=0, column=col, padx=4)
            ttk.Combobox(
                filter_bar,
                textvariable=var,
                values=values,
                state="readonly",
                width=18
            ).grid(row=1, column=col, padx=4)
            col += 1

        # ---- YEAR MODE ----
        ttk.Label(filter_bar, text="Modo Año").grid(row=0, column=col, padx=6)
        ttk.Combobox(
            filter_bar,
            textvariable=self.year_mode_var,
            values=["EXACTO", "RANGO"],
            state="readonly",
            width=10
        ).grid(row=1, column=col, padx=6)
        col += 1

        # ---- YEARS (BACKEND META) ----
        raw_years = self.filters.get("available_years") or []
        years = sorted({str(int(y)) for y in raw_years if y})

        current_year = str(self.filters.get("year") or datetime.now().year)

        ttk.Label(filter_bar, text="Año desde").grid(row=0, column=col, padx=4)
        ttk.Combobox(
            filter_bar,
            textvariable=self.year_from_var,
            values=years,
            state="readonly",
            width=8
        ).grid(row=1, column=col, padx=4)
        col += 1

        ttk.Label(filter_bar, text="Año hasta").grid(row=0, column=col, padx=4)
        ttk.Combobox(
            filter_bar,
            textvariable=self.year_to_var,
            values=years,
            state="readonly",
            width=8
        ).grid(row=1, column=col, padx=4)
        col += 1

        # 🔹 NUEVO: QUARTER
        ttk.Label(filter_bar, text="Quarter").grid(row=0, column=col, padx=4)
        ttk.Combobox(
            filter_bar,
            textvariable=self.quarter_var,
            values=["Q1", "Q2", "Q3", "Q4"],
            state="readonly",
            width=6
        ).grid(row=1, column=col, padx=4)
        col += 1

        # Preselección segura del año
        if current_year in years:
            self.year_from_var.set(current_year)
            self.year_to_var.set(current_year)

        ttk.Button(filter_bar, text="Aplicar", command=self._apply_filters)\
            .grid(row=1, column=col, padx=10)

        ttk.Button(filter_bar, text="Limpiar", command=self._clear_filters)\
            .grid(row=1, column=col + 1)

        # ---------------- TABLE ----------------
        frame = ttk.LabelFrame(self, text="Detalle por Surveyor")
        frame.pack(fill="both", expand=True, padx=10, pady=6)

        cols = (
            "surveyor", "continente", "pais", "puerto",
            "total_servicios", "honorarios_total",
            "acumulado_pct", "es_pareto_80"
        )

        self.tree = ttk.Treeview(frame, columns=cols, show="headings")

        headers = {
            "surveyor": "Surveyor",
            "continente": "Continente",
            "pais": "País",
            "puerto": "Puerto",
            "total_servicios": "Servicios",
            "honorarios_total": "Honorarios",
            "acumulado_pct": "% Acumulado",
            "es_pareto_80": "Pareto 80%"
        }

        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, anchor="center", width=140)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._load_table()

    # =========================================================
    # FILTERING
    # =========================================================
    def _apply_filters(self):

        def _quarter_ok():
            """
            Quarter NO es por fila.
            Si el quarter existe en el período (backend),
            se permite mostrar data.
            """
            q = (self.quarter_var.get() or "").strip()
            if not q:
                return True

            available = self.filters.get("available_quarters") or []
            return q in available

        # Si el quarter no aplica al período → tabla vacía
        if not _quarter_ok():
            self.data = []
            self._refresh()
            return

        self.data = [
            r for r in self.data_original
            if (not self.surveyor_var.get() or r.get("surveyor") == self.surveyor_var.get())
            and (not self.continente_var.get() or r.get("continente") == self.continente_var.get())
            and (not self.pais_var.get() or r.get("pais") == self.pais_var.get())
            and (not self.puerto_var.get() or r.get("puerto") == self.puerto_var.get())
        ]

        self._refresh()

    def _clear_filters(self):
        for v in (
            self.surveyor_var, self.continente_var,
            self.pais_var, self.puerto_var,
            self.year_from_var, self.year_to_var,
            self.quarter_var
        ):
            v.set("")

        self.year_mode_var.set("EXACTO")
        self.data = list(self.data_original)
        self._refresh()

    def _refresh(self):
        self._load_table()
        self.subtitle_lbl.config(text=self._build_filter_text())

    # =========================================================
    # HELPERS
    # =========================================================
    def _unique(self, key):
        return sorted({r.get(key) for r in self.data_original if r.get(key)})

    def _build_filter_text(self):
        parts = []

        if self.year_from_var.get():
            parts.append(
                f"Año: {self.year_from_var.get()}"
                f"{'–' + self.year_to_var.get() if self.year_to_var.get() else ''}"
            )

        if self.quarter_var.get():
            parts.append(f"Quarter: {self.quarter_var.get()}")

        return " | ".join(parts) if parts else "Sin filtros aplicados"

    def _load_table(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.data:
            self.tree.insert("", "end", values=(
                r.get("surveyor"),
                r.get("continente"),
                r.get("pais"),
                r.get("puerto"),
                r.get("total_servicios"),
                f"{float(r.get('honorarios_total', 0)):,.2f}",
                f"{float(r.get('acumulado_pct', 0)):,.2f}%",
                "✔" if r.get("es_pareto_80") else ""
            ))
