import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from Modulos.HHRR.ui_lazy_table import TablaLazy
from api_client import listar_eventos_hr, hr_download_payslip_pdf


class VistaColillasEmployee(ttk.Frame):

    def __init__(self, parent, empleado_id=None, rol=None):
        super().__init__(parent)

        self.rol = (rol or "").lower().strip()
        self.data = []

        self._construir_ui()
        self._cargar_colillas()  # 🔥 IMPORTANTE

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        columnas = ["periodo", "status"]

        self.tabla = TablaLazy(
            self,
            columnas=columnas,
            ancho_columnas={
                "periodo": 150,
                "status": 120
            }
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=10)

        cont_btn = ttk.Frame(self)
        cont_btn.pack(fill="x", pady=5)

        ttk.Button(
            cont_btn,
            text="Recargar",
            command=self._cargar_colillas
        ).pack(side="left", padx=5)

        ttk.Button(
            cont_btn,
            text="Descargar",
            command=self._descargar_colilla
        ).pack(side="right", padx=5)

    # =========================================================
    # CARGA DATA (SIN get_payslips_api)
    # =========================================================
    def _cargar_colillas(self):

        try:
            datos = listar_eventos_hr(event_type="PAYSLIP")
        except Exception as e:
            messagebox.showerror("Error", f"Backend error:\n{e}")
            return

        if not isinstance(datos, list):
            datos = []

        filas = []
        self.data = []

        for d in datos:

            if not isinstance(d, dict):
                continue

            payload = d.get("payload") or {}

            year = payload.get("year")
            month = payload.get("month")

            periodo = payload.get("periodo")

            if not periodo:
                if year and month:
                    periodo = f"{year}-{str(month).zfill(2)}"
                else:
                    periodo = "—"

            fila = {
                "periodo": periodo,
                "status": d.get("status") or "—",
                "_year": year,
                "_month": month,
                "_usuario": payload.get("usuario") or d.get("usuario")
            }

            filas.append(fila)
            self.data.append(fila)

        self.tabla.cargar_datos(filas)

        if not filas:
            messagebox.showinfo("Info", "No hay colillas disponibles")

    # =========================================================
    # DESCARGA
    # =========================================================
    def _descargar_colilla(self):

        row = self.tabla.obtener_seleccionado()

        if not row:
            messagebox.showwarning("Atención", "Seleccione una colilla")
            return

        year = row.get("_year")
        month = row.get("_month")
        usuario = row.get("_usuario")

        if not year or not month:
            messagebox.showerror("Error", "Datos incompletos de la colilla")
            return

        filename = f"COLILLA_{usuario or 'COLILLA'}_{year}_{month}.pdf"

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=filename,
            filetypes=[("PDF", "*.pdf")]
        )

        if not path:
            return

        try:
            resp = hr_download_payslip_pdf(
                year=year,
                month=month,
                usuario=usuario
            )

            if resp is None:
                raise Exception("Respuesta vacía")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al descargar:\n{e}")
            return

        try:
            with open(path, "wb") as f:

                if hasattr(resp, "iter_content"):
                    for chunk in resp.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                elif isinstance(resp, (bytes, bytearray)):
                    f.write(resp)
                else:
                    raise Exception("Formato de respuesta no soportado")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return

        messagebox.showinfo("OK", "Colilla descargada correctamente")
