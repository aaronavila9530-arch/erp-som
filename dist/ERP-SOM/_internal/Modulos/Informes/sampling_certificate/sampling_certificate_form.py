import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.informes_home_ui import InformesHomeUI
from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.date_utils import to_db_date, to_long_english_date

import api_client


class SamplingCertificateForm(ttk.Frame):

    MAX_HOLDS = 10

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, record=None, on_back=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.record = record
        self.on_back = on_back

        self.vars = {}
        self.holds = []

        self.pack(fill="both", expand=True)

        self._build_scrollable()
        self._build_ui()

        # cargar registro si viene desde tabla
        if self.record:
            self.load_record(self.record["id"])


    # =========================================================
    # SCROLLABLE FRAME
    # =========================================================
    def _build_scrollable(self):

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        )

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        frame = ttk.Frame(self.scroll_frame, padding=20)
        frame.pack(fill="both", expand=True)

        # =====================================================
        # FORM TITLE
        # =====================================================

        ttk.Label(
            frame,
            text="Sampling Certificate Form",
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="center", pady=(0,20))



        # =====================================================
        # TOP BAR
        # =====================================================

        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0,20))

        left = ttk.Frame(top)
        left.pack(side="left", fill="x", expand=True)

        ttk.Button(
            left,
            text="HOME",
            command=self._go_home
        ).pack(side="left")

        ttk.Button(
            left,
            text="SELECT REPORT",
            command=self._open_report_selector
        ).pack(side="left", padx=10)

        right = ttk.Frame(top)
        right.pack(side="right")

        self.btn_send = ttk.Button(
            right,
            text="Enviar a Revisión",
            command=self._send_review
        )

        self.btn_send.pack(side="left", padx=4)

        self.btn_edit = ttk.Button(
            right,
            text="Editar",
            command=self._enable_edit_mode
        )

        self.btn_save_changes = ttk.Button(
            right,
            text="Guardar Cambios",
            command=self._save_changes
        )

        # =====================================================
        # HEADER
        # =====================================================

        header = ttk.LabelFrame(frame, text="Report Header")
        header.pack(fill="x", pady=10)

        self.vars["report_no"] = tk.StringVar()
        self.vars["port"] = tk.StringVar()
        self.vars["country"] = tk.StringVar()
        self.vars["customer"] = tk.StringVar()

        self._field(header,"Report No","report_no",0)
        self._field(header,"Port","port",1)
        self._field(header,"Country","country",2)
        self._field(header,"Customer","customer",3)

        # =====================================================
        # CERTIFICATE DATA
        # =====================================================

        cert = ttk.LabelFrame(frame, text="Sampling Certificate")
        cert.pack(fill="x", pady=10)

        self.vars["certificate_no"] = tk.StringVar()
        self.vars["vessel"] = tk.StringVar()
        self.vars["place"] = tk.StringVar()
        self.vars["cargo"] = tk.StringVar()

        ttk.Label(cert,text="Certificate No").grid(row=0,column=0,sticky="w")
        ttk.Entry(cert,textvariable=self.vars["certificate_no"],width=25).grid(row=0,column=1)

        ttk.Label(cert,text="Vessel").grid(row=1,column=0,sticky="w")
        ttk.Entry(cert,textvariable=self.vars["vessel"],width=50).grid(row=1,column=1)

        ttk.Label(cert,text="Date").grid(row=2,column=0,sticky="w")

        self.date_var = tk.StringVar()

        self.date_entry = DateEntry(
            cert,
            width=18,
            textvariable=self.date_var,
            date_pattern="yyyy-mm-dd"
        )

        self.date_entry.grid(row=2,column=1,sticky="w")

        # LONG DATE
        self.date_entry.bind(
            "<<DateEntrySelected>>",
            self._set_long_date
        )

        self.date_entry.bind(
            "<FocusOut>",
            self._set_long_date
        )

        self.date_entry.grid(row=2,column=1,sticky="w")

        ttk.Label(cert,text="Place").grid(row=3,column=0,sticky="w")
        ttk.Entry(cert,textvariable=self.vars["place"],width=50).grid(row=3,column=1)

        ttk.Label(cert,text="Cargo").grid(row=4,column=0,sticky="w")
        ttk.Entry(cert,textvariable=self.vars["cargo"],width=50).grid(row=4,column=1)

        # =====================================================
        # HOLDS INSPECTED
        # =====================================================

        holds_info = ttk.LabelFrame(frame, text="Holds Inspected")
        holds_info.pack(fill="x", pady=10)

        self.vars["holds_inspected"] = tk.StringVar()

        ttk.Label(
            holds_info,
            text="Holds:"
        ).grid(row=0, column=0, sticky="w")

        ttk.Entry(
            holds_info,
            textvariable=self.vars["holds_inspected"],
            width=50
        ).grid(row=0, column=1, sticky="w")


        # =====================================================
        # HOLDS AND SEAL NUMBERS
        # =====================================================

        holds_frame = ttk.LabelFrame(frame, text="Holds and Seal Numbers")
        holds_frame.pack(fill="x", pady=10)

        for i in range(self.MAX_HOLDS):

            seal_var = tk.StringVar()

            row = ttk.Frame(holds_frame)
            row.pack(fill="x", pady=2)

            ttk.Label(
                row,
                text=f"HOLD {i+1}",
                width=10
            ).pack(side="left")

            ttk.Entry(
                row,
                textvariable=seal_var,
                width=20
            ).pack(side="left")

            self.holds.append({
                "hold": i + 1,
                "seal": seal_var
            })


        # =====================================================
        # OBSERVATIONS
        # =====================================================

        obs = ttk.LabelFrame(frame, text="Observations")
        obs.pack(fill="both", pady=10)

        self.observations = tk.Text(
            obs,
            height=8,
            wrap="word"
        )
        self.observations.pack(fill="both", expand=True)

        # =====================================================
        # DATE + TIME (CLOSING)
        # =====================================================

        dt = ttk.LabelFrame(frame, text="Closing")
        dt.pack(fill="x", pady=10)

        ttk.Label(dt, text="Date").grid(row=0, column=0, sticky="w")

        self.closing_date_var = tk.StringVar()

        self.closing_date = DateEntry(
            dt,
            width=18,
            textvariable=self.closing_date_var,
            date_pattern="yyyy-mm-dd"
        )

        self.closing_date.grid(row=0, column=1, sticky="w")

        # LONG DATE
        self.closing_date.bind(
            "<<DateEntrySelected>>",
            self._set_long_closing_date
        )

        self.closing_date.bind(
            "<FocusOut>",
            self._set_long_closing_date
        )

        ttk.Label(dt, text="Time").grid(row=1, column=0, sticky="w")

        self.hour = tk.StringVar()
        self.minute = tk.StringVar()

        ttk.Entry(dt, textvariable=self.hour, width=5).grid(row=1, column=1, sticky="w")
        ttk.Entry(dt, textvariable=self.minute, width=5).grid(row=1, column=1, padx=40, sticky="w")


        # =====================================================
        # MASTER
        # =====================================================

        master = ttk.LabelFrame(frame, text="Signed By")
        master.pack(fill="x", pady=10)

        self.vars["master"] = tk.StringVar()

        ttk.Label(master,text="Master / Chief Officer").grid(row=0,column=0,sticky="w")

        ttk.Entry(
            master,
            textvariable=self.vars["master"],
            width=50
        ).grid(row=0,column=1)


    # =========================================================
    # FIELD HELPER
    # =========================================================
    def _field(self,parent,label,var,row):

        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w")

        ttk.Entry(
            parent,
            textvariable=self.vars[var],
            width=40
        ).grid(row=row,column=1,sticky="w")

    # =========================================================
    # SELECT REPORT
    # =========================================================
    def _open_report_selector(self):

        PopupServicioDraftSelector(
            self,
            self._fill_from_report
        )

    def _fill_from_report(self, values):

        if not values:
            return

        (
            num_informe,
            buque,
            cliente,
            continente,
            pais,
            puerto,
            operacion,
            fecha_inicio
        ) = values

        # REPORT HEADER
        self.vars["report_no"].set(num_informe)
        self.vars["port"].set(puerto)
        self.vars["country"].set(pais)
        self.vars["customer"].set(cliente)

        # CERTIFICATE HEADER
        self.vars["certificate_no"].set(num_informe)
        self.vars["vessel"].set(buque)
        self.vars["place"].set(f"{puerto}, {pais}")


    # =========================================================
    # HOME
    # =========================================================
    def _go_home(self):

        try:

            for child in self.parent.winfo_children():
                child.destroy()

            from Modulos.Informes.informes_home_ui import InformesHomeUI

            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Unable to return to Informes Home:\n{str(e)}"
            )

    # =========================================================
    # BUILD PAYLOAD
    # =========================================================

    def _build_payload(self):

        payload = {}

        for key, var in self.vars.items():

            value = var.get()

            payload[key] = value if value else None

        payload["holds_inspected"] = (
            self.vars["holds_inspected"].get() or None
        )

        # HOLDS

        holds_payload = []

        for h in self.holds:

            seal = h["seal"].get().strip()

            if seal:

                holds_payload.append({
                    "hold": h["hold"],
                    "seal": seal
                })

        payload["holds"] = holds_payload

        # DATE

        payload["date"] = to_db_date(self.date_entry.get()) or None

        payload["closing_date"] = to_db_date(self.closing_date.get()) or None

        # TIME

        h = self.hour.get().strip()
        m = self.minute.get().strip()

        payload["closing_time"] = f"{h}:{m}" if h and m else None

        # OBSERVATIONS

        try:
            payload["observations"] = self.observations.get("1.0","end").strip()
        except:
            payload["observations"] = None

        # MASTER

        payload["master"] = self.vars["master"].get() or None

        return payload


    # =========================================================
    # SUBMIT
    # =========================================================
    def _submit(self):

        payload = self._build_payload()

        try:

            if self.record:

                api_client.update_sampling_certificate_api(
                    self.record["id"],
                    payload
                )

                messagebox.showinfo("Success","Changes saved")

            else:

                api_client.create_sampling_certificate_api(payload)

                messagebox.showinfo("Success","Sent to review")

        except Exception as e:

            messagebox.showerror("Error",str(e))


    def set_edit_mode(self, record_id):

        self.record_id = record_id
        self.edit_mode = True

        self.btn_send.pack_forget()
        self.btn_edit.pack(side="left", padx=4)
        self.btn_save_changes.pack(side="left", padx=4)

    def _enable_edit_mode(self):
        self.btn_save_changes.config(state="normal")


    # =========================================================
    # SEND REVIEW / UPDATE
    # =========================================================
    def _send_review(self):

        try:

            payload = self._build_payload()

            # NUEVO REGISTRO → POST
            if True:

                result = api_client.create_sampling_certificate_api(payload)

                self.record_id = result.get("id")

                messagebox.showinfo(
                    "ERP-SOM",
                    f"Report submitted for review.\n\nID: {self.record_id}"
                )

            # EXISTENTE → PUT
            elif False:

                api_client.update_sampling_certificate_api(
                    self.record_id,
                    payload
                )

                messagebox.showinfo(
                    "ERP-SOM",
                    "Changes saved successfully."
                )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error sending report:\n{str(e)}"
            )



    def _save_changes(self):

        try:

            payload = self._build_payload()

            api_client.update_sampling_certificate_api(
                self.record_id,
                payload
            )

            messagebox.showinfo(
                "ERP-SOM",
                "Changes saved successfully."
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error saving changes:\n{str(e)}"
            )


    # =========================================================
    # DATE LONG FORMAT
    # =========================================================

    def _set_long_date(self, event=None):

        try:

            d = self.date_entry.get_date()

            long_date = to_long_english_date(d)

            self.date_var.set(long_date)

        except Exception:
            pass


    def _set_long_closing_date(self, event=None):

        try:

            d = self.closing_date.get_date()

            long_date = to_long_english_date(d)

            self.closing_date_var.set(long_date)

        except Exception:
            pass


    # =========================================================
    # EDIT MODE
    # =========================================================

    def set_edit_mode(self, record_id):

        self.record_id = record_id
        self.edit_mode = True

        self.btn_send.pack_forget()
        self.btn_edit.pack(side="left", padx=4)
        self.btn_save_changes.pack(side="left", padx=4)


    # =========================================================
    # LOAD RECORD (GET BY ID)
    # =========================================================
    def load_record(self, record_id):

        try:

            data = api_client.get_sampling_certificate_api(record_id)

            self.record_id = record_id

            for key in self.vars:

                if key in data and data[key] is not None:
                    self.vars[key].set(data[key])

            # seals
            for h in self.holds:

                col = f"hold_{h['hold']}_seal"

                if col in data and data[col]:
                    h["seal"].set(data[col])

            if data.get("observations"):
                self.observations.insert("1.0", data["observations"])

            if data.get("date"):
                self.date_var.set(data["date"])

            if data.get("closing_date"):
                self.closing_date_var.set(data["closing_date"])

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Unable to load record:\n{str(e)}"
            )


