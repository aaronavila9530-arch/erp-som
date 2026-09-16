import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

COMPANY_LEGAL_NAME = "MSL SRL Marine Surveyors and Logistics Group"
COMPANY_TAX_ID = "3-102-920372"
COMPANY_ADDRESS = "San Jose, Costa Rica, C.A"
COMPANY_ADDRESS_2 = "Alajuela, Rio Segundo, Plaza Aeropuerto, Local G-14"
COMPANY_PHONE = "506-8814-07-84"
IBAN_CODE = "CR49015201308000025850"


def _safe(value, default=""):
    return default if value in (None, "") else str(value).strip()


def _date_parts(value):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.day:02d}", f"{value.month:02d}", f"{str(value.year)[-2:]}"
    text = _safe(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(text[:20], fmt).date()
            return f"{parsed.day:02d}", f"{parsed.month:02d}", f"{str(parsed.year)[-2:]}"
        except Exception:
            pass
    today = date.today()
    return f"{today.day:02d}", f"{today.month:02d}", f"{str(today.year)[-2:]}"


def _money_text(total, moneda="USD"):
    try:
        value = float(total or 0)
    except Exception:
        value = 0.0
    symbol = "$" if _safe(moneda, "USD").upper() == "USD" else _safe(moneda).upper()
    return f"{symbol} {value:,.2f}"


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

        pdf = tk.Frame(container, bg="white", bd=1, relief="solid", width=690, height=545)
        pdf.pack(fill="both", expand=True, padx=10, pady=10)
        pdf.pack_propagate(False)

        def lbl(parent, text, bold=False, anchor="w", fg="black", size=10, justify="left"):
            item = tk.Label(
                parent,
                text=text,
                bg="white",
                fg=fg,
                anchor=anchor,
                justify=justify,
                font=("Times New Roman", size, "bold" if bold else "normal")
            )
            return item

        day, month, year = _date_parts(self.data.get("fecha_factura") or self.data.get("fecha_emision"))
        cliente = _safe(self.data.get("cliente") or self.data.get("nombre_cliente")).upper()
        place = _safe(self.data.get("place") or self.data.get("lugar")).upper()
        survey = _safe(self.data.get("survey") or self.data.get("operacion")).upper()
        description = _safe(self.data.get("descripcion") or self.data.get("descripcion_servicio")).upper()
        terms = _safe(self.data.get("payment_terms"))
        if not terms:
            days = _safe(self.data.get("termino_pago"), "0")
            terms = f"CREDIT {days} DAYS" if days not in ("", "0") else "DUE UPON RECEIPT"
        total = _money_text(self.data.get("total"), self.data.get("moneda", "USD"))

        header = tk.Frame(pdf, bg="white")
        header.pack(fill="x", padx=18, pady=(12, 6))
        left = tk.Frame(header, bg="white")
        left.pack(side="left", fill="x", expand=True)
        right = tk.Frame(header, bg="white")
        right.pack(side="right")

        lbl(left, "M.S.L S.R.L", bold=True, fg="blue", size=18).pack(anchor="w")
        lbl(left, "Marine Surveyors and Logistics Group", bold=True, fg="red", size=14).pack(anchor="w")
        lbl(left, COMPANY_ADDRESS, bold=True, size=9).pack(anchor="w")
        lbl(left, COMPANY_ADDRESS_2, bold=True, size=9).pack(anchor="w")
        lbl(right, f"Ced. Jurídica {COMPANY_TAX_ID}", bold=True, anchor="e", size=9).pack(anchor="e")
        lbl(right, f"Phone {COMPANY_PHONE}", bold=True, anchor="e", size=9).pack(anchor="e")
        lbl(right, "\nINVOICE", bold=True, anchor="e", size=15).pack(anchor="e")
        invoice_no = _safe(self.data.get("numero_documento") or self.data.get("numero_factura") or "-")
        inv_line = tk.Frame(right, bg="white")
        inv_line.pack(anchor="e")
        lbl(inv_line, "N°", bold=True, size=12).pack(side="left")
        lbl(inv_line, invoice_no, bold=True, fg="red", size=12).pack(side="left")

        top_row = tk.Frame(pdf, bg="white")
        top_row.pack(fill="x", padx=18, pady=(8, 4))
        client_box = tk.Frame(top_row, bg="white", bd=1, relief="solid", height=86)
        client_box.pack(side="left", fill="x", expand=True)
        client_box.pack_propagate(False)
        lbl(client_box, f"CLIENT: {cliente}", bold=True, size=11).pack(anchor="w", padx=8, pady=(8, 0))
        lbl(client_box, f"PLACE: {place}", bold=True, size=11).pack(anchor="w", padx=8, pady=(18, 0))

        date_wrap = tk.Frame(top_row, bg="white")
        date_wrap.pack(side="right", padx=(16, 0))
        date_box = tk.Frame(date_wrap, bg="white", bd=1, relief="solid")
        date_box.pack(anchor="e")
        for idx, text in enumerate(("DAY", "MONTH", "YEAR")):
            lbl(date_box, text, bold=True, size=10, anchor="center").grid(row=0, column=idx, ipadx=12, ipady=3, sticky="nsew")
        for idx, text in enumerate((day, month, year)):
            lbl(date_box, text, bold=True, size=10, anchor="center").grid(row=1, column=idx, ipadx=12, ipady=3, sticky="nsew")
        lbl(date_wrap, f"TERM OF PAYMENT: {terms.upper()}", bold=True, fg="red", size=8).pack(anchor="e", pady=(15, 0))

        lbl(pdf, "DESCRIPTION", bold=True, size=12).pack(anchor="w", padx=28, pady=(8, 2))
        desc_box = tk.Frame(pdf, bg="white", bd=1, relief="solid", height=180)
        desc_box.pack(fill="x", padx=18)
        desc_box.pack_propagate(False)
        lbl(desc_box, description, size=11, wraplength=610, justify="left").pack(anchor="w", padx=8, pady=(8, 0))
        if place:
            lbl(desc_box, place, size=11).pack(anchor="w", padx=8, pady=(18, 0))
        if survey:
            lbl(desc_box, "SURVEY:", size=11).pack(anchor="w", padx=8, pady=(18, 0))
            line = tk.Frame(desc_box, bg="white")
            line.pack(fill="x", padx=8)
            lbl(line, f"-{survey}", size=11).pack(side="left")
            lbl(line, total, size=11).pack(side="right", padx=(0, 20))

        total_box = tk.Frame(pdf, bg="white", bd=1, relief="solid")
        total_box.pack(anchor="e", padx=42, pady=(8, 0))
        lbl(total_box, "TOTAL", bold=True, size=12, anchor="center").pack(side="left", ipadx=13, ipady=5)
        tk.Frame(total_box, bg="black", width=1, height=28).pack(side="left", fill="y")
        lbl(total_box, total, bold=True, size=12, anchor="center").pack(side="left", ipadx=13, ipady=5)

        bank = tk.Frame(container, bg="white")
        bank.pack(fill="x", padx=34, pady=(4, 0))
        bank_lines = [
            "Beneficiary Bank: BCR Banco de Costa Rica",
            "Direccion fisica: San Jose de Costa Rica",
            "SWIFT N° BCRICRSJ",
            "Account: 308258-5",
            "",
            f"IBAN CODE: {IBAN_CODE}",
            f"Beneficiary: {COMPANY_LEGAL_NAME}",
            f"Address: {COMPANY_ADDRESS_2}",
            "Account: 308258-5 BCRICRSJ",
            "",
            "NOTE: PAYMENTS TO BE DRAWN ON C.R BANK FREE OF",
            "ALL CHARGES / IN U.S DOLLARS",
        ]
        for text in bank_lines:
            color = "red" if text.startswith("IBAN CODE") or text.startswith("NOTE") or text.startswith("ALL CHARGES") else "black"
            lbl(bank, text, fg=color, size=9).pack(anchor="w")

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
