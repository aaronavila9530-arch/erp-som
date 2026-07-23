import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    get_payslips_api,
    hr_download_payslip_pdf
)


class VistaColillasEmployee(ttk.Frame):

    def __init__(self, parent, empleado_id=None, rol=None):
        super().__init__(parent)

        self.parent = parent
        self.empleado_id = empleado_id
        self.rol = (rol or "").lower().strip()

        self.page = 1
        self.page_size = 20
        self.data = []

        self._build_ui()
        self.after(100, self._load_data)  # 🔥 evita crash inicial

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        ttk.Label(
            self,
            text="Colillas de Pago",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)

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

        # 🔒 USER no puede cambiar usuario
        if self.rol == "user":
            self.cmb_usuario.configure(state="disabled")

        ttk.Button(filtros, text="Buscar", command=self._buscar)\
            .grid(row=1, column=3, padx=10)

        ttk.Button(filtros, text="Descargar colilla", command=self._descargar_colilla)\
            .grid(row=1, column=4, padx=10)

        # ================= TABLA =================
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "usuario", "year", "month", "salario_neto", "generado_por")

        self.table = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.table.heading(col, text=col.upper())
            self.table.column(col, width=120, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)

        self.table.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # ================= PAGINADO =================
        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=5)

        ttk.Button(pag, text="◀ Anterior", command=self._prev).pack(side="left")
        ttk.Button(pag, text="Siguiente ▶", command=self._next).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _load_data(self):

        try:
            resp = get_payslips_api(
                page=self.page,
                page_size=self.page_size,
                year=self._get_year(),
                month=self._get_month()
                # ❌ ELIMINADO usuario
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error backend:\n{e}")
            return

        if not isinstance(resp, dict):
            resp = {}

        self.data = resp.get("data", []) or []

        self._render_table()
        self._load_filters()

    def _render_table(self):

        self.table.delete(*self.table.get_children())

        for r in self.data:

            try:
                salario = float(r.get("salario_neto", 0))
                salario_fmt = f"{salario:,.2f}"
            except Exception:
                salario_fmt = "0.00"

            self.table.insert(
                "",
                "end",
                values=(
                    r.get("id"),
                    r.get("usuario"),
                    r.get("year"),
                    r.get("month"),
                    salario_fmt,
                    r.get("generado_por")
                )
            )

    # =========================================================
    # FILTROS
    # =========================================================
    def _load_filters(self):

        try:
            usuarios = sorted({r.get("usuario") for r in self.data if r.get("usuario")})
            years = sorted({r.get("year") for r in self.data if r.get("year")})
            months = sorted({r.get("month") for r in self.data if r.get("month")})
        except Exception:
            usuarios, years, months = [], [], []

        self.cmb_usuario["values"] = [""] + list(usuarios)
        self.cmb_year["values"] = [""] + list(years)
        self.cmb_month["values"] = [""] + list(months)

    def _get_year(self):
        val = self.cmb_year.get()
        return int(val) if str(val).isdigit() else None

    def _get_month(self):
        val = self.cmb_month.get()
        return int(val) if str(val).isdigit() else None

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
    # DESCARGA
    # =========================================================
    def _descargar_colilla(self):

        selected = self.table.selection()

        if not selected:
            messagebox.showwarning("Atención", "Seleccione una colilla")
            return

        try:
            row_index = self.table.index(selected[0])
            row = self.data[row_index]
        except Exception:
            messagebox.showerror("Error", "No se pudo leer la fila seleccionada")
            return

        year = row.get("year")
        month = row.get("month")

        if not year or not month:
            messagebox.showerror("Error", "Periodo inválido")
            return

        usuario = row.get("usuario")
        if not usuario:
            messagebox.showerror("Error", "La colilla seleccionada no tiene usuario asociado")
            return

        filename = f"COLILLA_{usuario}_{year}_{month}.pdf"

        save_path = filedialog.asksaveasfilename(
            title="Guardar colilla",
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

            if not resp:
                raise Exception("Respuesta vacía")

        except Exception as e:
            messagebox.showerror("Error", f"Descarga fallida:\n{e}")
            return

        try:
            with open(save_path, "wb") as f:

                if hasattr(resp, "iter_content"):
                    for chunk in resp.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                elif isinstance(resp, (bytes, bytearray)):
                    f.write(resp)
                else:
                    raise Exception("Formato inválido")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return

        messagebox.showinfo("OK", "Colilla descargada correctamente")
