# ============================================================
# POPUP — DETALLE CLIENTE
# Ruta: Modulos/Comercial/popup/popup_cliente_detalle.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox

from api_client import get_comercial_clientes_api
from Modulos.Comercial.date_utils import to_long_english_date


class PopupClienteDetalle(tk.Toplevel):
    """
    POPUP — DETALLE CLIENTE
    Consulta backend y muestra información completa del cliente.
    """

    def __init__(self, parent, cliente_id=None, codigo=None, nombre=None):
        super().__init__(parent)

        self.parent = parent
        self.cliente_id = cliente_id
        self.codigo = codigo
        self.nombre = nombre

        # ----------------------------------------------------
        # CONFIGURACIÓN VENTANA
        # ----------------------------------------------------
        self.title("Cliente — Detalle")
        self.geometry("820x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ----------------------------------------------------
        # CONTENEDOR PRINCIPAL
        # ----------------------------------------------------
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=15, pady=15)

        # ----------------------------------------------------
        # CARGAR DATA CLIENTE
        # ----------------------------------------------------
        try:
            self.cliente_data = self._load_cliente()
        except Exception as e:
            messagebox.showerror("Cliente", str(e))
            self.destroy()
            return

        if not self.cliente_data:
            messagebox.showwarning("Cliente", "Cliente no encontrado")
            self.destroy()
            return

        self.title(f"Cliente — {self.cliente_data.get('nombrecomercial', '')}")

        self._build_ui()

    # ========================================================
    # CARGA CLIENTE DESDE API
    # ========================================================
    def _load_cliente(self):
        resp = get_comercial_clientes_api(
            id=self.cliente_id,
            codigo=self.codigo,
            nombre=self.nombre
        )

        data = resp.get("data", [])
        return data[0] if data else None

    # ========================================================
    # UI
    # ========================================================
    def _build_ui(self):

        # ====================================================
        # SECCIÓN 1 — IDENTIFICACIÓN
        # ====================================================
        sec_id = ttk.LabelFrame(self.container, text="Identificación")
        sec_id.pack(fill="x", pady=5)

        self._row(sec_id, 0, "ID", self.cliente_data.get("id"))
        self._row(sec_id, 1, "Código", self.cliente_data.get("codigo"))
        self._row(sec_id, 2, "Nombre Jurídico", self.cliente_data.get("nombrejuridico"))
        self._row(sec_id, 3, "Nombre Comercial", self.cliente_data.get("nombrecomercial"))

        # ====================================================
        # SECCIÓN 2 — CONTACTO
        # ====================================================
        sec_contacto = ttk.LabelFrame(self.container, text="Contacto")
        sec_contacto.pack(fill="x", pady=5)

        self._row(sec_contacto, 0, "Teléfono", self.cliente_data.get("telefono"))
        self._row(sec_contacto, 1, "Prefijo", self.cliente_data.get("prefijo"))
        self._row(sec_contacto, 2, "Correo(s)", self.cliente_data.get("correo"), wrap=True)
        self._row(sec_contacto, 3, "Contacto Principal", self.cliente_data.get("contacto_principal"))
        self._row(sec_contacto, 4, "Contacto Secundario", self.cliente_data.get("contacto_secundario"))

        # ====================================================
        # SECCIÓN 3 — UBICACIÓN
        # ====================================================
        sec_ubic = ttk.LabelFrame(self.container, text="Ubicación")
        sec_ubic.pack(fill="x", pady=5)

        self._row(sec_ubic, 0, "País", self.cliente_data.get("pais"))
        self._row(sec_ubic, 1, "Provincia", self.cliente_data.get("provincia"))
        self._row(sec_ubic, 2, "Cantón", self.cliente_data.get("canton"))
        self._row(sec_ubic, 3, "Distrito", self.cliente_data.get("distrito"))
        self._row(
            sec_ubic,
            4,
            "Dirección Exacta",
            self.cliente_data.get("direccionexacta"),
            wrap=True
        )

        # ====================================================
        # SECCIÓN 4 — DATOS ADMINISTRATIVOS
        # ====================================================
        sec_admin = ttk.LabelFrame(self.container, text="Datos Administrativos")
        sec_admin.pack(fill="x", pady=5)

        self._row(sec_admin, 0, "Cédula / VAT", self.cliente_data.get("cedulajuridicavat"))
        self._row(sec_admin, 1, "Actividad Económica", self.cliente_data.get("actividad_economica"))
        self._row(sec_admin, 2, "Fecha Creación", to_long_english_date(self.cliente_data.get("creado_en")))
        self._row(sec_admin, 3, "Fecha de Pago", to_long_english_date(self.cliente_data.get("fecha_pago")))

        # ====================================================
        # SECCIÓN 5 — COMENTARIOS
        # ====================================================
        sec_notes = ttk.LabelFrame(self.container, text="Comentarios")
        sec_notes.pack(fill="both", expand=True, pady=5)

        txt = tk.Text(
            sec_notes,
            height=4,
            wrap="word"
        )
        txt.insert("1.0", self.cliente_data.get("comentarios") or "")
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=5, pady=5)

        # ====================================================
        # FOOTER
        # ====================================================
        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=10)

        ttk.Button(
            footer,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right", padx=10)

    # ========================================================
    # HELPER — FILA LABEL / VALUE
    # ========================================================
    def _row(self, parent, row, label, value, wrap=False):
        ttk.Label(
            parent,
            text=f"{label}:",
            width=22,
            anchor="w",
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=row,
            column=0,
            padx=5,
            pady=3,
            sticky="w"
        )

        ttk.Label(
            parent,
            text=value if value not in (None, "") else "-",
            wraplength=520 if wrap else 0,
            justify="left",
            anchor="w"
        ).grid(
            row=row,
            column=1,
            padx=5,
            pady=3,
            sticky="w"
        )
