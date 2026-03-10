import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

from api_client import (
    get_vessel_truck_supervision_by_id_api,
    update_vessel_truck_supervision_api
)


class PopupVesselTruckSupervisionReview(tk.Toplevel):

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, report_id: int):
        super().__init__(parent)

        self.parent = parent
        self.report_id = report_id
        self.report_data = None

        self.title("Review Vessel Truck Supervision")
        self.geometry("900x750")
        self.grab_set()

        self._build_ui()
        self._load_data()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        # ---------------- HEADER ----------------
        ttk.Label(
            container,
            text="Vessel Truck Supervision Review",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # ---------------- BASIC FIELDS ----------------
        form = ttk.Frame(container)
        form.pack(fill="x", pady=5)

        # Row 0
        ttk.Label(form, text="Cert No").grid(row=0, column=0, sticky="w")
        self.cert_no = ttk.Entry(form, width=25)
        self.cert_no.grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Customer").grid(row=0, column=2, sticky="w")
        self.customer = ttk.Entry(form, width=30)
        self.customer.grid(row=0, column=3, padx=5)

        # Row 1
        ttk.Label(form, text="Port").grid(row=1, column=0, sticky="w")
        self.port = ttk.Entry(form, width=25)
        self.port.grid(row=1, column=1, padx=5)

        ttk.Label(form, text="Country").grid(row=1, column=2, sticky="w")
        self.country = ttk.Entry(form, width=25)
        self.country.grid(row=1, column=3, padx=5)

        # Row 2
        ttk.Label(form, text="Report Date").grid(row=2, column=0, sticky="w")
        self.report_date = DateEntry(form, width=15, date_pattern="dd-mm-yyyy")
        self.report_date.grid(row=2, column=1, padx=5)

        # ---------------- VESSEL ----------------
        vessel_frame = ttk.LabelFrame(container, text="Vessel")
        vessel_frame.pack(fill="x", pady=10)

        self.vessel_name = ttk.Entry(vessel_frame, width=30)
        self.flag_port_registry = ttk.Entry(vessel_frame, width=30)
        self.grt = ttk.Entry(vessel_frame, width=20)
        self.nrt = ttk.Entry(vessel_frame, width=20)
        self.imo_no = ttk.Entry(vessel_frame, width=20)
        self.build_year = ttk.Entry(vessel_frame, width=20)

        labels = [
            ("Name", self.vessel_name),
            ("Flag / Registry", self.flag_port_registry),
            ("GRT", self.grt),
            ("NRT", self.nrt),
            ("IMO", self.imo_no),
            ("Build Year", self.build_year),
        ]

        for i, (text, widget) in enumerate(labels):
            ttk.Label(vessel_frame, text=text).grid(row=i, column=0, sticky="w")
            widget.grid(row=i, column=1, padx=5, pady=2)

        # ---------------- REPRESENTATIVES ----------------
        reps_frame = ttk.LabelFrame(container, text="Representatives")
        reps_frame.pack(fill="x", pady=10)

        ttk.Label(reps_frame, text="Captain").grid(row=0, column=0, sticky="w")
        self.captain = ttk.Entry(reps_frame, width=30)
        self.captain.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(reps_frame, text="Chief Officer").grid(row=1, column=0, sticky="w")
        self.chief_officer = ttk.Entry(reps_frame, width=30)
        self.chief_officer.grid(row=1, column=1, padx=5, pady=2)

        # ---------------- TIMES ----------------
        times_frame = ttk.LabelFrame(container, text="Times")
        times_frame.pack(fill="x", pady=10)

        ttk.Label(times_frame, text="Arrival Date").grid(row=0, column=0, sticky="w")
        self.arrival_date = DateEntry(times_frame, width=15, date_pattern="dd-mm-yyyy")
        self.arrival_date.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(times_frame, text="Inspection Date").grid(row=1, column=0, sticky="w")
        self.inspection_date = DateEntry(times_frame, width=15, date_pattern="dd-mm-yyyy")
        self.inspection_date.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(times_frame, text="Supervision Completed").grid(row=2, column=0, sticky="w")
        self.supervision_completed_date = DateEntry(times_frame, width=15, date_pattern="dd-mm-yyyy")
        self.supervision_completed_date.grid(row=2, column=1, padx=5, pady=2)


        # ---------------- TEXT SECTIONS ----------------
        self.process_text = self._create_text_section(container, "Process")
        self.findings_doc = self._create_text_section(container, "Findings Documental")
        self.findings_oper = self._create_text_section(container, "Findings Operational")
        self.incidents_text = self._create_text_section(container, "Incidents")
        self.conclusion_text = self._create_text_section(container, "Conclusion")

        # ---------------- ACTIONS ----------------
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=15)

        ttk.Button(
            actions,
            text="💾 Save Changes",
            command=self._update_report
        ).pack(side="right")

        ttk.Button(
            actions,
            text="Close",
            command=self.destroy
        ).pack(side="right", padx=10)

    # =========================================================
    # TEXT SECTION BUILDER
    # =========================================================
    def _create_text_section(self, parent, title):

        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill="both", expand=True, pady=5)

        txt = tk.Text(frame, height=4, wrap="word")
        txt.pack(fill="both", expand=True, padx=5, pady=5)

        return txt

    # =========================================================
    # LOAD DATA (GET)
    # =========================================================
    def _load_data(self):

        try:
            resp = get_vessel_truck_supervision_by_id_api(self.report_id)

            if not resp.get("success"):
                messagebox.showerror("Error", "Report not found")
                self.destroy()
                return

            data = resp.get("data", {})
            self.report_data = data

            self.cert_no.delete(0, "end")
            self.cert_no.insert(0, str(data.get("cert_no") or ""))

            self.customer.delete(0, "end")
            self.customer.insert(0, str(data.get("customer") or ""))

            self.port.delete(0, "end")
            self.port.insert(0, str(data.get("port") or ""))

            self.country.delete(0, "end")
            self.country.insert(0, str(data.get("country") or ""))

            if data.get("report_date"):
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(
                        str(data.get("report_date")),
                        "%Y-%m-%d"
                    ).date()
                    self.report_date.set_date(parsed_date)
                except Exception:
                    pass

            # ---------------- REPRESENTATIVES ----------------
            self.captain.delete(0, "end")
            self.captain.insert(0, str(data.get("captain") or ""))

            self.chief_officer.delete(0, "end")
            self.chief_officer.insert(0, str(data.get("chief_officer") or ""))

            # ---------------- TIMES ----------------
            from datetime import datetime

            if data.get("arrival_date"):
                try:
                    parsed = datetime.strptime(
                        str(data.get("arrival_date")),
                        "%Y-%m-%d"
                    ).date()
                    self.arrival_date.set_date(parsed)
                except:
                    pass

            if data.get("inspection_date"):
                try:
                    parsed = datetime.strptime(
                        str(data.get("inspection_date")),
                        "%Y-%m-%d"
                    ).date()
                    self.inspection_date.set_date(parsed)
                except:
                    pass

            if data.get("supervision_completed_date"):
                try:
                    parsed = datetime.strptime(
                        str(data.get("supervision_completed_date")),
                        "%Y-%m-%d"
                    ).date()
                    self.supervision_completed_date.set_date(parsed)
                except:
                    pass

            self.vessel_name.insert(0, data.get("vessel_name", ""))
            self.flag_port_registry.insert(0, data.get("flag_port_registry", ""))
            self.grt.insert(0, data.get("grt", ""))
            self.nrt.insert(0, data.get("nrt", ""))
            self.imo_no.insert(0, data.get("imo_no", ""))
            self.build_year.insert(0, data.get("build_year", ""))

            self.process_text.insert("1.0", data.get("process_text", ""))
            self.findings_doc.insert("1.0", data.get("findings_documental_text", ""))
            self.findings_oper.insert("1.0", data.get("findings_operational_text", ""))
            self.incidents_text.insert("1.0", data.get("incidents_text", ""))
            self.conclusion_text.insert("1.0", data.get("conclusion_text", ""))

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.destroy()

    # =========================================================
    # UPDATE (PUT)
    # =========================================================
    def _update_report(self):

        data = {
            "cert_no": self.cert_no.get(),
            "customer": self.customer.get(),
            "port": self.port.get(),
            "country": self.country.get(),
            "report_date": self.report_date.get(),

            "vessel_name": self.vessel_name.get(),
            "flag_port_registry": self.flag_port_registry.get(),
            "grt": self.grt.get(),
            "nrt": self.nrt.get(),
            "imo_no": self.imo_no.get(),
            "build_year": self.build_year.get(),

            "captain": self.captain.get(),
            "chief_officer": self.chief_officer.get(),

            "arrival_date": self.arrival_date.get(),
            "inspection_date": self.inspection_date.get(),
            "supervision_completed_date": self.supervision_completed_date.get(),

            "process_text": self.process_text.get("1.0", "end").strip(),
            "findings_documental_text": self.findings_doc.get("1.0", "end").strip(),
            "findings_operational_text": self.findings_oper.get("1.0", "end").strip(),
            "incidents_text": self.incidents_text.get("1.0", "end").strip(),
            "conclusion_text": self.conclusion_text.get("1.0", "end").strip(),
        }

        try:
            update_vessel_truck_supervision_api(self.report_id, data)

            messagebox.showinfo("Success", "Report updated successfully.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
