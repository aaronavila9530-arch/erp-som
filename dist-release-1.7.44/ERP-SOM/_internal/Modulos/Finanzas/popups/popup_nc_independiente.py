import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os

from api_client import BASE_URL


class PopupNotaCreditoIndependiente(tk.Toplevel):

    def __init__(self, parent, nombre_cliente, codigo_cliente):
        super().__init__(parent)

        self.parent = parent
        self.nombre_cliente = nombre_cliente
        self.codigo_cliente = codigo_cliente

        self.title("Nota de Crédito (NC)")
        self.geometry("560x520")
        self.resizable(False, False)

        # ================= MODAL =================
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        # ================= ESTADO =================
        self.tipo = tk.StringVar(value="MANUAL")
        self.xml_path = None

        # ================= UI =================
        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = tk.Frame(self, padx=20, pady=20)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text=f"Cliente: {self.nombre_cliente}",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 15))

        tipo_frame = ttk.LabelFrame(container, text="Tipo de Nota de Crédito")
        tipo_frame.pack(fill="x", pady=(0, 15))

        ttk.Radiobutton(
            tipo_frame,
            text="NC Manual",
            variable=self.tipo,
            value="MANUAL",
            command=self._toggle_tipo
        ).pack(anchor="w", padx=10, pady=5)

        ttk.Radiobutton(
            tipo_frame,
            text="Cargar XML (NC electrónica)",
            variable=self.tipo,
            value="XML",
            command=self._toggle_tipo
        ).pack(anchor="w", padx=10, pady=5)

        self.frm_manual = ttk.LabelFrame(
            container,
            text="Datos de la Nota de Crédito"
        )
        self.frm_manual.pack(fill="x")
        self._build_manual_fields()

        self.frm_xml = ttk.Frame(container)
        self.frm_xml.pack(fill="x")
        self.frm_xml.pack_forget()
        self._build_xml_fields()

        actions = tk.Frame(container)
        actions.pack(fill="x", pady=20)

        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Emitir NC", command=self._emitir).pack(side="right", padx=10)

    # ============================================================
    # MANUAL (NO TOCADO)
    # ============================================================
    def _build_manual_fields(self):

        f = self.frm_manual

        self.num_informe = tk.StringVar()
        self.buque = tk.StringVar()
        self.operacion = tk.StringVar()
        self.periodo = tk.StringVar()
        self.puerto = tk.StringVar()
        self.pais = tk.StringVar()
        self.detalle = tk.StringVar()
        self.monto = tk.StringVar()

        def row(label, var):
            r = ttk.Frame(f)
            r.pack(fill="x", pady=4)
            ttk.Label(r, text=label, width=22).pack(side="left")
            ttk.Entry(r, textvariable=var).pack(side="left", fill="x", expand=True)

        row("Número de informe:", self.num_informe)
        row("Buque / Contenedor:", self.buque)
        row("Operación:", self.operacion)
        row("Periodo de operación:", self.periodo)
        row("Puerto:", self.puerto)
        row("País:", self.pais)
        row("Detalle *:", self.detalle)
        row("Monto *:", self.monto)

    # ============================================================
    # XML UI
    # ============================================================
    def _build_xml_fields(self):

        ttk.Button(
            self.frm_xml,
            text="Seleccionar archivo XML",
            command=self._seleccionar_xml
        ).pack(anchor="w")

        self.lbl_xml = ttk.Label(
            self.frm_xml,
            text="Ningún archivo seleccionado",
            foreground="gray"
        )
        self.lbl_xml.pack(anchor="w", pady=5)

    # ============================================================
    # TOGGLE
    # ============================================================
    def _toggle_tipo(self):

        if self.tipo.get() == "MANUAL":
            self.frm_xml.pack_forget()
            self.frm_manual.pack(fill="x")
        else:
            self.frm_manual.pack_forget()
            self.frm_xml.pack(fill="x")

    # ============================================================
    # XML SELECT
    # ============================================================
    def _seleccionar_xml(self):

        path = filedialog.askopenfilename(
            title="Seleccionar Nota de Crédito electrónica",
            filetypes=[("XML", "*.xml")]
        )

        if not path:
            return

        self.xml_path = path
        self.lbl_xml.config(text=os.path.basename(path), foreground="black")

    # ============================================================
    # EMITIR
    # ============================================================
    def _emitir(self):

        # ---------------- MANUAL (NO TOCADO) ----------------
        if self.tipo.get() == "MANUAL":

            payload = {
                "tipo_factura": "MANUAL",
                "codigo_cliente": self.codigo_cliente,
                "nombre_cliente": self.nombre_cliente,
                "descripcion": self.detalle.get(),
                "total": float(self.monto.get() or 0),
                "moneda": "USD"
            }

            try:
                r = requests.post(
                    f"{BASE_URL}/invoicing/nota-credito",
                    json=payload,
                    timeout=30
                )
                r.raise_for_status()

                numero = r.json().get("numero_documento", "—")
                messagebox.showinfo(
                    "Nota de Crédito",
                    f"NC emitida.\nNúmero: {numero}"
                )
                self.destroy()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        # ---------------- XML (ÚNICO CAMBIO) ----------------
        else:

            if not self.xml_path:
                messagebox.showwarning(
                    "Validación",
                    "Debe seleccionar un archivo XML"
                )
                return

            if not self.xml_path.lower().endswith(".xml"):
                messagebox.showwarning(
                    "Validación",
                    "El archivo seleccionado debe ser .xml"
                )
                return

            try:
                with open(self.xml_path, "r", encoding="utf-8") as f:
                    xml_content = f.read()

                payload = {
                    "tipo_factura": "XML",
                    "codigo_cliente": self.codigo_cliente,
                    "nombre_cliente": self.nombre_cliente,
                    "xml_content": xml_content
                }

                r = requests.post(
                    f"{BASE_URL}/invoicing/nota-credito",
                    json=payload,
                    timeout=60
                )

                r.raise_for_status()

                resp = r.json()
                numero = resp.get("numero_documento", "—")

                messagebox.showinfo(
                    "Nota de Crédito emitida",
                    f"NC emitida correctamente.\n\nNúmero: {numero}"
                )

                self.destroy()

            except requests.exceptions.HTTPError:
                messagebox.showerror("Error", r.text)
            except Exception as e:
                messagebox.showerror("Error", str(e))
