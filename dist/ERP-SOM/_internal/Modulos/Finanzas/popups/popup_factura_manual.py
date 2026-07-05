import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import date

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker
from api_client import (
    post_factura_manual_api,
    get_termino_pago_cliente_api   # ✅ FUNCIÓN REAL
)


class PopupFacturaManual(tk.Toplevel):

    def __init__(self, parent, servicio, on_success):
        super().__init__(parent)

        self.servicio = servicio
        self.on_success = on_success

        self.title("Factura Manual Anticipada")
        self.geometry("600x520")
        self.transient(parent)
        self.grab_set()

        # ================= VARIABLES =================
        self.fecha = tk.StringVar(value=to_long_english_date(date.today()))
        self.moneda = tk.StringVar(value="USD")
        self.termino_pago = tk.StringVar()
        self.total = tk.StringVar()

        self.buque = tk.StringVar(value=servicio.get("buque_contenedor", ""))
        self.servicio_op = tk.StringVar(value=servicio.get("operacion", ""))
        self.num_informe = tk.StringVar(value=servicio.get("num_informe", ""))
        self.periodo = tk.StringVar(
            value=f"De {to_long_english_date(servicio.get('fecha_inicio'))} a {to_long_english_date(servicio.get('fecha_fin'))}"
        )

        self.descripcion_default = (
            f"{servicio.get('puerto')}, {servicio.get('pais')} – "
            f"{servicio.get('operacion')} – {servicio.get('detalle')}"
        )

        # 🔑 CARGA REAL DESDE BACKEND
        self._cargar_terminos_pago()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        frame = tk.Frame(self, bg="white")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        r = 0
        self._field(frame, "Buque / Contenedor:", self.buque, r); r += 1
        self._field(frame, "Servicio:", self.servicio_op, r); r += 1
        self._field(frame, "Número de informe:", self.num_informe, r); r += 1
        self._field(frame, "Periodo de operación:", self.periodo, r); r += 1
        self._field(frame, "Fecha emisión:", self.fecha, r); r += 1
        self._field(frame, "Moneda:", self.moneda, r); r += 1
        self._field(frame, "Término de pago (días):", self.termino_pago, r, readonly=True); r += 1
        self._field(frame, "Total:", self.total, r); r += 1

        tk.Label(
            frame,
            text="Descripción:",
            bg="white",
            fg="black"
        ).grid(row=r, column=0, sticky="nw", pady=5)

        self.txt_desc = tk.Text(
            frame,
            height=4,
            width=50,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        self.txt_desc.insert("1.0", self.descripcion_default)
        self.txt_desc.grid(row=r, column=1, pady=5, sticky="w")

        tk.Button(
            frame,
            text="Preview Factura",
            width=20,
            command=self._preview
        ).grid(row=r + 1, column=1, sticky="e", pady=20)

    def _field(self, parent, label, var, row, readonly=False):

        tk.Label(
            parent,
            text=label,
            bg="white",
            fg="black"
        ).grid(row=row, column=0, sticky="w", pady=5)

        entry = tk.Entry(
            parent,
            textvariable=var,
            width=45,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        entry.grid(row=row, column=1, pady=5, sticky="w")

        if readonly:
            entry.config(state="readonly")

        if "Fecha" in label:
            tk.Button(
                parent,
                text="📅",
                width=3,
                command=lambda: DatePicker(self, entry, output_format=LONG_DATE_FORMAT)
            ).grid(row=row, column=2, padx=5, sticky="w")

    # ============================================================
    # TÉRMINOS DE PAGO (cliente → cliente_credito) ✅
    # ============================================================
    def _cargar_terminos_pago(self):
        """
        cliente.nombrecomercial
            → cliente.codigo
                → cliente_credito.termino_pago
        """
        nombre_cliente = (self.servicio.get("cliente") or "").strip()

        if not nombre_cliente:
            self.termino_pago.set("")
            return

        try:
            info = get_termino_pago_cliente_api(nombre_cliente)

            termino = info.get("termino_pago")

            if termino is None:
                self.termino_pago.set("")
            else:
                self.termino_pago.set(str(int(termino)))

        except Exception as e:
            print("ERROR cargando término de pago:", e)
            self.termino_pago.set("")

    # ============================================================
    # FACTURAR
    # ============================================================
    def _facturar(self):

        if not self.total.get().strip():
            messagebox.showerror("Error", "El total es obligatorio.")
            return

        payload = {
            "servicio_id": int(self.servicio["consec"]),
            "descripcion": self.txt_desc.get("1.0", "end").strip(),
            "moneda": self.moneda.get(),
            "termino_pago": int(self.termino_pago.get() or 0),
            "total": float(self.total.get())
        }

        try:
            data = post_factura_manual_api(payload)

            factura_id = data["factura_id"]

            from api_client import api_request, BASE_URL

            pdf_response = api_request(
                "GET",
                f"{BASE_URL}/factura/pdf/{factura_id}",
                timeout=20,
                stream=True
            )

            path = filedialog.asksaveasfilename(
                title="Guardar factura",
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                initialfile=f"Factura_{data.get('numero_factura')}.pdf"
            )

            if path:
                with open(path, "wb") as f:
                    for chunk in pdf_response.iter_content(8192):
                        f.write(chunk)

            messagebox.showinfo(
                "Factura creada",
                "La factura manual fue creada correctamente."
            )

            self.destroy()
            self.on_success()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # PREVIEW
    # ============================================================
    def _preview(self):

        data = {
            "cliente": self.servicio["cliente"],
            "fecha_factura": self.fecha.get().strip(),
            "buque": self.buque.get(),
            "operacion": self.servicio_op.get(),
            "num_informe": self.num_informe.get(),
            "periodo_operacion": self.periodo.get(),
            "descripcion": self.txt_desc.get("1.0", "end").strip(),
            "moneda": self.moneda.get(),
            "termino_pago": self.termino_pago.get(),
            "total": self.total.get()
        }

        from Modulos.Finanzas.popups.popup_preview_factura import PopupPreviewFactura
        PopupPreviewFactura(
            self,
            data=data,
            on_confirm=self._facturar
        )
