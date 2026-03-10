import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

from api_client import (
    get_payslips_api,
    hr_download_payslip_pdf
)


class VistaColillasEmployee(ttk.Frame):

    def __init__(self, parent, empleado_id=None):
        super().__init__(parent)

        self.parent = parent
        self.empleado_id = empleado_id

        self.page = 1
        self.page_size = 20
        self.data = []

        self._build_ui()
        self._load_data()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        ttk.Label(
            self,
            text="Colillas de Pago",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)

        # -------------------------
        # FILTROS
        # -------------------------
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Usuario").grid(row=0, column=0, sticky="w")
        ttk.Label(filtros, text="Año").grid(row=0, column=1, sticky="w")
        ttk.Label(filtros, text="Mes").grid(row=0, column=2, sticky="w")

        self.cmb_usuario = ttk.Combobox(filtros, width=20, state="readonly")
        self.cmb_year = ttk.Combobox(filtros, width=10, state="readonly")
        self.cmb_month = ttk.Combobox(filtros, width=10, state="readonly")

        self.cmb_usuario.grid(row=1, column=0, padx=5)
        self.cmb_year.grid(row=1, column=1, padx=5)
        self.cmb_month.grid(row=1, column=2, padx=5)

        ttk.Button(
            filtros,
            text="Buscar",
            command=self._buscar
        ).grid(row=1, column=3, padx=10)

        ttk.Button(
            filtros,
            text="Descargar colilla",
            command=self._descargar_colilla
        ).grid(row=1, column=4, padx=10)

        # -------------------------
        # TABLA
        # -------------------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "id",
            "usuario",
            "year",
            "month",
            "salario_neto",
            "generado_por"
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "ID",
            "usuario": "Usuario",
            "year": "Año",
            "month": "Mes",
            "salario_neto": "Salario Neto",
            "generado_por": "Generado por"
        }

        for col, text in headings.items():
            self.table.heading(col, text=text)
            self.table.column(col, width=120, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)

        self.table.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # -------------------------
        # PAGINADO
        # -------------------------
        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=5)

        ttk.Button(pag, text="◀ Anterior", command=self._prev).pack(side="left")
        ttk.Button(pag, text="Siguiente ▶", command=self._next).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _load_data(self):

        resp = get_payslips_api(
            page=self.page,
            page_size=self.page_size,
            year=self._get_year(),
            month=self._get_month()
        )

        self.data = resp.get("data", [])
        self._render_table()
        self._load_filters()

    def _render_table(self):

        self.table.delete(*self.table.get_children())

        for r in self.data:
            self.table.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["usuario"],
                    r["year"],
                    r["month"],
                    f"{float(r['salario_neto']):,.2f}",
                    r["generado_por"]
                )
            )

    # =========================================================
    # FILTROS
    # =========================================================
    def _load_filters(self):

        usuarios = sorted(set(r["usuario"] for r in self.data))
        years = sorted(set(r["year"] for r in self.data))
        months = sorted(set(r["month"] for r in self.data))

        self.cmb_usuario["values"] = [""] + usuarios
        self.cmb_year["values"] = [""] + years
        self.cmb_month["values"] = [""] + months

    def _get_year(self):
        val = self.cmb_year.get()
        return int(val) if val.isdigit() else None

    def _get_month(self):
        val = self.cmb_month.get()
        return int(val) if val.isdigit() else None

    def _buscar(self):
        self.page = 1
        self._load_data()

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _prev(self):
        if self.page > 1:
            self.page -= 1
            self._load_data()

    def _next(self):
        self.page += 1
        self._load_data()

    # =========================================================
    # DESCARGA — PDF RECONSTRUIDO EN BACKEND
    # =========================================================
    def _descargar_colilla(self):

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning(
                "Atención",
                "Seleccione una colilla para descargar."
            )
            return

        row_index = self.table.index(selected[0])
        row = self.data[row_index]

        year = row["year"]
        month = row["month"]
        usuario = row["usuario"]

        # -------------------------
        # SAVE AS
        # -------------------------
        filename = f"COLILLA_{usuario}_{year}_{month}.pdf"

        save_path = filedialog.asksaveasfilename(
            title="Guardar colilla de pago",
            defaultextension=".pdf",
            initialfile=filename,
            filetypes=[("PDF", "*.pdf")]
        )

        if not save_path:
            return

        try:
            resp = hr_download_payslip_pdf(
                year=year,
                month=month,
                usuario=usuario
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo generar la colilla:\n{e}"
            )
            return

        try:
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar el archivo:\n{e}"
            )
            return

        messagebox.showinfo(
            "Descarga completa",
            "La colilla fue generada y descargada correctamente."
        )
