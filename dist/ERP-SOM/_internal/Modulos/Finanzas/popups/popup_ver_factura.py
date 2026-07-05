import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import subprocess
import sys

from Modulos.Finanzas.date_utils import to_long_english_date


class PopupVerFactura(tk.Toplevel):

    def __init__(self, parent, factura):
        super().__init__(parent)

        self.factura = factura  # dict desde API

        self.title("Ver Factura")
        self.geometry("420x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ================= VALIDACIÓN BASE =================
        if not self.factura:
            messagebox.showerror(
                "Error",
                "No se recibió información de la factura"
            )
            self.destroy()
            return

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        frame = tk.Frame(self)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(
            frame,
            text="Factura",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # -------- INFO --------
        info = [
            ("Tipo:", self.factura.get("tipo_factura", "")),
            ("Cliente:", self.factura.get("codigo_cliente", "")),
            ("Fecha:", to_long_english_date(self.factura.get("fecha_emision", ""))),
            ("Total:", self.factura.get("total", "")),
        ]

        for label, value in info:
            row = tk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=12).pack(side="left")
            ttk.Label(row, text=str(value)).pack(side="left")

        # -------- ACTIONS --------
        actions = tk.Frame(frame)
        actions.pack(fill="x", pady=20)

        ttk.Button(
            actions,
            text="Ver archivo",
            command=self._ver_archivo
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Guardar como…",
            command=self._guardar_archivo
        ).pack(side="left", padx=10)

        ttk.Button(
            actions,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right")

    # ============================================================
    # HELPERS
    # ============================================================
    def _get_file_path(self):
        """
        Devuelve ruta ABSOLUTA al archivo PDF o XML
        """
        path = self.factura.get("pdf_path") or self.factura.get("xml_path")

        if not path:
            return None

        # Normalizar separadores
        path = os.path.normpath(path)

        # Si el backend guardó ruta relativa, convertirla a absoluta
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        return path

    # ============================================================
    # ACTIONS
    # ============================================================
    def _ver_archivo(self):
        file_path = self._get_file_path()

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror(
                "Error",
                "Archivo de factura no encontrado en el sistema"
            )
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el archivo:\n{str(e)}"
            )

    def _guardar_archivo(self):
        file_path = self._get_file_path()

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror(
                "Error",
                "Archivo de factura no encontrado"
            )
            return

        ext = os.path.splitext(file_path)[1].lower()

        dest = filedialog.asksaveasfilename(
            title="Guardar factura",
            defaultextension=ext or ".pdf",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("XML files", "*.xml"),
                ("Todos", "*.*")
            ]
        )

        if not dest:
            return

        try:
            shutil.copy(file_path, dest)
            messagebox.showinfo(
                "OK",
                "Factura guardada correctamente"
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar el archivo:\n{str(e)}"
            )
