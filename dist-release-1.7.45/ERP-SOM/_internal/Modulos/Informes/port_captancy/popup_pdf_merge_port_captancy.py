import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader

import api_client


class PopupPDFMergePortCaptancy(tk.Toplevel):

    PRESENTATION_OPTIONS = [
        "Port Captancy – Aceros",
        "Port Captancy – Granos"
    ]

    def __init__(self, parent, record_id: int):
        super().__init__(parent)

        self.parent = parent
        self.record_id = record_id

        self.report_data = None
        self.pdf_files = []

        self.title("Generate Port Captancy Presentation")
        self.geometry("700x860")
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

        ttk.Label(
            frame,
            text="PRESENTATION TYPE"
        ).pack(anchor="w")

        self.presentation_type_var = tk.StringVar()

        self.presentation_type_combo = ttk.Combobox(
            frame,
            textvariable=self.presentation_type_var,
            values=self.PRESENTATION_OPTIONS,
            state="readonly"
        )

        self.presentation_type_combo.pack(fill="x", pady=5)

        self.presentation_type_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._refresh_generate_button()
        )

        ttk.Separator(frame).pack(fill="x", pady=15)

        ttk.Label(
            frame,
            text="PDF Files",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            height=14
        )

        self.listbox.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview
        )

        scrollbar.pack(side="right", fill="y")

        self.listbox.configure(
            yscrollcommand=scrollbar.set
        )

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=15)

        ttk.Button(
            btn_frame,
            text="➕ Agregar PDF",
            command=self._add_pdf
        ).pack(fill="x", ipady=6)

        ttk.Button(
            btn_frame,
            text="❌ Quitar seleccionado",
            command=self._remove_selected
        ).pack(fill="x", pady=5, ipady=6)

        ttk.Separator(frame).pack(fill="x", pady=15)

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
    # SET ENTRY
    # =====================================================

    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # LOAD BACKEND DATA
    # =====================================================

    def _load_backend_data(self):

        try:

            resp = api_client.get_port_captancy_report_by_id_api(
                self.record_id
            )

            if not resp:
                messagebox.showerror("Error", "No data found.")
                return

            if resp.get("success"):
                self.report_data = resp.get("data")
            else:
                self.report_data = resp

            if not self.report_data:
                messagebox.showerror("Error", "Empty backend response.")
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
                self.report_data.get("requested_by")
            )

            self._set_entry(
                self.port_entry,
                f"{self.report_data.get('port')} – {self.report_data.get('country')}"
            )

            self._refresh_generate_button()

        except Exception as e:

            messagebox.showerror("Error", str(e))

    # =====================================================
    # ADD PDF
    # =====================================================

    def _add_pdf(self):

        files = filedialog.askopenfilenames(
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not files:
            return

        for file_path in files:

            if not os.path.exists(file_path):
                continue

            try:
                PdfReader(file_path)
            except Exception:
                messagebox.showerror(
                    "Error",
                    f"El archivo no es un PDF válido:\n{file_path}"
                )
                return

            self.pdf_files.append(file_path)
            self.listbox.insert("end", os.path.basename(file_path))

        self._refresh_generate_button()

    # =====================================================
    # REMOVE SELECTED
    # =====================================================

    def _remove_selected(self):

        selection = self.listbox.curselection()

        if not selection:
            return

        index = selection[0]

        self.listbox.delete(index)
        self.pdf_files.pop(index)

        self._refresh_generate_button()

    # =====================================================
    # ENABLE / DISABLE BUTTON
    # =====================================================

    def _refresh_generate_button(self):

        has_backend = self.report_data is not None
        has_type = bool(self.presentation_type_var.get())
        has_pdfs = len(self.pdf_files) > 0

        if has_backend and has_type and has_pdfs:
            self.btn_final.config(state="normal")
        else:
            self.btn_final.config(state="disabled")

    # =====================================================
    # CREATE FINAL REPORT
    # =====================================================

    def _create_final_report(self):

        try:

            presentation_pdf = api_client.generate_port_captancy_presentation_api(
                self.record_id
            )

            if not os.path.exists(presentation_pdf):

                messagebox.showerror(
                    "Error",
                    "No se pudo generar la presentación."
                )

                return

            save_path = filedialog.asksaveasfilename(
                title="Guardar Informe Final",
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Final_Port_Captancy_{self.record_id}.pdf"
            )

            if not save_path:
                return

            writer = PdfWriter()

            presentation_reader = PdfReader(presentation_pdf)

            for page in presentation_reader.pages:
                writer.add_page(page)

            for pdf_path in self.pdf_files:

                reader = PdfReader(pdf_path)

                for page in reader.pages:
                    writer.add_page(page)

            with open(save_path, "wb") as f:
                writer.write(f)

            writer.close()

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
