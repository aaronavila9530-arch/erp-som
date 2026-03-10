import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    get_vessel_truck_supervision_by_id_api,
    generate_truck_presentation_pdf_api,
    generate_truck_unified_pdf_api
)


class PopupTruckSupervisionFinalReport(tk.Toplevel):

    def __init__(self, parent, report_id):
        super().__init__(parent)

        self.parent = parent
        self.report_id = report_id
        self.report_data = None

        self.title("Generate Truck Supervision Presentation")
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

        self.cert_entry = self._readonly_field(frame, "CERT No.")
        self.vessel_entry = self._readonly_field(frame, "VESSEL")
        self.customer_entry = self._readonly_field(frame, "CUSTOMER")
        self.place_entry = self._readonly_field(frame, "PLACE")
        self.date_entry = self._readonly_field(frame, "DATE")

        ttk.Button(
            frame,
            text="Generate Presentation",
            command=self._generate_presentation
        ).pack(fill="x", pady=(20, 5))

        ttk.Button(
            frame,
            text="Generate Unified Report (With Attachments)",
            command=self._generate_unified
        ).pack(fill="x")

    # =====================================================
    # READONLY FIELD
    # =====================================================
    def _readonly_field(self, parent, label):

        ttk.Label(parent, text=label).pack(anchor="w")
        entry = ttk.Entry(parent, state="readonly")
        entry.pack(fill="x", pady=5)
        return entry

    # =====================================================
    # LOAD DATA FROM BACKEND
    # =====================================================
    def _load_backend_data(self):

        try:
            resp = get_vessel_truck_supervision_by_id_api(self.report_id)

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

            self._set_entry(self.cert_entry, self.report_data.get("cert_no"))
            self._set_entry(self.vessel_entry, self.report_data.get("vessel_name"))
            self._set_entry(self.customer_entry, self.report_data.get("customer"))

            place = f"{self.report_data.get('port') or ''} – {self.report_data.get('country') or ''}"
            self._set_entry(self.place_entry, place)

            self._set_entry(self.date_entry, self.report_data.get("report_date"))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # SET ENTRY VALUE SAFELY
    # =====================================================
    def _set_entry(self, entry, value):
        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # GENERATE PRESENTATION
    # =====================================================
    def _generate_presentation(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        try:
            resp = generate_truck_presentation_pdf_api(self.report_id)

            # Si API devolvió error dict
            if isinstance(resp, dict):
                messagebox.showerror("Error", resp.get("error", "Unknown error"))
                return

            if resp.status_code != 200:
                try:
                    error_json = resp.json()
                    messagebox.showerror(
                        "Error",
                        error_json.get("detail", f"HTTP {resp.status_code}")
                    )
                except Exception:
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

            messagebox.showinfo(
                "Success",
                "Presentation generated successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # GENERATE UNIFIED REPORT
    # =====================================================
    def _generate_unified(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        try:
            resp = generate_truck_unified_pdf_api(self.report_id)

            if isinstance(resp, dict):
                messagebox.showerror("Error", resp.get("error", "Unknown error"))
                return

            if resp.status_code != 200:
                try:
                    error_json = resp.json()
                    messagebox.showerror(
                        "Error",
                        error_json.get("detail", f"HTTP {resp.status_code}")
                    )
                except Exception:
                    messagebox.showerror("Error", f"HTTP {resp.status_code}")
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
