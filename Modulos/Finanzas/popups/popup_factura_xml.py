import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

from api_client import post_factura_electronica_xml_api


class PopupFacturaXML(tk.Toplevel):
    """
    Factura Electrónica (XML)
    LIGADA a un servicio finalizado.
    """

    def __init__(self, parent, servicio, on_success):
        super().__init__(parent)

        self.servicio = servicio
        self.on_success = on_success

        self.title("Factura Electrónica (XML)")
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ====================================================
        # VALIDACIÓN ESTRUCTURAL (IGUAL QUE MANUAL)
        # ====================================================
        if not self.servicio or not self.servicio.get("consec"):
            messagebox.showerror(
                "Error",
                "Servicio inválido o no seleccionado."
            )
            self.destroy()
            return

        self._build_ui()

    # ====================================================
    # UI
    # ====================================================
    def _build_ui(self):

        frame = tk.Frame(self, bg="white")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(
            frame,
            text=(
                "Seleccione el archivo XML de la factura electrónica.\n\n"
                "Este documento quedará LIGADO al servicio seleccionado."
            ),
            wraplength=360,
            justify="center"
        ).pack(pady=20)

        ttk.Button(
            frame,
            text="Seleccionar XML",
            width=25,
            command=self._seleccionar_xml
        ).pack(pady=10)

    # ====================================================
    # ACTION
    # ====================================================
    def _seleccionar_xml(self):

        xml_path = filedialog.askopenfilename(
            title="Seleccionar factura electrónica (XML)",
            filetypes=[("Archivos XML", "*.xml")]
        )

        if not xml_path:
            return

        if not os.path.exists(xml_path):
            messagebox.showerror(
                "Error",
                "El archivo seleccionado no existe."
            )
            return

        try:
            # ====================================================
            # LLAMADA AL API (BACKEND HACE TODO)
            # ====================================================
            post_factura_electronica_xml_api(
                servicio_id=self.servicio["consec"],
                xml_path=xml_path
            )

            messagebox.showinfo(
                "Factura electrónica",
                "La factura electrónica fue registrada correctamente."
            )

            self.destroy()

            # 🔁 MISMO COMPORTAMIENTO QUE FACTURA MANUAL
            if callable(self.on_success):
                self.on_success()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar la factura electrónica:\n{str(e)}"
            )
