# ============================================================
# POPUP — NUEVA COTIZACIÓN (MULTI-SERVICIO)
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta

from api_client import (
    get_comercial_precios_api,
    post_comercial_cotizacion_api,
    get_comercial_next_quotation_number_api
)

from Modulos.Comercial.exporters.cotizacion_word_exporter import export_cotizacion_word
from Modulos.Comercial.exporters.cotizacion_pdf_exporter import export_cotizacion_pdf


class PopupNuevaCotizacion(tk.Toplevel):
    """
    Popup para generar una cotización comercial
    con uno o múltiples servicios
    """

    def __init__(self, parent, on_success=None, on_preview=None):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success
        self.on_preview = on_preview

        self.title("Nueva Cotización")
        self.geometry("980x760")
        self.resizable(True, True)
        
        self.grab_set()
        self.resizable(True, True)
        self.attributes("-toolwindow", False)

        # =========================
        # WINDOW STATE
        # =========================
        self._is_maximized = False
        self._normal_geometry = self.geometry()


        # =========================
        # STATE
        # =========================
        self.precios_all = []
        self.servicios_seleccionados = []  # [{servicio, precio}]
        self.total_precio = 0.0

        # =========================
        # QUOTATION NUMBER
        # =========================
        self.quotation_number = ""

        self._build_ui()
        self._load_precios()
        self._load_quotation_number()



    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # =====================================================
        # SCROLL CONTAINER (CANVAS + SCROLLBARS) — BLINDADO
        # =====================================================
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")

        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # El container es el que manda el tamaño
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Frame interno donde va TODO el UI
        self.content = ttk.Frame(self.canvas)
        self._content_window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        # Ajustar scrollregion cuando cambie el contenido
        def _on_content_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.content.bind("<Configure>", _on_content_configure)

        # Ajustar el ancho del content al ancho visible del canvas (evita “huecos” raros)
        def _on_canvas_configure(event):
            self.canvas.itemconfigure(self._content_window_id, width=event.width)

        self.canvas.bind("<Configure>", _on_canvas_configure)

        # =====================================================
        # A PARTIR DE AQUÍ, TODO LO QUE ANTES ERA parent=self
        # AHORA DEBE SER parent=self.content
        # =====================================================

        # =====================================================
        # QUOTATION NUMBER (TOP LEFT)
        # =====================================================
        self.lbl_quotation = ttk.Label(
            self.content,
            text=self.quotation_number or "",
            font=("Segoe UI", 12, "bold"),
            foreground="darkred"
        )
        self.lbl_quotation.pack(anchor="w", padx=12, pady=(8, 2))


        # =====================================================
        # FORM
        # =====================================================
        form = ttk.LabelFrame(self.content, text="Datos Generales")
        form.pack(fill="x", padx=12, pady=6)

        self.cliente_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()
        self.idioma_var = tk.StringVar(value="ES")
        self.validez_var = tk.IntVar(value=15)
        self.formato_var = tk.StringVar(value="WORD")

        self.cb_cliente = ttk.Combobox(form, textvariable=self.cliente_var, state="readonly", width=28)
        self.cb_continente = ttk.Combobox(form, textvariable=self.continente_var, state="readonly", width=20)
        self.cb_pais = ttk.Combobox(form, textvariable=self.pais_var, state="readonly", width=20)
        self.cb_puerto = ttk.Combobox(form, textvariable=self.puerto_var, state="readonly", width=20)

        ttk.Label(form, text="Cliente").grid(row=0, column=0, sticky="w", padx=6)
        self.cb_cliente.grid(row=1, column=0, padx=6)

        ttk.Label(form, text="Continente").grid(row=0, column=1, sticky="w", padx=6)
        self.cb_continente.grid(row=1, column=1, padx=6)

        ttk.Label(form, text="País").grid(row=0, column=2, sticky="w", padx=6)
        self.cb_pais.grid(row=1, column=2, padx=6)

        ttk.Label(form, text="Puerto").grid(row=0, column=3, sticky="w", padx=6)
        self.cb_puerto.grid(row=1, column=3, padx=6)

        ttk.Label(form, text="Idioma").grid(row=2, column=0, sticky="w", padx=6)
        ttk.Combobox(
            form,
            textvariable=self.idioma_var,
            values=["ES", "EN"],
            state="readonly",
            width=10
        ).grid(row=3, column=0, padx=6, sticky="w")

        ttk.Label(form, text="Validez (días)").grid(row=2, column=1, sticky="w", padx=6)
        ttk.Entry(form, textvariable=self.validez_var, width=10)\
            .grid(row=3, column=1, padx=6, sticky="w")

        ttk.Label(form, text="Formato").grid(row=2, column=2, sticky="w", padx=6)
        ttk.Combobox(
            form,
            textvariable=self.formato_var,
            values=["WORD", "PDF"],
            state="readonly",
            width=10
        ).grid(row=3, column=2, padx=6, sticky="w")

        # =====================================================
        # SERVICIOS (MULTI)
        # =====================================================
        servicios_frame = ttk.LabelFrame(self.content, text="Servicios Cotizados")
        servicios_frame.pack(fill="both", expand=True, padx=12, pady=6)

        left = ttk.Frame(servicios_frame)
        left.pack(side="left", fill="y", padx=6)

        right = ttk.Frame(servicios_frame)
        right.pack(side="right", fill="both", expand=True, padx=6)

        self.cb_servicio = ttk.Combobox(left, state="readonly", width=30)
        self.cb_servicio.pack(pady=4)

        ttk.Button(left, text="Agregar Servicio", command=self._agregar_servicio).pack(pady=4)
        ttk.Button(left, text="Quitar Servicio", command=self._quitar_servicio).pack(pady=4)

        self.tree = ttk.Treeview(
            right,
            columns=("servicio", "precio"),
            show="headings",
            height=6
        )
        self.tree.heading("servicio", text="Servicio")
        self.tree.heading("precio", text="Precio")
        self.tree.column("servicio", width=280)
        self.tree.column("precio", width=120, anchor="e")
        self.tree.pack(fill="both", expand=True)

        self.lbl_total = ttk.Label(
            right,
            text="Total: 0.00",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_total.pack(anchor="e", pady=6)

        # =====================================================
        # TEXTO
        # =====================================================
        text_frame = ttk.LabelFrame(self.content, text="Texto de la Cotización")
        text_frame.pack(fill="both", expand=True, padx=12, pady=6)

        self.text = tk.Text(text_frame, wrap="word")
        self.text.pack(fill="both", expand=True, padx=6, pady=6)

        self._build_text_base()

        # =====================================================
        # FOOTER
        # =====================================================
        footer = ttk.Frame(self.content)
        footer.pack(fill="x", padx=12, pady=10)

        ttk.Button(
            footer,
            text="Exportar WORD",
            command=lambda: self._exportar("WORD")
        ).pack(side="right", padx=6)

        ttk.Button(
            footer,
            text="Exportar PDF",
            command=lambda: self._exportar("PDF")
        ).pack(side="right", padx=6)

        ttk.Button(
            footer,
            text="Confirmar y Guardar",
            command=self._guardar_cotizacion
        ).pack(side="right", padx=6)

    # =========================================================
    # DATA
    # =========================================================
    def _load_precios(self):
        resp = get_comercial_precios_api()
        self.precios_all = resp.get("data", [])

        self.cb_cliente["values"] = sorted({p["cliente"] for p in self.precios_all})
        self.cb_servicio["values"] = sorted({p["servicio"] for p in self.precios_all})
        self.cb_continente["values"] = sorted({p["continente"] for p in self.precios_all if p.get("continente")})
        self.cb_pais["values"] = sorted({p["pais"] for p in self.precios_all if p.get("pais")})
        self.cb_puerto["values"] = sorted({p["puerto"] for p in self.precios_all if p.get("puerto")})

    # =========================================================
    # SERVICIOS
    # =========================================================
    def _agregar_servicio(self):
        servicio = self.cb_servicio.get()
        if not servicio:
            return

        for p in self.precios_all:
            if (
                p["cliente"] == self.cliente_var.get()
                and p["servicio"] == servicio
                and p.get("pais") == self.pais_var.get()
                and p.get("puerto") == self.puerto_var.get()
                and p.get("activo")
            ):
                self.servicios_seleccionados.append(p)
                break
        else:
            messagebox.showwarning("Servicio", "No existe precio configurado")
            return

        self._refresh_servicios()

    def _quitar_servicio(self):
        sel = self.tree.selection()
        if not sel:
            return

        idx = self.tree.index(sel[0])
        del self.servicios_seleccionados[idx]
        self._refresh_servicios()

    def _refresh_servicios(self):
        self.tree.delete(*self.tree.get_children())
        self.total_precio = 0.0

        for p in self.servicios_seleccionados:
            self.tree.insert(
                "",
                "end",
                values=(p["servicio"], f"$ {float(p['precio']):,.2f} USD")
            )
            self.total_precio += float(p["precio"])

        self.lbl_total.config(text=f"Total: $ {self.total_precio:,.2f} USD")
        self._build_text_base()

    # =========================================================
    # TEXTO
    # =========================================================
    def _build_text_base(self):
        self.text.delete("1.0", "end")

        hoy = date.today()
        valido = hoy + timedelta(days=self.validez_var.get())
        cliente = self.cliente_var.get() or "Client"

        servicios_txt = "\n".join(
           f"- {p['servicio']}: $ {float(p['precio']):,.2f} USD"
            for p in self.servicios_seleccionados
        )

        if self.idioma_var.get() == "EN":
            txt = (
                f"Dear {cliente},\n\n"
                f"We are pleased to submit our quotation for the following services:\n\n"
                f"{servicios_txt}\n\n"
                f"Total amount: USD {self.total_precio:,.2f}\n\n"
                f"This quotation is valid until {valido}.\n"
                f"Payment terms: 30 days from invoice date.\n\n"
                f"Sincerely,\n"
                f"Marine Surveyors & Logistics Group SRL"
            )
        else:
            txt = (
                f"Estimado {cliente},\n\n"
                f"Por medio de la presente compartimos la cotización para los siguientes servicios:\n\n"
                f"{servicios_txt}\n\n"
                f"Monto total: $ {self.total_precio:,.2f} USD\n\n"
                f"Esta cotización tiene una validez hasta el {valido}.\n"
                f"Términos de pago: 30 días fecha factura.\n\n"
                f"Atentamente,\n"
                f"Marine Surveyors & Logistics Group SRL"
            )

        self.text.insert("1.0", txt)

    # =========================================================
    # ACTION
    # =========================================================
    def _generar(self):

        if not self.servicios_seleccionados:
            messagebox.showwarning("Cotización", "Debe agregar al menos un servicio")
            return

        ext = "docx" if self.formato_var.get() == "WORD" else "pdf"

        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[("Word", "*.docx")] if ext == "docx" else [("PDF", "*.pdf")]
        )
        if not path:
            return

        data = {
            "cliente": self.cliente_var.get(),
            "servicio": ", ".join(p["servicio"] for p in self.servicios_seleccionados),
            "pais": self.pais_var.get(),
            "puerto": self.puerto_var.get(),
            "precio": self.total_precio,
            "idioma": self.idioma_var.get(),
            "validez_dias": self.validez_var.get(),
            "texto": self.text.get("1.0", "end")
        }

        try:
            # EXPORT
            export_data = {
                "quotation_number": self.quotation_number,
                "cliente": self.cliente_var.get(),
                "servicio": ", ".join(p["servicio"] for p in self.servicios_seleccionados),
                "idioma": self.idioma_var.get(),
                "texto": self.text.get("1.0", "end")
            }

            if self.formato_var.get() == "WORD":
                export_cotizacion_word(export_data, path)
            else:
                export_cotizacion_pdf(export_data, path)

            # API
            api_data = {
                "cliente": self.cliente_var.get(),
                "servicio": ", ".join(p["servicio"] for p in self.servicios_seleccionados),
                "continente": self.continente_var.get(),
                "pais": self.pais_var.get(),
                "puerto": self.puerto_var.get(),
                "precio": self.total_precio,
                "idioma": self.idioma_var.get(),
                "validez": self.validez_var.get(),
                "status": "PENDIENTE"
            }

            for i, p in enumerate(self.servicios_seleccionados[:4], start=1):
                api_data[f"servicio_{i}"] = p["servicio"]
                api_data[f"precio_{i}"] = float(p["precio"])

            post_comercial_cotizacion_api(api_data)

            if callable(self.on_success):
                self.on_success()

            messagebox.showinfo("Cotización", "Cotización generada correctamente")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # WINDOW CONTROLS
    # =========================================================
    def _minimize(self):
        self.iconify()

    def _toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            self.state("zoomed")  # Windows
            self._is_maximized = True
        else:
            self.state("normal")
            self.geometry(self._normal_geometry)
            self._is_maximized = False


    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


    # =========================================================
    # QUOTATION NUMBER
    # =========================================================
    def _load_quotation_number(self):
        try:
            resp = get_comercial_next_quotation_number_api()
            self.quotation_number = resp.get("quotation_number", "")

            if hasattr(self, "lbl_quotation"):
                self.lbl_quotation.config(text=self.quotation_number)

            self._build_text_base()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo obtener el consecutivo de cotización\n{e}"
            )
            self.quotation_number = "Quotation ?????"


    # =========================================================
    # EXPORT (WORD / PDF) — NO GUARDA
    # =========================================================
    def _exportar(self, formato: str):

        if not self.servicios_seleccionados:
            messagebox.showwarning(
                "Cotización",
                "Debe agregar al menos un servicio"
            )
            return

        ext = "docx" if formato == "WORD" else "pdf"

        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[("Word", "*.docx")] if ext == "docx" else [("PDF", "*.pdf")]
        )
        if not path:
            return

        export_data = {
            "quotation_number": self.quotation_number,
            "cliente": self.cliente_var.get(),
            "servicio": ", ".join(p["servicio"] for p in self.servicios_seleccionados),
            "idioma": self.idioma_var.get(),
            "texto": self.text.get("1.0", "end")
        }

        try:
            if formato == "WORD":
                export_cotizacion_word(export_data, path)
            else:
                export_cotizacion_pdf(export_data, path)

            messagebox.showinfo(
                "Exportación",
                f"{formato} generado correctamente"
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # GUARDAR COTIZACIÓN — 1 SOLA VEZ
    # =========================================================
    def _guardar_cotizacion(self):

        if not self.servicios_seleccionados:
            messagebox.showwarning(
                "Cotización",
                "Debe agregar al menos un servicio"
            )
            return

        api_data = {
            "cliente": self.cliente_var.get(),
            "servicio": ", ".join(p["servicio"] for p in self.servicios_seleccionados),
            "continente": self.continente_var.get(),
            "pais": self.pais_var.get(),
            "puerto": self.puerto_var.get(),
            "precio": self.total_precio,
            "idioma": self.idioma_var.get(),
            "validez": self.validez_var.get(),
            "status": "PENDIENTE"
        }

        for i, p in enumerate(self.servicios_seleccionados[:4], start=1):
            api_data[f"servicio_{i}"] = p["servicio"]
            api_data[f"precio_{i}"] = float(p["precio"])

        try:
            post_comercial_cotizacion_api(api_data)

            if callable(self.on_success):
                self.on_success()

            messagebox.showinfo(
                "Cotización",
                "Cotización guardada correctamente"
            )

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))


