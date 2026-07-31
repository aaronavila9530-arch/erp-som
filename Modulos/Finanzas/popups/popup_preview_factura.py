import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Finanzas.date_utils import to_long_english_date


class PopupPreviewFactura(tk.Toplevel):

    def __init__(self, parent, data, on_confirm):
        super().__init__(parent)

        self.data = data or {}
        self.on_confirm = on_confirm

        self.title("Preview Factura")
        self.geometry("760x650")
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = tk.Frame(self, bg="white")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        pdf = tk.Frame(container, bg="white", bd=1, relief="solid")
        pdf.pack(fill="both", expand=True, padx=10, pady=10)

        def lbl(parent, text, bold=False, anchor="w"):
            return tk.Label(
                parent,
                text=text,
                bg="white",
                fg="black",
                anchor=anchor,
                font=("Segoe UI", 10, "bold" if bold else "normal")
            )

        # ====================================================
        # EMISOR
        # ====================================================
        emisor = tk.Frame(pdf, bg="white")
        emisor.pack(fill="x", padx=10, pady=(10, 5))

        lbl(emisor, "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL", bold=True).pack(anchor="w")
        lbl(emisor, "Cédula Jurídica: 3-102-920372").pack(anchor="w")
        lbl(emisor, "Correo: operations@mslogisticsgroup.com  |  Tel: +506 4352-8382").pack(anchor="w")

        ttk.Separator(pdf).pack(fill="x", pady=8)

        # ====================================================
        # CLIENTE + FACTURA
        # ====================================================
        cliente = tk.Frame(pdf, bg="white")
        cliente.pack(fill="x", padx=10, pady=5)

        lbl(cliente, "FACTURA N° —", bold=True).pack(anchor="w")
        lbl(cliente, f"Cliente: {self.data.get('cliente', '')}").pack(anchor="w")
        lbl(cliente, f"N° Informe: {self.data.get('num_informe', '')}").pack(anchor="w")
        lbl(cliente, f"Fecha factura: {to_long_english_date(self.data.get('fecha_factura', ''))}").pack(anchor="w")

        ttk.Separator(pdf).pack(fill="x", pady=8)

        # ====================================================
        # TÉRMINOS DE PAGO
        # ====================================================
        pago = tk.Frame(pdf, bg="white")
        pago.pack(fill="x", padx=10, pady=5)

        lbl(pago, "Términos de pago", bold=True).pack(anchor="w")
        lbl(
            pago,
            f"{self.data.get('termino_pago', '')} días  |  "
            f"Moneda: {self.data.get('moneda', '')}"
        ).pack(anchor="w")

        ttk.Separator(pdf).pack(fill="x", pady=8)

        # ====================================================
        # DESCRIPCIÓN DEL SERVICIO
        # ====================================================
        desc = tk.Frame(pdf, bg="white")
        desc.pack(fill="x", padx=10, pady=5)

        lbl(desc, "Descripción del servicio", bold=True).pack(anchor="w")
        lbl(desc, f"Buque / Contenedor: {self.data.get('buque', '')}").pack(anchor="w")
        lbl(desc, f"Operación: {self.data.get('operacion', '')}").pack(anchor="w")
        lbl(desc, f"Periodo de operación: {self.data.get('periodo_operacion', '')}").pack(anchor="w")

        tk.Label(
            desc,
            text=self.data.get("descripcion", ""),
            bg="white",
            fg="black",
            justify="left",
            wraplength=700,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 0))

        ttk.Separator(pdf).pack(fill="x", pady=8)

        # ====================================================
        # TOTAL
        # ====================================================
        total = tk.Frame(pdf, bg="white")
        total.pack(fill="x", padx=10, pady=5)

        lbl(
            total,
            f"TOTAL {self.data.get('moneda', '')} {self.data.get('total', '')}",
            bold=True,
            anchor="e"
        ).pack(anchor="e")

        ttk.Separator(pdf).pack(fill="x", pady=8)

        # ====================================================
        # DATOS BANCARIOS
        # ====================================================
        banco = tk.Frame(pdf, bg="white")
        banco.pack(fill="x", padx=10, pady=(5, 10))

        lbl(banco, "Datos bancarios", bold=True).pack(anchor="w")
        lbl(banco, "Banco: Banco de Costa Rica").pack(anchor="w")
        lbl(banco, "IBAN: CR49015201308000025850").pack(anchor="w")
        lbl(banco, "SWIFT: BNCRCRSJ").pack(anchor="w")

        # ====================================================
        # BOTONES
        # ====================================================
        actions = tk.Frame(container, bg="white")
        actions.pack(fill="x", pady=15)

        ttk.Button(actions, text="⬅ Atrás", command=self.destroy).pack(side="left")

        if self.on_confirm:
            ttk.Button(actions, text="Facturar", command=self._confirmar).pack(side="right")

    # ============================================================
    # CONFIRMACIÓN
    # ============================================================
    def _confirmar(self):
        if not messagebox.askyesno(
            "Confirmar",
            "¿Está seguro en continuar?\n\n"
            "Si continúa no podrá modificar tras facturado."
        ):
            return

        self.destroy()
        self.on_confirm()
