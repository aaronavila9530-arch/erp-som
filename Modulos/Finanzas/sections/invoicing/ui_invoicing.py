import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL


class InvoicingUI(tk.Frame):

    def __init__(self, parent, on_back=None):
        super().__init__(parent, bg="white")
        self.on_back = on_back

        # ================= ESTADO =================
        self.selected_cliente = tk.StringVar()
        self.clientes_loaded = False

        self.clientes_map = {}     # nombre → codigo_cliente
        self.servicios = []
        self.selected_servicio = None

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        # ================= HEADER =================
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            header,
            text="Invoicing & Billing",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        if self.on_back:
            ttk.Button(
                header,
                text="⬅ Volver",
                command=self.on_back
            ).pack(side="right")

        # ================= FILTROS =================
        filtros = tk.Frame(self, bg="white")
        filtros.pack(fill="x", padx=20, pady=10)

        ttk.Label(filtros, text="Cliente:", width=15).pack(side="left")

        self.cbo_cliente = ttk.Combobox(
            filtros,
            textvariable=self.selected_cliente,
            state="readonly",
            width=40
        )
        self.cbo_cliente.pack(side="left", padx=5)
        self.cbo_cliente.bind("<Button-1>", self._load_clientes)

        ttk.Button(
            filtros,
            text="Buscar",
            command=self._on_buscar
        ).pack(side="left", padx=10)

        # ================= INFO =================
        self.info_label = ttk.Label(
            self,
            text="Seleccione un cliente y presione Buscar",
            foreground="gray"
        )
        self.info_label.pack(padx=20, pady=10)

        # ================= TABLA =================
        self.table_container = tk.Frame(self, bg="white")
        self.table_container.pack(fill="both", expand=True, padx=20, pady=10)

        # ================= ACTIONS =================
        actions = tk.Frame(self, bg="white")
        actions.pack(fill="x", padx=20, pady=10)

        # ---- Facturación normal (por servicio) ----
        self.btn_manual = ttk.Button(
            actions,
            text="Factura Manual",
            state="disabled",
            command=self._factura_manual
        )
        self.btn_manual.pack(side="left")

        self.btn_xml = ttk.Button(
            actions,
            text="Factura Electrónica (XML)",
            state="disabled",
            command=self._factura_xml
        )
        self.btn_xml.pack(side="left", padx=10)

        self.btn_ver = ttk.Button(
            actions,
            text="Ver Factura",
            state="disabled",
            command=self._ver_factura
        )
        self.btn_ver.pack(side="left", padx=(0, 20))

        # ---- NUEVO: Facturación independiente ----
        ttk.Separator(actions, orient="vertical").pack(
            side="left", fill="y", padx=10
        )

        ttk.Button(
            actions,
            text="🟦 Facturación Anticipada",
            command=self._facturacion_anticipada
        ).pack(side="left", padx=5)

        ttk.Button(
            actions,
            text="🟥 Nota de Crédito (NC)",
            command=self._nota_credito
        ).pack(side="left", padx=5)

    # ============================================================
    # DATA
    # ============================================================
    def _load_clientes(self, *_):
        if self.clientes_loaded:
            return

        try:
            r = requests.get(f"{BASE_URL}/clientes", timeout=15)
            r.raise_for_status()

            data = r.json().get("data", [])

            self.clientes_map.clear()
            nombres = []

            for c in data:
                nombre = c.get("nombrecomercial") or c.get("nombrejuridico")
                codigo = c.get("codigo")

                if nombre and codigo:
                    self.clientes_map[nombre] = codigo.strip()
                    nombres.append(nombre)

            self.cbo_cliente["values"] = nombres
            self.clientes_loaded = True

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_buscar(self):
        if not self.selected_cliente.get():
            messagebox.showwarning("Atención", "Seleccione un cliente")
            return

        nombre_cliente = self.selected_cliente.get()

        try:
            r = requests.get(
                f"{BASE_URL}/invoicing/facturables",
                params={"cliente": nombre_cliente},
                timeout=20
            )
            r.raise_for_status()

            self.servicios = r.json().get("data", [])

            for widget in self.table_container.winfo_children():
                widget.destroy()

            self.selected_servicio = None
            self.btn_manual["state"] = "disabled"
            self.btn_xml["state"] = "disabled"
            self.btn_ver["state"] = "disabled"

            if not self.servicios:
                self.info_label.config(
                    text="Sin servicios pendientes por facturar",
                    foreground="gray"
                )
                return

            self.info_label.config(
                text=f"{len(self.servicios)} servicios listos para facturar",
                foreground="green"
            )

            self._draw_table()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # TABLE
    # ============================================================
    def _draw_table(self):

        columns = [
            "tipo",
            "buque_contenedor",
            "num_informe",
            "detalle",
            "cliente",
            "continente",
            "pais",
            "puerto",
            "operacion",
            "fecha_inicio",
            "hora_inicio",
            "fecha_fin",
            "hora_fin",
            "demoras",
            "duracion"
        ]

        # --------------------------------------------------------
        # Limpiar contenedor (evita tablas duplicadas)
        # --------------------------------------------------------
        for w in self.table_container.winfo_children():
            w.destroy()

        # --------------------------------------------------------
        # Frame interno (patrón correcto Tkinter)
        # --------------------------------------------------------
        frame = tk.Frame(self.table_container, bg="white")
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings"
        )

        scroll_y = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview
        )
        scroll_x = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=tree.xview
        )

        tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        # --------------------------------------------------------
        # Layout correcto (grid, no pack)
        # --------------------------------------------------------
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # --------------------------------------------------------
        # Headers
        # --------------------------------------------------------
        for col in columns:
            header = col.replace("_", " ").upper()
            if col == "buque_contenedor":
                header = "BUQUE / CONTENEDOR"

            tree.heading(col, text=header)
            tree.column(col, width=150, anchor="w")

        # --------------------------------------------------------
        # Data
        # --------------------------------------------------------
        for s in self.servicios:
            row = []

            for col in columns:
                value = s.get(col)

                if col in ("duracion", "demoras"):
                    value = self._format_duracion(value)

                row.append(value)

            tree.insert("", "end", values=row)

        tree.bind("<<TreeviewSelect>>", lambda e: self._on_select(tree))
        self.tree = tree


    def _on_select(self, tree):
        sel = tree.selection()
        if not sel:
            return

        index = tree.index(sel[0])
        self.selected_servicio = self.servicios[index]

        self.btn_manual["state"] = "normal"
        self.btn_xml["state"] = "normal"

        self.btn_ver["state"] = (
            "normal" if self.selected_servicio.get("factura") else "disabled"
        )

    # ============================================================
    # ACTIONS – FACTURACIÓN NORMAL
    # ============================================================
    def _factura_manual(self):
        if not self.selected_servicio:
            return
        from Modulos.Finanzas.popups.popup_factura_manual import PopupFacturaManual
        PopupFacturaManual(self, self.selected_servicio, self._on_buscar)

    def _factura_xml(self):
        if not self.selected_servicio:
            return
        from Modulos.Finanzas.popups.popup_factura_xml import PopupFacturaXML
        PopupFacturaXML(self, self.selected_servicio, self._on_buscar)

    def _ver_factura(self):
        messagebox.showinfo(
            "Pendiente",
            "Visor de factura se implementa en el siguiente paso"
        )

    # ============================================================
    # ACTIONS – NUEVOS FLUJOS
    # ============================================================
    def _facturacion_anticipada(self):
        from Modulos.Finanzas.popups.popup_facturacion_anticipada import (
            PopupFacturacionAnticipada
        )

        PopupFacturacionAnticipada(
            parent=self,
            on_success=self._on_buscar
        )

    def _nota_credito(self):
        if not self.selected_cliente.get():
            messagebox.showwarning(
                "Atención",
                "Debe seleccionar un cliente"
            )
            return

        from Modulos.Finanzas.popups.popup_nc_independiente import (
            PopupNotaCreditoIndependiente
        )

        PopupNotaCreditoIndependiente(
            parent=self,
            nombre_cliente=self.selected_cliente.get(),
            codigo_cliente=self.clientes_map.get(self.selected_cliente.get())
        )


    # ============================================================
    # HELPERS
    # ============================================================
    def _format_duracion(self, minutos):
        if not minutos:
            return ""

        try:
            total_min = int(float(minutos))
        except (ValueError, TypeError):
            return ""

        dias = total_min // (24 * 60)
        horas = (total_min % (24 * 60)) // 60
        mins = total_min % 60

        parts = []
        if dias:
            parts.append(f"{dias}D")
        if horas:
            parts.append(f"{horas}H")
        if mins:
            parts.append(f"{mins}M")

        return " ".join(parts)
