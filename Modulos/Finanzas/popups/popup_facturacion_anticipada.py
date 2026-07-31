import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from datetime import date

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker
from api_client import (
    get_clientes_finanzas_api,
    post_invoicing_anticipada_manual_api,
    post_invoicing_anticipada_xml_api
)


class PopupFacturacionAnticipada(tk.Toplevel):

    def __init__(self, parent, on_success, servicio=None):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success
        self.servicio = servicio or {}  # NO requerido

        self.title("Factura Anticipada")
        self.geometry("600x560")
        self.transient(parent)
        self.grab_set()

        # ================= VARIABLES =================
        self.tipo_factura = tk.StringVar(value="MANUAL")

        # Cliente (combo)
        self.cliente_nombre = tk.StringVar()
        self.cliente_codigo = None
        self._clientes_map = {}  # nombre -> codigo

        # Manual
        self.fecha = tk.StringVar(value=to_long_english_date(date.today()))
        self.moneda = tk.StringVar(value="USD")
        self.termino_pago = tk.StringVar()
        self.total = tk.StringVar()

        self.buque = tk.StringVar()
        self.operacion = tk.StringVar()
        self.num_informe = tk.StringVar()
        self.periodo_operacion = tk.StringVar()

        # XML
        self.xml_path = None
        self.lbl_xml_path = None

        self._build_ui()
        self._load_clientes()
        self._cargar_termino_pago_desde_servicio()

        # Estado inicial UI
        self._on_tipo_change()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        frame = tk.Frame(self, bg="white")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        r = 0

        # -------- Tipo factura --------
        tk.Label(frame, text="Tipo de factura:", bg="white", fg="black")\
            .grid(row=r, column=0, sticky="w", pady=5)

        # OJO: OptionMenu en Tk (sin ttk) para evitar estilos raros
        opt = tk.OptionMenu(
            frame,
            self.tipo_factura,
            "MANUAL",
            "XML",
            command=lambda *_: self._on_tipo_change()
        )
        opt.config(bg="white", fg="black", highlightthickness=1, relief="solid", bd=1)
        opt.grid(row=r, column=1, sticky="w", pady=5)

        r += 1

        # -------- Cliente (combo) --------
        tk.Label(frame, text="Cliente:", bg="white", fg="black")\
            .grid(row=r, column=0, sticky="w", pady=5)

        self.cbo_cliente = ttk.Combobox(
            frame,
            textvariable=self.cliente_nombre,
            state="readonly",
            width=42
        )
        self.cbo_cliente.grid(row=r, column=1, sticky="w", pady=5)
        self.cbo_cliente.bind("<<ComboboxSelected>>", self._on_cliente_select)

        r += 1

        # -------- Campos MANUAL (guardamos widgets para ocultar/mostrar) --------
        self.manual_widgets = []

        self.manual_widgets += self._field(frame, "Buque / Contenedor:", self.buque, r); r += 1
        self.manual_widgets += self._field(frame, "Operación:", self.operacion, r); r += 1
        self.manual_widgets += self._field(frame, "Número de informe:", self.num_informe, r); r += 1
        self.manual_widgets += self._field(frame, "Periodo de operación:", self.periodo_operacion, r); r += 1
        self.manual_widgets += self._field(frame, "Fecha emisión:", self.fecha, r); r += 1
        self.manual_widgets += self._field(frame, "Moneda:", self.moneda, r); r += 1
        self.manual_widgets += self._field(frame, "Término de pago (días):", self.termino_pago, r); r += 1
        self.manual_widgets += self._field(frame, "Total:", self.total, r); r += 1

        # -------- Descripción (manual) --------
        lbl_desc = tk.Label(frame, text="Descripción:", bg="white", fg="black")
        lbl_desc.grid(row=r, column=0, sticky="nw", pady=5)
        self.manual_widgets.append(lbl_desc)

        self.txt_desc = tk.Text(
            frame,
            height=4,
            width=50,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        self.txt_desc.grid(row=r, column=1, pady=5, sticky="w")
        self.manual_widgets.append(self.txt_desc)

        r += 1

        # -------- XML (solo se muestra en modo XML) --------
        self.btn_xml = tk.Button(
            frame,
            text="Cargar XML",
            width=20,
            command=self._cargar_xml,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        self.btn_xml.grid(row=r, column=1, sticky="w", pady=10)

        self.lbl_xml_path = tk.Label(frame, text="", bg="white", fg="black")
        self.lbl_xml_path.grid(row=r + 1, column=1, sticky="w", pady=(0, 10))

        # -------- Botones --------
        btns = tk.Frame(frame, bg="white")
        btns.grid(row=r + 2, column=1, sticky="e", pady=15)

        self.btn_preview = tk.Button(
            btns,
            text="Preview",
            width=18,
            command=self._preview,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        self.btn_preview.pack(side="left", padx=5)

        self.btn_generar = tk.Button(
            btns,
            text="Generar factura",
            width=18,
            command=self._facturar,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        self.btn_generar.pack(side="left", padx=5)

    def _field(self, parent, label, var, row):
        widgets = []

        lbl = tk.Label(parent, text=label, bg="white", fg="black")
        lbl.grid(row=row, column=0, sticky="w", pady=5)
        widgets.append(lbl)

        ent = tk.Entry(
            parent,
            textvariable=var,
            width=45,
            bg="white",
            fg="black",
            relief="solid",
            bd=1
        )
        ent.grid(row=row, column=1, pady=5, sticky="w")
        widgets.append(ent)

        if "Fecha" in label:
            btn = tk.Button(
                parent,
                text="📅",
                width=3,
                command=lambda: DatePicker(self, ent, output_format=LONG_DATE_FORMAT),
                bg="white",
                fg="black",
                relief="solid",
                bd=1
            )
            btn.grid(row=row, column=2, padx=5, sticky="w")
            widgets.append(btn)

        return widgets

    # ============================================================
    # CLIENTES
    # ============================================================
    def _load_clientes(self):
        """
        Carga clientes desde API (tabla cliente) y muestra nombrecomercial.
        """
        try:
            data = get_clientes_finanzas_api()  # [{"codigo":..., "nombre":...}, ...]
            nombres = []
            self._clientes_map.clear()

            for c in data:
                nombre = (c.get("nombre") or "").strip()
                codigo = (c.get("codigo") or "").strip()
                if nombre and codigo:
                    self._clientes_map[nombre] = codigo
                    nombres.append(nombre)

            self.cbo_cliente["values"] = nombres

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar clientes: {e}")

    def _on_cliente_select(self, *_):
        nombre = (self.cliente_nombre.get() or "").strip()
        self.cliente_codigo = self._clientes_map.get(nombre)

    # ============================================================
    # TÉRMINO PAGO (si viene desde servicio, lo muestra)
    # ============================================================
    def _cargar_termino_pago_desde_servicio(self):
        termino = self.servicio.get("termino_pago")
        if termino is not None and str(termino).strip() != "":
            self.termino_pago.set(str(termino))

    # ============================================================
    # MODO MANUAL / XML
    # ============================================================
    def _on_tipo_change(self):
        modo = self.tipo_factura.get()

        if modo == "XML":
            # Ocultar campos manuales
            for w in self.manual_widgets:
                w.grid_remove() if hasattr(w, "grid_remove") else None

            self.btn_preview.pack_forget()  # preview no aplica para XML
            self.btn_xml.grid()
            self.lbl_xml_path.grid()
        else:
            # Mostrar campos manuales
            for w in self.manual_widgets:
                w.grid()  # vuelve a mostrar en su grid original

            # Re-mostrar Preview (si estaba oculto)
            if not self.btn_preview.winfo_ismapped():
                self.btn_preview.pack(side="left", padx=5)

            self.btn_xml.grid_remove()
            self.lbl_xml_path.grid_remove()
            self.xml_path = None
            if self.lbl_xml_path:
                self.lbl_xml_path.config(text="")

    # ============================================================
    # XML
    # ============================================================
    def _cargar_xml(self):
        path = filedialog.askopenfilename(
            title="Seleccionar XML",
            filetypes=[("XML", "*.xml")]
        )
        if path:
            self.xml_path = path
            if self.lbl_xml_path:
                self.lbl_xml_path.config(text=path)
            messagebox.showinfo("XML", "XML cargado correctamente.")

    # ============================================================
    # VALIDACIONES
    # ============================================================
    def _validate_cliente(self) -> bool:
        nombre = (self.cliente_nombre.get() or "").strip()
        if not nombre:
            messagebox.showerror("Error", "Debe seleccionar un cliente.")
            return False

        self.cliente_codigo = self._clientes_map.get(nombre)
        if not self.cliente_codigo:
            messagebox.showerror("Error", "Código de cliente no encontrado.")
            return False

        return True

    def _validate_manual(self) -> bool:
        if not self._validate_cliente():
            return False

        if not self.total.get().strip():
            messagebox.showerror("Error", "El total es obligatorio.")
            return False

        try:
            total = float(self.total.get())
            if total <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Total inválido.")
            return False

        if not self.buque.get().strip():
            messagebox.showerror("Error", "Buque / Contenedor requerido.")
            return False

        if not self.operacion.get().strip():
            messagebox.showerror("Error", "Operación requerida.")
            return False

        if not self.periodo_operacion.get().strip():
            messagebox.showerror("Error", "Periodo de operación requerido.")
            return False

        desc = self.txt_desc.get("1.0", "end").strip()
        if not desc:
            messagebox.showerror("Error", "Descripción requerida.")
            return False

        return True

    # ============================================================
    # GENERAR FACTURA
    # ============================================================
    def _facturar(self):
        if self.tipo_factura.get() == "MANUAL":
            self._facturar_manual()
        else:
            self._facturar_xml()

    def _facturar_manual(self):
        if not self._validate_manual():
            return

        try:
            data = post_invoicing_anticipada_manual_api(
                codigo_cliente=self.cliente_codigo,
                nombre_cliente=self.cliente_nombre.get().strip(),
                num_informe=self.num_informe.get().strip(),
                buque=self.buque.get().strip(),
                operacion=self.operacion.get().strip(),
                periodo_operacion=self.periodo_operacion.get().strip(),
                descripcion=self.txt_desc.get("1.0", "end").strip(),
                moneda=self.moneda.get().strip() or "USD",
                termino_pago=int(self.termino_pago.get().strip() or 0),
                total=float(self.total.get().strip())
            )

            messagebox.showinfo(
                "Factura creada",
                f"Factura Nº {data.get('numero_documento')} creada correctamente."
            )

            self.destroy()
            self.on_success()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _facturar_xml(self):
        if not self._validate_cliente():
            return

        if not self.xml_path:
            messagebox.showerror("Error", "Debe cargar un archivo XML.")
            return

        try:
            data = post_invoicing_anticipada_xml_api(
                codigo_cliente=self.cliente_codigo,
                nombre_cliente=self.cliente_nombre.get().strip(),
                xml_path=self.xml_path
            )

            messagebox.showinfo(
                "Factura creada",
                f"Factura Nº {data.get('numero_documento')} creada correctamente."
            )

            self.destroy()
            self.on_success()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # PREVIEW (solo MANUAL)
    # ============================================================
    def _preview(self):
        if not self._validate_cliente():
            return

        data = {
            # cliente
            "cliente": self.cliente_nombre.get().strip(),
            "nombre_cliente": self.cliente_nombre.get().strip(),
            "codigo_cliente": self.cliente_codigo,

            # fechas / términos
            "fecha_factura": self.fecha.get().strip(),
            "fecha_emision": self.fecha.get().strip(),
            "termino_pago": self.termino_pago.get().strip(),
            "moneda": self.moneda.get().strip() or "USD",

            # servicio
            "buque": self.buque.get().strip(),
            "buque_contenedor": self.buque.get().strip(),
            "operacion": self.operacion.get().strip(),

            "num_informe": self.num_informe.get().strip(),

            "periodo": self.periodo_operacion.get().strip(),
            "periodo_operacion": self.periodo_operacion.get().strip(),

            "descripcion": self.txt_desc.get("1.0", "end").strip(),
            "descripcion_servicio": self.txt_desc.get("1.0", "end").strip(),

            "total": self.total.get().strip()
        }

        from Modulos.Finanzas.popups.popup_preview_factura import PopupPreviewFactura
        PopupPreviewFactura(self, data=data, on_confirm=self._facturar)
