import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date
import os

from Modulos.HHRR.reports.payroll_pdf import generar_colilla_pdf
from api_client import (
    hr_calculate_payroll,
    hr_post_payroll
)


def fmt(valor):
    """Formato monetario con separador de miles"""
    try:
        return f"{float(valor):,.2f}"
    except Exception:
        return valor


class PopupColillaPago(tk.Toplevel):
    """
    Popup de Generación / Preview de Colilla de Pago.
    Genera PDF y registra en payroll_runs.
    """

    def __init__(self, parent, empleado_row: dict):
        super().__init__(parent)

        self.parent = parent
        self.empleado = empleado_row or {}
        self.preview_data = None

        # =====================================================
        # PERIODO PERMITIDO = MES CERRADO (MES ANTERIOR)
        # =====================================================
        hoy = date.today()

        if hoy.month == 1:
            self.month = 12
            self.year = hoy.year - 1
        else:
            self.month = hoy.month - 1
            self.year = hoy.year

        self.title("Generar Colilla de Pago")
        self.geometry("640x520")
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        # -----------------------------------------------------
        # DATOS EMPLEADO
        # -----------------------------------------------------
        info = ttk.LabelFrame(main, text="Empleado")
        info.pack(fill="x", pady=5)

        self._info_row(info, "Nombre", self.empleado.get("nombre", ""))
        self._info_row(info, "Apellidos", self.empleado.get("apellidos", ""))
        self._info_row(info, "Usuario", self.empleado.get("usuario", ""))
        self._info_row(info, "Jornada", self.empleado.get("jornada", ""))
        self._info_row(info, "Tipo de pago", self.empleado.get("pago", ""))

        # -----------------------------------------------------
        # PERIODO
        # -----------------------------------------------------
        periodo = ttk.LabelFrame(main, text="Periodo")
        periodo.pack(fill="x", pady=5)

        ttk.Label(periodo, text="Año").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(periodo, text="Mes").grid(row=0, column=2, padx=5, pady=5)

        self.var_year = tk.IntVar(value=self.year)
        self.var_month = tk.IntVar(value=self.month)

        ttk.Entry(
            periodo,
            textvariable=self.var_year,
            width=10,
            state="disabled"
        ).grid(row=0, column=1, padx=5)

        ttk.Entry(
            periodo,
            textvariable=self.var_month,
            width=10,
            state="disabled"
        ).grid(row=0, column=3, padx=5)

        ttk.Label(
            periodo,
            text="Solo se permite generar la planilla del mes cerrado (mes anterior)",
            foreground="gray"
        ).grid(row=1, column=0, columnspan=4, pady=5)

        # -----------------------------------------------------
        # EDITABLES
        # -----------------------------------------------------
        edit = ttk.LabelFrame(main, text="Valores editables")
        edit.pack(fill="x", pady=5)

        salario_base = float(self.empleado.get("salario") or 0)

        self.var_salario = tk.DoubleVar(value=salario_base)
        self.var_valor_hora_extra = tk.DoubleVar(value=0.0)

        ttk.Label(edit, text="Salario").grid(row=0, column=0, padx=5, pady=5, sticky="w")

        ttk.Entry(
            edit,
            textvariable=self.var_salario,
            width=20
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(edit, text="Valor Hora Extra").grid(
            row=1,
            column=0,
            padx=5,
            pady=5,
            sticky="w"
        )

        self.entry_hora_extra = ttk.Entry(
            edit,
            textvariable=self.var_valor_hora_extra,
            width=20,
            state="disabled"
        )

        self.entry_hora_extra.grid(row=1, column=1, padx=5, pady=5)

        # -----------------------------------------------------
        # BOTONES
        # -----------------------------------------------------
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=15)

        ttk.Button(
            btns,
            text="Preview",
            command=self._preview
        ).pack(side="left", padx=5)

        self.btn_pdf = ttk.Button(
            btns,
            text="Generar PDF",
            command=self._export_pdf,
            state="disabled"
        )

        self.btn_pdf.pack(side="left", padx=5)

        ttk.Button(
            btns,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right", padx=5)

        # -----------------------------------------------------
        # RESULTADO
        # -----------------------------------------------------
        self.result = ttk.LabelFrame(main, text="Resultado Preview")
        self.result.pack(fill="both", expand=True, pady=5)

        self.txt_result = tk.Text(
            self.result,
            height=10,
            state="disabled"
        )

        self.txt_result.pack(fill="both", expand=True)

    # =========================================================
    # HELPERS UI
    # =========================================================
    def _info_row(self, parent, label, value):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        ttk.Label(
            row,
            text=label + ":",
            width=18
        ).pack(side="left")

        ttk.Label(
            row,
            text=value
        ).pack(side="left")

    # =========================================================
    # PREVIEW
    # =========================================================
    def _preview(self):

        try:

            data = hr_calculate_payroll(
                usuario=self.empleado.get("usuario"),
                year=self.var_year.get(),
                month=self.var_month.get()
            )

            if not data:
                raise Exception("No se pudo calcular la planilla.")

            self.preview_data = data

            # habilitar campo horas extra si aplica
            if data.get("jornada") == "HORAS" and data.get("horas_ot", 0) > 0:
                self.entry_hora_extra.config(state="normal")
            else:
                self.entry_hora_extra.config(state="disabled")
                self.var_valor_hora_extra.set(0.0)

            self._render_result(data)

            self.btn_pdf.config(state="normal")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # RENDER RESULTADO
    # =========================================================
    def _render_result(self, data: dict):

        self.txt_result.config(state="normal")
        self.txt_result.delete("1.0", tk.END)

        for k, v in data.items():

            if isinstance(v, (int, float)):
                v = fmt(v)

            self.txt_result.insert(
                tk.END,
                f"{k.replace('_',' ').title()}: {v}\n"
            )

        self.txt_result.config(state="disabled")

    # =========================================================
    # EXPORT PDF + POST payroll_runs
    # =========================================================
    def _export_pdf(self):

        if not self.preview_data:
            messagebox.showwarning(
                "Planilla",
                "Primero debe ejecutar el preview."
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"COLILLA_{self.preview_data['usuario']}_{self.year}_{self.month}.pdf"
        )

        if not path:
            return

        try:

            # -------------------------------------------------
            # 1️⃣ Generar PDF local
            # -------------------------------------------------
            generar_colilla_pdf(
                path=path,
                data=self.preview_data,
                year=self.year,
                month=self.month
            )

            # -------------------------------------------------
            # 2️⃣ PDF PATH ONLINE (REFERENCIA LÓGICA)
            # -------------------------------------------------
            filename = os.path.basename(path)
            pdf_path_online = f"/LOCAL_USER_FILE/{filename}"

            # -------------------------------------------------
            # 3️⃣ PAYLOAD BACKEND
            # -------------------------------------------------
            payload = {
                "usuario": self.preview_data["usuario"],
                "year": self.year,
                "month": self.month,
                "salario_neto": self.preview_data.get("salario_neto", 0),
                "salario_bruto": self.preview_data.get(
                    "salario_bruto",
                    self.preview_data.get("salario_neto", 0)
                ),
                "horas_ot": self.preview_data.get("horas_ot", 0),
                "pago_horas_extra": self.preview_data.get("pago_horas_extra", 0),
                "pdf_path": pdf_path_online
            }

            hr_post_payroll(payload)

            messagebox.showinfo(
                "Planilla",
                "Colilla generada y registrada correctamente."
            )

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))