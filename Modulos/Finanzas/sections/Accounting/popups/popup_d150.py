import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from api_client import get_accounting_iva_api


class PopupD150(tk.Toplevel):

    def __init__(self, parent, period):
        super().__init__(parent)

        self.period = period
        self.title(f"Formulario TRIBU-CR 150 - IVA ({period})")
        self.geometry("650x420")
        self.resizable(False, False)

        self.data = None

        self._build_ui()
        self._load_data()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------
    def _build_ui(self):

        frame = tk.LabelFrame(
            self,
            text="IV. CÁLCULO DEL IMPUESTO",
            padx=15,
            pady=15
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.labels = {}

        fields = [
            "Monto del impuesto ventas generales",
            "Total monto del impuesto",
            "Total crédito fiscal para el IVA",
            "Total gasto para utilidades",
            "Devolución IVA servicios salud",
            "Impuesto determinado",
            "Saldo a favor"
        ]

        for i, label in enumerate(fields):
            tk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=4)
            var = tk.StringVar(value="0.00")
            tk.Label(
                frame,
                textvariable=var,
                anchor="e",
                width=20,
                font=("Segoe UI", 10, "bold")
            ).grid(row=i, column=1, sticky="e")
            self.labels[label] = var

        # ---------------- BOTONES ----------------
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="Exportar Excel",
            command=self._export_excel
        ).pack(side="left", padx=10)

        ttk.Button(
            btn_frame,
            text="Exportar PDF",
            command=self._export_pdf
        ).pack(side="left", padx=10)

        ttk.Button(
            btn_frame,
            text="Cerrar",
            command=self.destroy
        ).pack(side="left", padx=10)

    # -------------------------------------------------
    # DATA
    # -------------------------------------------------
    def _load_data(self):
        try:
            data = get_accounting_iva_api(self.period)
            self.data = data

            iva_pagar = data["iva_por_pagar"]
            iva_credito = data["iva_credito"]
            saldo_favor = data["saldo_favor_anterior"]
            impuesto_determinado = iva_pagar - iva_credito

            self.labels["Monto del impuesto ventas generales"].set(f"{iva_pagar:,.2f}")
            self.labels["Total monto del impuesto"].set(f"{iva_pagar:,.2f}")
            self.labels["Total crédito fiscal para el IVA"].set(f"{iva_credito:,.2f}")
            self.labels["Total gasto para utilidades"].set(f"{-iva_credito:,.2f}")
            self.labels["Devolución IVA servicios salud"].set("0.00")
            self.labels["Impuesto determinado"].set(f"{max(impuesto_determinado, 0):,.2f}")
            self.labels["Saldo a favor"].set(f"{max(saldo_favor, 0):,.2f}")

        except Exception as e:
            messagebox.showerror("Formulario 150", str(e))
            self.destroy()

    # -------------------------------------------------
    # EXPORT EXCEL
    # -------------------------------------------------
    def _export_excel(self):
        from openpyxl import Workbook

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Formulario 150"

        ws.append(["Formulario TRIBU-CR 150 - Declaración IVA"])
        ws.append(["Periodo", self.period])
        ws.append([])

        for label, var in self.labels.items():
            ws.append([label, var.get()])

        wb.save(path)
        messagebox.showinfo("Exportación", "Archivo Excel generado.")

    # -------------------------------------------------
    # EXPORT PDF
    # -------------------------------------------------
    def _export_pdf(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return

        c = canvas.Canvas(path, pagesize=A4)
        y = 800

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Formulario TRIBU-CR 150 - Impuesto al Valor Agregado")
        y -= 30

        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Periodo: {self.period}")
        y -= 30

        for label, var in self.labels.items():
            c.drawString(50, y, label)
            c.drawRightString(550, y, var.get())
            y -= 18

        c.save()
        messagebox.showinfo("Exportación", "Archivo PDF generado.")
