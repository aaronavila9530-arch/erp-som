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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
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
        self.geometry("980x760")
        self.minsize(760, 560)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel)
        self.bind("<Button-5>", self._on_mousewheel)

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        root = tk.Frame(self, bg="#f3f4f6")
        root.pack(fill="both", expand=True)

        scroll_host = tk.Frame(root, bg="#f3f4f6")
        scroll_host.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(scroll_host, bg="#f3f4f6", highlightthickness=0)
        y_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=self.canvas.yview)
        x_scroll = ttk.Scrollbar(scroll_host, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_host.grid_rowconfigure(0, weight=1)
        scroll_host.grid_columnconfigure(0, weight=1)

        day, month, year = _date_parts(self.data.get("fecha_factura") or self.data.get("fecha_emision"))
        cliente = _safe(self.data.get("cliente") or self.data.get("nombre_cliente")).upper()
        place = _safe(self.data.get("place") or self.data.get("lugar")).upper()
        survey = _safe(self.data.get("survey") or self.data.get("operacion")).upper()
        description = self._description_text()
        terms = _safe(self.data.get("payment_terms"))
        if terms.isdigit():
            terms = f"CREDIT {terms} DAYS"
        if not terms:
            days = _safe(self.data.get("termino_pago"), "0")
            terms = f"CREDIT {days} DAYS" if days not in ("", "0") else "DUE UPON RECEIPT"
        total = _money_text(self.data.get("total"), self.data.get("moneda", "USD"))
        invoice_no = _safe(self.data.get("numero_documento") or self.data.get("numero_factura") or "-")

        self._draw_invoice_preview(
            cliente=cliente,
            place=place,
            survey=survey,
            description=description,
            terms=terms,
            total=total,
            invoice_no=invoice_no,
            day=day,
            month=month,
            year=year,
        )

        actions = tk.Frame(root, bg="white", bd=1, relief="ridge")
        actions.pack(fill="x", side="bottom", padx=0, pady=0)

        ttk.Button(actions, text="Atrás", command=self.destroy).pack(side="left", padx=16, pady=10)

        if self.on_confirm:
            ttk.Button(actions, text="Facturar", command=self._confirmar).pack(side="right", padx=16, pady=10)

    def _description_text(self):
        raw = _safe(self.data.get("descripcion") or self.data.get("descripcion_servicio"))
        return raw.upper() if raw else "SIN DESCRIPCION"

    def _draw_invoice_preview(self, *, cliente, place, survey, description, terms, total, invoice_no, day, month, year):
        self.canvas.delete("all")

        page_x = 36
        page_y = 28
        page_w = 900
        page_h = 1250
        margin = 28
        left = page_x + margin
        right = page_x + page_w - margin
        top = page_y + margin

        def text(x, y, value, *, size=12, bold=False, fill="black", anchor="nw", width=None, justify="left"):
            return self.canvas.create_text(
                x,
                y,
                text=value,
                fill=fill,
                anchor=anchor,
                width=width,
                justify=justify,
                font=("Times New Roman", size, "bold" if bold else "normal"),
            )

        self.canvas.create_rectangle(page_x, page_y, page_x + page_w, page_y + page_h, fill="white", outline="")
        self.canvas.create_rectangle(left, top, right, page_y + page_h - margin, outline="black", width=2)

        # Header
        text(left + 28, top + 28, "M.S.L S.R.L", size=24, bold=True, fill="blue")
        text(left + 28, top + 66, "Marine Surveyors and Logistics Group", size=20, bold=True, fill="red")
        text(left + 28, top + 100, COMPANY_ADDRESS, size=12, bold=True)
        text(left + 28, top + 124, COMPANY_ADDRESS_2, size=12, bold=True)

        text(right - 28, top + 34, f"Ced. Juridica {COMPANY_TAX_ID}", size=12, bold=True, anchor="ne")
        text(right - 28, top + 58, f"Phone {COMPANY_PHONE}", size=12, bold=True, anchor="ne")
        text(right - 88, top + 180, "INVOICE", size=22, bold=True, anchor="n")
        text(right - 88, top + 220, "N°", size=16, bold=True, anchor="n")
        text(right - 54, top + 220, invoice_no, size=16, bold=True, fill="red", anchor="n")

        # Client and date blocks
        client_x = left + 16
        client_y = top + 244
        date_w = 252
        col_w = date_w / 3
        date_gap = 28
        date_x = right - 16 - date_w
        client_w = date_x - date_gap - client_x
        client_h = 170
        self.canvas.create_rectangle(client_x, client_y, client_x + client_w, client_y + client_h, outline="black", width=2)
        text(client_x + 14, client_y + 18, f"CLIENT: {cliente}", size=16, bold=True, width=client_w - 28)
        text(client_x + 14, client_y + 82, f"PLACE: {place}", size=16, bold=True, width=client_w - 28)

        date_y = client_y + 18
        row_h = 42
        for i in range(4):
            x = date_x + i * col_w
            self.canvas.create_line(x, date_y, x, date_y + row_h * 2, fill="black", width=2)
        for j in range(3):
            y = date_y + j * row_h
            self.canvas.create_line(date_x, y, date_x + col_w * 3, y, fill="black", width=2)
        for i, value in enumerate(("DAY", "MONTH", "YEAR")):
            text(date_x + col_w * i + col_w / 2, date_y + 13, value, size=14, bold=True, anchor="n")
        for i, value in enumerate((day, month, year)):
            text(date_x + col_w * i + col_w / 2, date_y + row_h + 13, value, size=14, bold=True, anchor="n")
        text(date_x - 6, date_y + 128, f"TERM OF PAYMENT: {terms.upper()}", size=11, bold=True, fill="red", width=date_w + 18)

        # Description block
        desc_title_y = client_y + client_h + 42
        text(left + 30, desc_title_y, "DESCRIPTION", size=18, bold=True)
        desc_x = left + 16
        desc_y = desc_title_y + 40
        desc_w = right - desc_x - 16
        desc_h = 285
        self.canvas.create_rectangle(desc_x, desc_y, desc_x + desc_w, desc_y + desc_h, outline="black", width=2)
        text(desc_x + 22, desc_y + 20, description, size=15, width=desc_w - 42)
        if survey:
            text(desc_x + 22, desc_y + 92, "SURVEY:", size=15)
            text(desc_x + 22, desc_y + 122, f"-{survey}", size=15, width=desc_w - 220)
            text(desc_x + desc_w - 42, desc_y + 90, total, size=15, anchor="ne")

        # Total and bank block
        total_y = desc_y + desc_h + 22
        total_x = right - 260
        self.canvas.create_rectangle(total_x, total_y, right - 16, total_y + 42, outline="black", width=2)
        self.canvas.create_line(total_x + 100, total_y, total_x + 100, total_y + 42, fill="black", width=2)
        text(total_x + 50, total_y + 12, "TOTAL", size=14, bold=True, anchor="n")
        text(right - 56, total_y + 12, total, size=14, bold=True, anchor="ne")

        bank_y = total_y + 74
        bank_lines = [
            ("Beneficiary Bank: BCR Banco de Costa Rica", "black"),
            ("Direccion fisica: San Jose de Costa Rica", "black"),
            ("SWIFT N° BCRICRSJ", "black"),
            ("Account: 308258-5", "black"),
            ("", "black"),
            (f"IBAN ACCOUNT: {IBAN_CODE}", "red"),
            (f"Beneficiary: {COMPANY_LEGAL_NAME}", "black"),
            (f"Address: {COMPANY_ADDRESS_2}", "black"),
            ("Account: 308258-5 BCRICRSJ", "black"),
            ("", "black"),
            ("NOTE: PAYMENTS TO BE DRAWN ON C.R BANK FREE OF", "red"),
            ("ALL CHARGES / IN U.S DOLLARS", "red"),
        ]
        for index, (line, color) in enumerate(bank_lines):
            text(desc_x + 22, bank_y + index * 22, line, size=12, bold=color == "red", fill=color)

        self.canvas.configure(scrollregion=(0, 0, page_x + page_w + 36, page_y + page_h + 24))

    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            delta = int(-1 * (event.delta / 120))
            if event.state & 0x0001:
                self.canvas.xview_scroll(delta * 3, "units")
            else:
                self.canvas.yview_scroll(delta * 3, "units")

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
