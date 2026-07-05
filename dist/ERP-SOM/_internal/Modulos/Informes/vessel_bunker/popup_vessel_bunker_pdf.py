import os
import tempfile
import tkinter as tk
from io import BytesIO
from tkinter import ttk, messagebox, filedialog

from pypdf import PdfReader, PdfWriter

from api_client import (
    get_vessel_bunker_report_api,
    generate_vessel_bunker_pdf_api,
    get_vessel_bunker_presentation_pdf
)


class PopupVesselBunkerPDF(tk.Toplevel):

    MODE_ONLY_BUNKER = "ONLY_BUNKER"
    MODE_CONDITION = "CONDITION"

    def __init__(self, parent, report_id: int):
        super().__init__(parent)

        self.parent = parent
        self.report_id = report_id
        self.report_data = None

        self.mode_var = tk.StringVar(value=self.MODE_ONLY_BUNKER)
        self.condition_pdf_path = None

        self.title("Generate Vessel Bunker Report")
        self.geometry("620x650")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        self._on_mode_change()

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
        ).pack(fill="x", pady=(0, 15))

        self.cert_entry = self._readonly_field(frame, "CERT NO.")
        self.vessel_entry = self._readonly_field(frame, "VESSEL")
        self.client_entry = self._readonly_field(frame, "CLIENT")
        self.port_entry = self._readonly_field(frame, "PORT")
        self.date_entry = self._readonly_field(frame, "REPORT DATE")

        # -------------------------------------------------
        # MODE SELECTOR
        # -------------------------------------------------
        mode_box = ttk.LabelFrame(frame, text="Selector", padding=10)
        mode_box.pack(fill="x", pady=(15, 10))

        ttk.Radiobutton(
            mode_box,
            text="Only bunker",
            value=self.MODE_ONLY_BUNKER,
            variable=self.mode_var,
            command=self._on_mode_change
        ).pack(anchor="w")

        ttk.Radiobutton(
            mode_box,
            text="Condition",
            value=self.MODE_CONDITION,
            variable=self.mode_var,
            command=self._on_mode_change
        ).pack(anchor="w")

        # -------------------------------------------------
        # ONLY BUNKER BUTTON
        # -------------------------------------------------
        self.btn_only_bunker = ttk.Button(
            frame,
            text="Generate Final Report (Bunker Only)",
            command=self._generate_bunker_only_pdf
        )
        self.btn_only_bunker.pack(fill="x", pady=(10, 5))

        # -------------------------------------------------
        # CONDITION AREA
        # -------------------------------------------------
        self.condition_frame = ttk.LabelFrame(frame, text="Condition", padding=15)
        self.condition_frame.pack(fill="x", pady=(10, 5))

        self.btn_browse_condition = ttk.Button(
            self.condition_frame,
            text="Buscar fotos del condition (PDF)",
            command=self._browse_condition_pdf
        )
        self.btn_browse_condition.pack(fill="x", pady=(0, 12), ipady=8)

        self.condition_path_var = tk.StringVar(value="No file selected.")
        ttk.Label(
            self.condition_frame,
            textvariable=self.condition_path_var,
            wraplength=460
        ).pack(anchor="w", pady=(0, 15))

        self.btn_bunker_and_condition = ttk.Button(
            self.condition_frame,
            text="Crear Bunker and Condition",
            command=self._generate_bunker_and_condition_pdf,
            state="disabled"
        )
        self.btn_bunker_and_condition.pack(fill="x", ipady=8)

    # =====================================================
    # READONLY FIELD
    # =====================================================
    def _readonly_field(self, parent, label):

        ttk.Label(parent, text=label).pack(anchor="w")
        entry = ttk.Entry(parent, state="readonly")
        entry.pack(fill="x", pady=5)
        return entry

    # =====================================================
    # MODE CHANGE
    # =====================================================
    def _on_mode_change(self):

        mode = self.mode_var.get()

        if mode == self.MODE_ONLY_BUNKER:
            try:
                self.condition_frame.pack_forget()
            except Exception:
                pass

            self.btn_only_bunker.configure(state="normal")
            self.btn_only_bunker.pack(fill="x", pady=(10, 5))

        else:
            try:
                self.btn_only_bunker.pack_forget()
            except Exception:
                pass

            self.condition_frame.pack(fill="x", pady=(10, 5))
            self.btn_bunker_and_condition.configure(
                state="normal" if self.condition_pdf_path else "disabled"
            )

    # =====================================================
    # LOAD DATA FROM BACKEND
    # =====================================================
    def _load_backend_data(self):

        try:
            resp = get_vessel_bunker_report_api(self.report_id)

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

            self._set_entry(self.cert_entry, self.report_data.get("bunker_cert_no"))
            self._set_entry(self.vessel_entry, self.report_data.get("ship_name"))
            self._set_entry(self.client_entry, self.report_data.get("client"))
            self._set_entry(
                self.port_entry,
                f"{self.report_data.get('port') or ''} – {self.report_data.get('country') or ''}"
            )
            self._set_entry(self.date_entry, self.report_data.get("report_date"))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # SAFE SET ENTRY
    # =====================================================
    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # BROWSE CONDITION PDF
    # =====================================================
    def _browse_condition_pdf(self):

        path = filedialog.askopenfilename(
            title="Select Condition PDF",
            filetypes=[("PDF File", "*.pdf")]
        )

        if not path:
            return

        if not os.path.exists(path):
            messagebox.showerror("Error", "Selected file not found.")
            return

        self.condition_pdf_path = path
        self.condition_path_var.set(path)

        self.btn_bunker_and_condition.configure(state="normal")

    # =====================================================
    # MERGE PDFs
    # =====================================================
    def _merge_pdfs_to_bytes(self, parts):

        writer = PdfWriter()

        for part in parts:
            if part is None:
                continue

            if isinstance(part, (bytes, bytearray)):
                reader = PdfReader(BytesIO(part))
            elif isinstance(part, str):
                if not os.path.exists(part):
                    raise FileNotFoundError(f"PDF not found: {part}")
                reader = PdfReader(part)
            else:
                raise ValueError("Invalid PDF part type")

            for page in reader.pages:
                writer.add_page(page)

        out = BytesIO()
        writer.write(out)
        return out.getvalue()

    # =====================================================
    # FETCH PRESENTATION PDF (bytes)
    # =====================================================
    def _fetch_presentation_pdf_bytes(self):

        pres = get_vessel_bunker_presentation_pdf(self.report_id)

        if not pres or not pres.get("success"):
            raise RuntimeError(pres.get("detail") or pres.get("error") or "Presentation PDF failed")

        content = pres.get("content")
        if not content:
            raise RuntimeError("Presentation PDF empty content")

        return content

    # =====================================================
    # FETCH FINAL BUNKER PDF (bytes)
    # =====================================================
    def _fetch_final_bunker_pdf_bytes(self):

        final = generate_vessel_bunker_pdf_api(self.report_id)

        if not final or not final.get("success"):
            raise RuntimeError(final.get("detail") or final.get("error") or "Final bunker PDF failed")

        content = final.get("content")
        if not content:
            raise RuntimeError("Final bunker PDF empty content")

        return content

    # =====================================================
    # ONLY BUNKER => SAVE
    # =====================================================
    def _generate_bunker_only_pdf(self):

        if not self.report_data:
            messagebox.showwarning("Warning", "Debe presionar Buscar primero.")
            return

        try:
            pres_bytes = self._fetch_presentation_pdf_bytes()
            final_bytes = self._fetch_final_bunker_pdf_bytes()

            merged_bytes = self._merge_pdfs_to_bytes([pres_bytes, final_bytes])

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Vessel_Bunker_ONLY_{self.report_id}.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                f.write(merged_bytes)

            messagebox.showinfo("Success", "Bunker only PDF generated successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # BUNKER + CONDITION => SAVE
    # =====================================================
    def _generate_bunker_and_condition_pdf(self):

        if not self.report_data:
            messagebox.showwarning("Warning", "Debe presionar Buscar primero.")
            return

        if not self.condition_pdf_path:
            messagebox.showwarning("Warning", "Debe seleccionar el PDF de Condition primero.")
            return

        try:
            pres_bytes = self._fetch_presentation_pdf_bytes()
            final_bytes = self._fetch_final_bunker_pdf_bytes()

            merged_bytes = self._merge_pdfs_to_bytes([
                pres_bytes,
                final_bytes,
                self.condition_pdf_path
            ])

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Vessel_Bunker_Condition_{self.report_id}.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                f.write(merged_bytes)

            messagebox.showinfo("Success", "Bunker + Condition PDF generated successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))