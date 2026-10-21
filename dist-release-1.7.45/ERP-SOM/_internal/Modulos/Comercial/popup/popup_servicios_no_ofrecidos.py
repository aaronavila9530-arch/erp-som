# =========================================================
# POPUP — SERVICIOS NO OFRECIDOS (ERP-SOM)
# =========================================================
import tkinter as tk
from tkinter import ttk, Menu, messagebox, filedialog
import csv
import pandas as pd

from api_client import get_comercial_servicios_no_ofrecidos_api


class PopupServiciosNoOfrecidos(tk.Toplevel):
    """
    Popup ejecutivo para visualizar servicios NO ofrecidos
    con filtros reales por Año / Rango / Quarter.
    """

    def __init__(self, parent, data=None, filters=None):
        super().__init__(parent)

        self.parent = parent
        self.data = data or []
        self.filters = filters or {}

        self.title("Servicios NO Ofrecidos")
        self.geometry("980x620")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_table()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ================= VARIABLES =================
        self.year_mode_var = tk.StringVar(value="EXACTO")
        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()
        self.quarter_from_var = tk.StringVar()
        self.quarter_to_var = tk.StringVar()

        # ================= HEADER =================
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=6)

        ttk.Label(
            header,
            text="Servicios NO Ofrecidos",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")

        # ================= FILTER BAR =================
        filtros = ttk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=10, pady=6)

        ttk.Label(filtros, text="Modo Año").grid(row=0, column=0, padx=4, sticky="w")
        cb_mode = ttk.Combobox(
            filtros,
            textvariable=self.year_mode_var,
            values=["EXACTO", "RANGO"],
            width=10,
            state="readonly"
        )
        cb_mode.grid(row=0, column=1, padx=4)
        cb_mode.bind("<<ComboboxSelected>>", lambda e: self._on_year_mode_change())

        ttk.Label(filtros, text="Año desde").grid(row=0, column=2, padx=4, sticky="w")
        ttk.Entry(filtros, textvariable=self.year_from_var, width=8).grid(
            row=0, column=3, padx=4
        )

        ttk.Label(filtros, text="Año hasta").grid(row=0, column=4, padx=4, sticky="w")
        self.entry_year_to = ttk.Entry(
            filtros, textvariable=self.year_to_var, width=8
        )
        self.entry_year_to.grid(row=0, column=5, padx=4)

        ttk.Label(filtros, text="Quarter desde").grid(row=0, column=6, padx=4, sticky="w")
        ttk.Combobox(
            filtros,
            textvariable=self.quarter_from_var,
            values=["", "Q1", "Q2", "Q3", "Q4"],
            width=6,
            state="readonly"
        ).grid(row=0, column=7, padx=4)

        ttk.Label(filtros, text="Quarter hasta").grid(row=0, column=8, padx=4, sticky="w")
        ttk.Combobox(
            filtros,
            textvariable=self.quarter_to_var,
            values=["", "Q1", "Q2", "Q3", "Q4"],
            width=6,
            state="readonly"
        ).grid(row=0, column=9, padx=4)

        ttk.Button(
            filtros,
            text="Aplicar",
            command=self._buscar
        ).grid(row=0, column=10, padx=8)

        ttk.Button(
            filtros,
            text="Limpiar",
            command=self._limpiar
        ).grid(row=0, column=11, padx=4)

        # ================= TABLE =================
        frame = ttk.LabelFrame(self, text="Servicios del Catálogo NO Ejecutados")
        frame.pack(fill="both", expand=True, padx=10, pady=6)

        cols = ("codigo", "codigoprod", "servicio", "costo_base")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")

        headers = {
            "codigo": "Código",
            "codigoprod": "Código Prod.",
            "servicio": "Servicio",
            "costo_base": "Costo Base"
        }

        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, anchor="center", width=200)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ================= FOOTER =================
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=10, pady=6)

        self.total_lbl = ttk.Label(
            footer,
            text="Total servicios NO ofrecidos: 0",
            font=("Segoe UI", 9, "bold")
        )
        self.total_lbl.pack(side="left")

        btn_export = ttk.Button(footer, text="Exportar ▼")
        btn_export.pack(side="right")

        menu = Menu(btn_export, tearoff=0)
        menu.add_command(label="Exportar CSV", command=self._export_csv)
        menu.add_command(label="Exportar Excel", command=self._export_excel)
        btn_export.bind("<Button-1>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        self._on_year_mode_change()

    # =========================================================
    # LOGIC
    # =========================================================
    def _on_year_mode_change(self):
        if self.year_mode_var.get() == "EXACTO":
            self.year_to_var.set(self.year_from_var.get())
            self.entry_year_to.configure(state="disabled")
        else:
            self.entry_year_to.configure(state="normal")

    def _buscar(self):
        try:
            yf = int(self.year_from_var.get()) if self.year_from_var.get() else None
            yt = int(self.year_to_var.get()) if self.year_to_var.get() else None

            q_from = self.quarter_from_var.get()
            q_to = self.quarter_to_var.get()

            quarter = q_from if q_from and not q_to else None

            resp = get_comercial_servicios_no_ofrecidos_api(
                year_from=yf,
                year_to=yt,
                quarter=quarter
            )

            self.data = resp.get("data", []) or []
            self._load_table()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _limpiar(self):
        self.year_from_var.set("")
        self.year_to_var.set("")
        self.quarter_from_var.set("")
        self.quarter_to_var.set("")
        self.data = []
        self._load_table()

    def _load_table(self):
        self.tree.delete(*self.tree.get_children())

        for r in self.data:
            self.tree.insert("", "end", values=(
                r.get("codigo"),
                r.get("codigoprod"),
                r.get("servicio"),
                f"{float(r.get('costo_base') or 0):,.2f}"
            ))

        self.total_lbl.config(
            text=f"Total servicios NO ofrecidos: {len(self.data)}"
        )

    # =========================================================
    # EXPORTS
    # =========================================================
    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Código", "Código Prod.", "Servicio", "Costo Base"])
            for r in self.data:
                writer.writerow([
                    r.get("codigo"),
                    r.get("codigoprod"),
                    r.get("servicio"),
                    r.get("costo_base")
                ])

    def _export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if not path:
            return

        pd.DataFrame(self.data).to_excel(path, index=False)
