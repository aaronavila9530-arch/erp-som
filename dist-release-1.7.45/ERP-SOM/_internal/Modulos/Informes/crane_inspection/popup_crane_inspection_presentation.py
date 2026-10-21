import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader

import api_client


class PopupCraneInspectionPresentation(tk.Toplevel):

    def __init__(self, parent, record_id: int):
        super().__init__(parent)

        self.parent = parent
        self.record_id = record_id
        self.report_data = None
        self.loaded_pdf_path = None

        self.title("Generate Crane Inspection Presentation")
        self.geometry("650x620")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame,
            text="Buscar",
            command=self._load_backend_data
        ).pack(fill="x", pady=(0, 15), ipady=6)

        self.report_entry = self._readonly_field(frame, "REPORT NUMBER")
        self.vessel_entry = self._readonly_field(frame, "VESSEL")
        self.client_entry = self._readonly_field(frame, "CLIENT")
        self.port_entry = self._readonly_field(frame, "PORT")

        ttk.Separator(frame).pack(fill="x", pady=15)

        ttk.Button(
            frame,
            text="Cargar Reporte (.pdf)",
            command=self._load_pdf
        ).pack(fill="x", ipady=8)

        self.loaded_file_label = ttk.Label(
            frame,
            text="No file selected",
            foreground="gray"
        )
        self.loaded_file_label.pack(fill="x", pady=(8, 20))

        self.btn_final = ttk.Button(
            frame,
            text="Generar Informe Final",
            command=self._create_final_report,
            state="disabled"
        )
        self.btn_final.pack(fill="x", ipady=8)

    # =====================================================
    # READONLY FIELD
    # =====================================================

    def _readonly_field(self, parent, label):

        ttk.Label(parent, text=label).pack(anchor="w")

        entry = ttk.Entry(parent, state="readonly")
        entry.pack(fill="x", pady=5)

        return entry

    # =====================================================
    # LOAD BACKEND DATA (MISMA LÓGICA QUE TU POPUP ORIGINAL)
    # =====================================================

    def _load_backend_data(self):

        try:

            resp = api_client.get_crane_inspection_api(
                self.record_id
            )

            if not resp or not resp.get("success"):

                messagebox.showerror(
                    "Error",
                    resp.get("error", "No data found.")
                )
                return

            self.report_data = resp.get("data")

            if not self.report_data:

                messagebox.showerror(
                    "Error",
                    "Empty backend response."
                )
                return

            self._set_entry(
                self.report_entry,
                self.report_data.get("report_number")
            )

            self._set_entry(
                self.vessel_entry,
                self.report_data.get("vessel")
            )

            self._set_entry(
                self.client_entry,
                self.report_data.get("client")
            )

            self._set_entry(
                self.port_entry,
                f"{self.report_data.get('port') or ''} – {self.report_data.get('country') or ''}"
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # LOAD PDF
    # =====================================================

    def _load_pdf(self):

        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not file_path:
            return

        if not file_path.lower().endswith(".pdf"):

            messagebox.showerror(
                "Error",
                "Solo se permiten archivos PDF."
            )
            return

        self.loaded_pdf_path = file_path

        self.loaded_file_label.config(
            text=file_path,
            foreground="black"
        )

        self.btn_final.config(state="normal")

    # =====================================================
    # CREATE FINAL REPORT
    # =====================================================

    def _create_final_report(self):

        if not self.loaded_pdf_path:

            messagebox.showwarning(
                "Warning",
                "Debe cargar primero un archivo PDF."
            )
            return

        try:

            presentation_pdf = api_client.generate_crane_inspection_presentation_api(
                self.record_id
            )

            if not presentation_pdf or not os.path.exists(presentation_pdf):

                messagebox.showerror(
                    "Error",
                    "No se pudo generar la presentación."
                )
                return

            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Final_Crane_Inspection_{self.record_id}.pdf"
            )

            if not save_path:
                return

            writer = PdfWriter()

            presentation_reader = PdfReader(presentation_pdf)

            for page in presentation_reader.pages:
                writer.add_page(page)

            loaded_reader = PdfReader(self.loaded_pdf_path)

            for page in loaded_reader.pages:
                writer.add_page(page)

            with open(save_path, "wb") as f:
                writer.write(f)

            messagebox.showinfo(
                "Success",
                "Informe final creado correctamente."
            )

            os.startfile(save_path)

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )