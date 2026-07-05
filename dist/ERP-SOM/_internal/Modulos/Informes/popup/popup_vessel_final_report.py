import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    get_vessel_presentation_data_api,
    generate_vessel_presentation_pdf_api,
    generate_vessel_unified_pdf_api
)


class PopupVesselFinalReport(tk.Toplevel):

    def __init__(self, parent, report_id):
        super().__init__(parent)

        self.parent = parent
        self.report_id = report_id
        self.report_data = None

        self.title("Generate Vessel Presentation")
        self.geometry("450x470")
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
        ).pack(fill="x", pady=(0, 15))

        ttk.Label(frame, text="CERT No.").pack(anchor="w")
        self.cert_entry = ttk.Entry(frame, state="readonly")
        self.cert_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="VESSEL").pack(anchor="w")
        self.vessel_entry = ttk.Entry(frame, state="readonly")
        self.vessel_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="TO").pack(anchor="w")
        self.to_entry = ttk.Entry(frame, state="readonly")
        self.to_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="PLACE").pack(anchor="w")
        self.place_entry = ttk.Entry(frame, state="readonly")
        self.place_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="DATE").pack(anchor="w")
        self.date_entry = ttk.Entry(frame, state="readonly")
        self.date_entry.pack(fill="x", pady=5)

        ttk.Button(
            frame,
            text="Generate Presentation",
            command=self._generate_presentation
        ).pack(fill="x", pady=(20, 5))

        ttk.Button(
            frame,
            text="Generate Unified Report",
            command=self._generate_unified
        ).pack(fill="x")

    # =====================================================
    # LOAD DATA
    # =====================================================
    def _load_backend_data(self):

        try:
            resp = get_vessel_presentation_data_api(self.report_id)

            if not resp or not resp.get("success"):
                self._clear_fields()
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Backend error.")
                    if isinstance(resp, dict)
                    else "Invalid backend response."
                )
                return

            self.report_data = resp.get("data")

            if not self.report_data:
                self._clear_fields()
                messagebox.showerror("Error", "No data received.")
                return

            self._set_entry(self.cert_entry, self.report_data.get("cert_no"))
            self._set_entry(self.vessel_entry, self.report_data.get("vessel_name"))
            self._set_entry(self.to_entry, self.report_data.get("requested_by"))
            self._set_entry(self.place_entry, "PUERTO CALDERA – COSTA RICA")
            self._set_entry(self.date_entry, self.report_data.get("sampling_start_time"))

        except Exception as e:
            self._clear_fields()
            messagebox.showerror("Error", str(e))

    # =====================================================
    # UTILITIES
    # =====================================================
    def _set_entry(self, entry, value):
        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    def _clear_fields(self):
        for entry in [
            self.cert_entry,
            self.vessel_entry,
            self.to_entry,
            self.place_entry,
            self.date_entry
        ]:
            entry.config(state="normal")
            entry.delete(0, "end")
            entry.config(state="readonly")

    # =====================================================
    # GENERATE PRESENTATION (API VERSION)
    # =====================================================
    def _generate_presentation(self):

        if not self.report_data:
            messagebox.showwarning("Warning", "Debe presionar Buscar primero.")
            return

        try:
            resp = generate_vessel_presentation_pdf_api(self.report_id)

            if not resp or isinstance(resp, dict):
                messagebox.showerror("Error", resp.get("error", "Unknown error"))
                return

            if resp.status_code != 200:
                messagebox.showerror("Error", f"HTTP {resp.status_code}")
                return

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Presentation_{self.report_data.get('cert_no')}.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo("Success", "Presentation generated successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # GENERATE UNIFIED REPORT (BACKEND VERSION)
    # =====================================================
    def _generate_unified(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        try:
            resp = generate_vessel_unified_pdf_api(self.report_id)

            if not resp or isinstance(resp, dict):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Unknown error")
                )
                return

            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    messagebox.showerror(
                        "Error",
                        error_data.get("detail", "Server error")
                    )
                except Exception:
                    messagebox.showerror(
                        "Error",
                        f"HTTP {resp.status_code}"
                    )
                return

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Unified_{self.report_data.get('cert_no')}.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo(
                "Success",
                "Unified report generated successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))
