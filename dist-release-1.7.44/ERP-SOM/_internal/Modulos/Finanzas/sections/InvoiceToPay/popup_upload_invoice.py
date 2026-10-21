import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import requests
import xml.etree.ElementTree as ET

from api_client import BASE_URL


class PopupUploadInvoice(tk.Toplevel):

    def __init__(self, parent, on_success=None):
        super().__init__(parent)

        self.on_success = on_success

        self.title("Cargar factura electrónica (XML)")
        self.geometry("500x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(
            frame,
            text="Carga de Facturas Electrónicas",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 15))

        ttk.Button(
            frame,
            text="📄 Cargar XML individual",
            command=self._upload_xml
        ).pack(fill="x", pady=5)

        ttk.Separator(frame).pack(fill="x", pady=15)

        ttk.Label(
            frame,
            text="Carga masiva (solo XML)",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        ttk.Button(
            frame,
            text="📂 Cargar múltiples XML",
            command=self._upload_multiple_xml
        ).pack(fill="x", pady=5)

        ttk.Button(
            frame,
            text="Cancelar",
            command=self.destroy
        ).pack(pady=20)

    # ============================================================
    # XML INDIVIDUAL
    # ============================================================
    def _upload_xml(self):

        path = filedialog.askopenfilename(
            filetypes=[("XML files", "*.xml")]
        )
        if not path:
            return

        try:
            self._send_xml(path)

            messagebox.showinfo(
                "XML cargado",
                "Factura electrónica cargada correctamente."
            )

            if self.on_success:
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el XML:\n{e}"
            )

    # ============================================================
    # XML MASIVO
    # ============================================================
    def _upload_multiple_xml(self):

        paths = filedialog.askopenfilenames(
            filetypes=[("XML files", "*.xml")]
        )
        if not paths:
            return

        ok = 0
        fail = 0

        for path in paths:
            try:
                self._send_xml(path, silent=True)
                ok += 1
            except Exception:
                fail += 1

        messagebox.showinfo(
            "Carga finalizada",
            f"XML cargados correctamente: {ok}\nErrores: {fail}"
        )

        if self.on_success:
            self.on_success()

        self.destroy()

    # ============================================================
    # ENVÍO XML (BACKEND-DRIVEN)
    # ============================================================
    def _send_xml(self, path, silent=False):

        try:
            with open(path, "rb") as f:
                response = requests.post(
                    f"{BASE_URL}/invoice-to-pay/upload/xml",
                    files={"file": f},
                    timeout=30
                )

            response.raise_for_status()

        except Exception as e:
            if silent:
                raise
            raise Exception(str(e))
