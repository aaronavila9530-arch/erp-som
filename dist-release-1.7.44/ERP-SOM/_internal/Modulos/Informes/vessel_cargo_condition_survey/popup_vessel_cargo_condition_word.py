import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader

import api_client


class PopupVesselCargoConditionWord(tk.Toplevel):

    def __init__(self, parent, record_id: int):
        super().__init__(parent)

        self.parent = parent
        self.record_id = record_id
        self.report_data = None
        self.loaded_pdf_path = None

        self.title("Generate Cargo Condition Report")
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
        self.client_entry = self._readonly_field(frame, "REQUESTED BY")
        self.port_entry = self._readonly_field(frame, "PORT")
        self.date_entry = self._readonly_field(frame, "SERVICE START DATE")
        self.status_entry = self._readonly_field(frame, "STATUS")

        ttk.Separator(frame).pack(fill="x", pady=15)

        # -------------------------------------------------
        # 1️⃣ CARGAR REPORTE (PDF)
        # -------------------------------------------------
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

        # -------------------------------------------------
        # 2️⃣ CREAR INFORME FINAL
        # -------------------------------------------------
        self.btn_final = ttk.Button(
            frame,
            text="Crear Informe Final",
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
    # LOAD BACKEND DATA
    # =====================================================
    def _load_backend_data(self):

        try:
            resp = api_client.get_vessel_cargo_condition_by_id_api(
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
                messagebox.showerror("Error", "Empty backend response.")
                return

            self._set_entry(self.report_entry, self.report_data.get("report_number"))
            self._set_entry(self.vessel_entry, self.report_data.get("vessel"))
            self._set_entry(self.client_entry, self.report_data.get("requested_by"))
            self._set_entry(
                self.port_entry,
                f"{self.report_data.get('port') or ''} – {self.report_data.get('country') or ''}"
            )
            self._set_entry(self.date_entry, self.report_data.get("service_start_date"))
            self._set_entry(self.status_entry, self.report_data.get("status"))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # STEP 1 - LOAD PDF
    # =====================================================
    def _load_pdf(self):

        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not file_path:
            return

        if not file_path.lower().endswith(".pdf"):
            messagebox.showerror("Error", "Solo se permiten archivos PDF.")
            return

        self.loaded_pdf_path = file_path
        self.loaded_file_label.config(
            text=file_path,
            foreground="black"
        )

        self.btn_final.config(state="normal")

    # =====================================================
    # STEP 2 - CREATE FINAL REPORT
    # =====================================================
    def _create_final_report(self):

        if not self.loaded_pdf_path:
            messagebox.showwarning(
                "Warning",
                "Debe cargar primero un archivo PDF."
            )
            return

        try:
            # -------------------------------------------------
            # 1️⃣ GENERATE PRESENTATION PDF FROM API
            # -------------------------------------------------
            resp = api_client.download_vessel_cargo_condition_presentation_pdf(
                self.record_id
            )

            if not resp.get("success"):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Error generando presentación.")
                )
                return

            presentation_bytes = resp["content"]

            # -------------------------------------------------
            # 2️⃣ SAVE TEMP PRESENTATION
            # -------------------------------------------------
            temp_presentation_path = os.path.join(
                os.getcwd(),
                f"temp_presentation_{self.record_id}.pdf"
            )

            with open(temp_presentation_path, "wb") as f:
                f.write(presentation_bytes)

            # -------------------------------------------------
            # 3️⃣ MERGE (PRESENTATION FIRST)
            # -------------------------------------------------
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Final_Cargo_Condition_{self.record_id}.pdf"
            )

            if not save_path:
                return

            writer = PdfWriter()

            # Presentation FIRST
            presentation_reader = PdfReader(temp_presentation_path)
            for page in presentation_reader.pages:
                writer.add_page(page)

            # Then loaded report
            loaded_reader = PdfReader(self.loaded_pdf_path)
            for page in loaded_reader.pages:
                writer.add_page(page)

            with open(save_path, "wb") as f:
                writer.write(f)

            os.remove(temp_presentation_path)

            messagebox.showinfo(
                "Success",
                "Informe final creado correctamente."
            )

            os.startfile(save_path)

        except Exception as e:
            messagebox.showerror("Error", str(e))