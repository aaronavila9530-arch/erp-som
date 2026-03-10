import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from api_client import (
    create_vessel_truck_supervision_api,
    update_vessel_truck_supervision_api,
    get_vessel_truck_supervision_by_id_api
)

from Modulos.Informes.vessel_truck_supervision.popup_servicio_selector import (
    PopupServicioSelector
)

from api_client import improve_truck_supervision_api
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare


class VesselTruckSupervisionForm(ttk.Frame):

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        self.current_report_id = None

        self.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_scrollable_form()

    # =========================================================
    # HEADER
    # =========================================================
    def _build_header(self):

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="Vessel Truck Supervision Report",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        if self.on_back:
            ttk.Button(
                header,
                text="← Back",
                command=self.on_back
            ).pack(side="right")

    # =========================================================
    # SCROLLABLE
    # =========================================================
    def _build_scrollable_form(self):

        canvas = tk.Canvas(self)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.form = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.form, anchor="nw")

        self.form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._section_header_data()
        self._section_ship()
        self._section_representatives()
        self._section_times()
        self._section_process()
        self._section_findings()
        self._section_conclusion()
        self._section_actions()
    # =========================================================
    # HEADER DATA + BUSCAR
    # =========================================================
    def _section_header_data(self):

        frm = ttk.LabelFrame(self.form, text="Report Header")
        frm.pack(fill="x", pady=10)

        # ---------------- CERT ----------------
        ttk.Label(frm, text="CERT Nº").grid(row=0, column=0, sticky="w", padx=5)
        self.cert_no = ttk.Entry(frm, width=25)
        self.cert_no.grid(row=0, column=1, padx=5)

        ttk.Button(
            frm,
            text="Buscar",
            command=self._search_report
        ).grid(row=0, column=2, padx=5)

        # ---------------- CUSTOMER (NUEVO) ----------------
        ttk.Label(frm, text="Customer").grid(row=1, column=0, sticky="w", padx=5)
        self.customer = ttk.Entry(frm, width=40)
        self.customer.grid(row=1, column=1, columnspan=2, padx=5, sticky="w")

        # ---------------- PUERTO ----------------
        ttk.Label(frm, text="Puerto").grid(row=2, column=0, sticky="w", padx=5)
        self.port = ttk.Entry(frm, width=30)
        self.port.grid(row=2, column=1, padx=5)

        # ---------------- PAÍS ----------------
        ttk.Label(frm, text="País").grid(row=2, column=2, sticky="w", padx=5)
        self.country = ttk.Entry(frm, width=25)
        self.country.grid(row=2, column=3, padx=5)

        # ---------------- FECHA ----------------
        ttk.Label(frm, text="Fecha").grid(row=3, column=0, sticky="w", padx=5)
        self.report_date = DateEntry(frm, width=15, date_pattern="dd-mm-yyyy")
        self.report_date.grid(row=3, column=1, padx=5)

    # =========================================================
    # BUQUE
    # =========================================================
    def _section_ship(self):

        frm = ttk.LabelFrame(self.form, text="2. BUQUE")
        frm.pack(fill="x", pady=10)

        labels = [
            "Nombre",
            "Bandera / Puerto Registro",
            "GRT",
            "NRT",
            "IMO Nº",
            "Año Construcción"
        ]

        self.ship_fields = {}

        for i, label in enumerate(labels):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", padx=5)
            entry = ttk.Entry(frm, width=30)
            entry.grid(row=i, column=1, padx=5)
            self.ship_fields[label] = entry

    # =========================================================
    # REPRESENTANTES
    # =========================================================
    def _section_representatives(self):

        frm = ttk.LabelFrame(self.form, text="Representantes")
        frm.pack(fill="x", pady=10)

        ttk.Label(frm, text="Capitán").grid(row=0, column=0, padx=5)
        self.captain = ttk.Entry(frm, width=30)
        self.captain.grid(row=0, column=1, padx=5)

        ttk.Label(frm, text="Primer Oficial").grid(row=1, column=0, padx=5)
        self.chief_officer = ttk.Entry(frm, width=30)
        self.chief_officer.grid(row=1, column=1, padx=5)

    # =========================================================
    # TIEMPOS
    # =========================================================
    def _section_times(self):

        frm = ttk.LabelFrame(self.form, text="Tiempos")
        frm.pack(fill="x", pady=10)

        self.time_fields = {}

        fields = [
            "Fecha Arribo",
            "Fecha Inspección",
            "Supervisión Completada"
        ]

        for i, label in enumerate(fields):
            ttk.Label(frm, text=label).grid(row=i, column=0, padx=5)
            entry = DateEntry(frm, width=15, date_pattern="dd-mm-yyyy")
            entry.grid(row=i, column=1, padx=5)
            self.time_fields[label] = entry

    # =========================================================
    # PROCESO
    # =========================================================
    def _section_process(self):

        frm = ttk.LabelFrame(self.form, text="4. Proceso de Supervisión")
        frm.pack(fill="both", expand=True, pady=10)

        self.process_text = tk.Text(frm, height=6, wrap="word")
        self.process_text.pack(fill="both", expand=True, padx=5, pady=5)

    # =========================================================
    # HALLAZGOS DIVIDIDOS
    # =========================================================
    def _section_findings(self):

        frm = ttk.LabelFrame(self.form, text="5. Hallazgos")
        frm.pack(fill="both", expand=True, pady=10)

        ttk.Label(frm, text="5.1 Hallazgos Documentales").pack(anchor="w")
        self.findings_doc = tk.Text(frm, height=4, wrap="word")
        self.findings_doc.pack(fill="x", padx=5, pady=5)

        ttk.Label(frm, text="5.2 Hallazgos de Control Operativo").pack(anchor="w")
        self.findings_oper = tk.Text(frm, height=4, wrap="word")
        self.findings_oper.pack(fill="x", padx=5, pady=5)

        ttk.Label(frm, text="5.3 Incidentes").pack(anchor="w")
        self.findings_inc = tk.Text(frm, height=4, wrap="word")
        self.findings_inc.pack(fill="x", padx=5, pady=5)

    # =========================================================
    # CONCLUSIÓN
    # =========================================================
    def _section_conclusion(self):

        frm = ttk.LabelFrame(self.form, text="6. Conclusión")
        frm.pack(fill="both", expand=True, pady=10)

        self.conclusion_text = tk.Text(frm, height=6, wrap="word")
        self.conclusion_text.pack(fill="both", expand=True, padx=5, pady=5)

    # =========================================================
    # ACTIONS (Guardar Cambios + Enviar)
    # =========================================================
    def _section_actions(self):

        frm = ttk.Frame(self.form)
        frm.pack(fill="x", pady=20)

        # ---------------- GUARDAR CAMBIOS ----------------
        self.btn_save_changes = ttk.Button(
            frm,
            text="Guardar Cambios",
            command=self._save_changes,
            state="disabled"
        )
        self.btn_save_changes.pack(side="right", padx=5)

        # ---------------- ENVIAR A REVISIÓN ----------------
        ttk.Button(
            frm,
            text="Enviar a Revisión",
            command=self._submit_for_review
        ).pack(side="right", padx=5)

        # ---------------- AI ----------------
        ttk.Button(
            frm,
            text="Improve AI Maritime",
            command=self._improve_ai
        ).pack(side="right", padx=5)


    # =========================================================
    # API SAVE
    # =========================================================
    def _submit_for_review(self):

        data = {
            "cert_no": self.cert_no.get(),
            "customer": self.customer.get(),
            "port": self.port.get(),
            "country": self.country.get(),
            "report_date": self.report_date.get(),

            "vessel_name": self.ship_fields["Nombre"].get(),
            "flag_port_registry": self.ship_fields["Bandera / Puerto Registro"].get(),
            "grt": self.ship_fields["GRT"].get(),
            "nrt": self.ship_fields["NRT"].get(),
            "imo_no": self.ship_fields["IMO Nº"].get(),
            "build_year": self.ship_fields["Año Construcción"].get(),

            "captain": self.captain.get(),
            "chief_officer": self.chief_officer.get(),

            "arrival_date": self.time_fields["Fecha Arribo"].get(),
            "inspection_date": self.time_fields["Fecha Inspección"].get(),
            "supervision_completed_date": self.time_fields["Supervisión Completada"].get(),

            "process_text": self.process_text.get("1.0", "end").strip(),

            "findings_documental_text": self.findings_doc.get("1.0", "end").strip(),
            "findings_operational_text": self.findings_oper.get("1.0", "end").strip(),
            "incidents_text": self.findings_inc.get("1.0", "end").strip(),

            "conclusion_text": self.conclusion_text.get("1.0", "end").strip(),
        }

        try:

            if self.current_report_id:
                update_vessel_truck_supervision_api(
                    self.current_report_id,
                    data
                )
            else:
                resp = create_vessel_truck_supervision_api(data)
                self.current_report_id = resp.get("data", {}).get("id")

            messagebox.showinfo(
                "Success",
                "Report sent successfully."
            )

            # 🔥 VOLVER AL MAIN SCREEN
            if self.on_back:
                self.on_back()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error sending report:\n{e}"
            )

    # =========================================================
    # SEARCH
    # =========================================================
    def _search_report(self):
        """
        Abre popup de servicios para seleccionar un servicio
        y autocompletar el formulario.
        """
        self._open_servicio_popup()


    # =========================================================
    # OPEN POPUP SERVICIOS
    # =========================================================
    def _open_servicio_popup(self):

        PopupServicioSelector(
            parent=self,
            on_select=self._on_servicio_selected
        )


    # =========================================================
    # SERVICIO SELECTED CALLBACK
    # =========================================================
    def _on_servicio_selected(self, values):
        """
        values viene del popup en este orden:

        (
            num_informe,
            buque_contenedor,
            cliente,
            continente,
            pais,
            puerto,
            anio,
            mes,
            operacion
        )
        """

        (
            num_informe,
            buque,
            cliente,
            continente,
            pais,
            puerto,
            anio,
            mes,
            operacion
        ) = values

        # ================= CERT NO =================
        self.cert_no.config(state="normal")
        self.cert_no.delete(0, "end")
        self.cert_no.insert(0, str(num_informe or ""))
        self.cert_no.config(state="readonly")

        # ================= CUSTOMER =================
        self.customer.config(state="normal")
        self.customer.delete(0, "end")
        self.customer.insert(0, str(cliente or ""))
        self.customer.config(state="readonly")

        # ================= PUERTO =================
        self.port.config(state="normal")
        self.port.delete(0, "end")
        self.port.insert(0, str(puerto or ""))
        self.port.config(state="readonly")

        # ================= PAÍS =================
        self.country.config(state="normal")
        self.country.delete(0, "end")
        self.country.insert(0, str(pais or ""))
        self.country.config(state="readonly")

        # ================= FECHA =================
        try:
            if anio and mes:
                fecha = datetime(int(anio), int(mes), 1)
                self.report_date.set_date(fecha)
        except Exception:
            pass

        # ================= BUQUE =================
        try:
            vessel_entry = self.ship_fields["Nombre"]
            vessel_entry.config(state="normal")
            vessel_entry.delete(0, "end")
            vessel_entry.insert(0, str(buque or ""))
            vessel_entry.config(state="readonly")
        except Exception:
            pass

        # ================= FECHA INSPECCIÓN =================
        try:
            if anio and mes:
                fecha = datetime(int(anio), int(mes), 1)
                self.time_fields["Fecha Inspección"].set_date(fecha)
        except Exception:
            pass


    # =========================================================
    # AI IMPROVE (SELECCIÓN DE SECCIÓN + IDIOMA)
    # =========================================================
    def _improve_ai(self):

        # ================= SELECCIÓN DE SECCIÓN =================
        opciones = {
            "1": ("Proceso de Supervisión", self.process_text),
            "2": ("Hallazgos Documentales", self.findings_doc),
            "3": ("Hallazgos Control Operativo", self.findings_oper),
            "4": ("Incidentes", self.findings_inc),
            "5": ("Conclusión", self.conclusion_text),
        }

        seleccion = tk.simpledialog.askstring(
            "Mejorar Sección",
            "¿Qué sección desea mejorar?\n\n"
            "1 - Proceso de Supervisión\n"
            "2 - Hallazgos Documentales\n"
            "3 - Hallazgos Control Operativo\n"
            "4 - Incidentes\n"
            "5 - Conclusión"
        )

        if not seleccion or seleccion not in opciones:
            return

        titulo, widget = opciones[seleccion]

        texto_actual = widget.get("1.0", "end").strip()

        if not texto_actual:
            messagebox.showwarning(
                "Texto vacío",
                "La sección seleccionada no contiene texto."
            )
            return

        # ================= IDIOMA =================
        respuesta = messagebox.askquestion(
            "Idioma",
            "¿Desea la respuesta en inglés?\n\nYes = Inglés\nNo = Español"
        )

        language = "EN" if respuesta == "yes" else "ES"

        try:

            payload = {
                "text": texto_actual,
                "vessel": self.ship_fields["Nombre"].get(),
                "location": self.port.get(),
                "cargo": "Truck Discharge Operation",
                "language": language
            }

            resp = improve_truck_supervision_api(payload)

            if not resp.get("success"):
                messagebox.showerror(
                    "Error IA",
                    "La IA no devolvió respuesta válida."
                )
                return

            ai_text = resp.get("text", "")

            # ================= POPUP COMPARACIÓN =================
            PopupAICompare(
                parent=self,
                original_text=texto_actual,
                ai_text=ai_text,
                on_accept=lambda new_text: self._apply_ai_section(widget, new_text),
                on_retry=self._improve_ai
            )

        except Exception as e:
            messagebox.showerror(
                "Error IA",
                f"No se pudo procesar la mejora AI:\n{e}"
            )


    # =========================================================
    # APPLY AI TEXT TO SPECIFIC SECTION
    # =========================================================
    def _apply_ai_section(self, widget, new_text):

        widget.delete("1.0", "end")
        widget.insert("1.0", new_text)



    # =========================================================
    # COLLECT FORM DATA
    # =========================================================
    def _collect_form_data(self):

        return {

            "cert_no": self.cert_no.get(),
            "customer": self.customer.get(),
            "port": self.port.get(),
            "country": self.country.get(),
            "report_date": self.report_date.get(),

            "vessel_name": self.ship_fields["Nombre"].get(),
            "flag_port_registry": self.ship_fields["Bandera / Puerto Registro"].get(),
            "grt": self.ship_fields["GRT"].get(),
            "nrt": self.ship_fields["NRT"].get(),
            "imo_no": self.ship_fields["IMO Nº"].get(),
            "build_year": self.ship_fields["Año Construcción"].get(),

            "captain": self.captain.get(),
            "chief_officer": self.chief_officer.get(),

            "arrival_date": self.time_fields["Fecha Arribo"].get(),
            "inspection_date": self.time_fields["Fecha Inspección"].get(),
            "supervision_completed_date": self.time_fields["Supervisión Completada"].get(),

            "process_text": self.process_text.get("1.0", "end").strip(),

            "findings_documental_text": self.findings_doc.get("1.0", "end").strip(),
            "findings_operational_text": self.findings_oper.get("1.0", "end").strip(),
            "incidents_text": self.findings_inc.get("1.0", "end").strip(),

            "conclusion_text": self.conclusion_text.get("1.0", "end").strip(),
        }


    # =========================================================
    # SAVE CHANGES (PUT)
    # =========================================================
    def _save_changes(self):

        if not self.current_report_id:
            messagebox.showwarning(
                "Guardar",
                "No hay reporte cargado."
            )
            return

        data = self._collect_form_data()

        try:

            update_vessel_truck_supervision_api(
                self.current_report_id,
                data
            )

            messagebox.showinfo(
                "Success",
                "Cambios guardados correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron guardar los cambios:\n{e}"
            )





    # =========================================================
    # LOAD DATA FROM BACKEND
    # =========================================================
    def load_report(self, report_id: int):

        try:

            resp = get_vessel_truck_supervision_by_id_api(report_id)

            if not resp or not resp.get("success"):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "No se pudo cargar el reporte.")
                )
                return

            data = resp.get("data", {})

            self.current_report_id = report_id

            # ================= HEADER =================
            self.cert_no.delete(0, "end")
            self.cert_no.insert(0, data.get("cert_no", ""))

            self.customer.delete(0, "end")
            self.customer.insert(0, data.get("customer", ""))

            self.port.delete(0, "end")
            self.port.insert(0, data.get("port", ""))

            self.country.delete(0, "end")
            self.country.insert(0, data.get("country", ""))

            # ================= FECHAS =================
            try:
                if data.get("report_date"):
                    self.report_date.set_date(data.get("report_date"))
            except:
                pass

            try:
                if data.get("arrival_date"):
                    self.time_fields["Fecha Arribo"].set_date(data.get("arrival_date"))
            except:
                pass

            try:
                if data.get("inspection_date"):
                    self.time_fields["Fecha Inspección"].set_date(data.get("inspection_date"))
            except:
                pass

            try:
                if data.get("supervision_completed_date"):
                    self.time_fields["Supervisión Completada"].set_date(
                        data.get("supervision_completed_date")
                    )
            except:
                pass


            # ================= REPRESENTANTES =================
            self.captain.delete(0, "end")
            self.captain.insert(0, data.get("captain", ""))

            self.chief_officer.delete(0, "end")
            self.chief_officer.insert(0, data.get("chief_officer", ""))

            # ================= SHIP =================
            self.ship_fields["Nombre"].delete(0, "end")
            self.ship_fields["Nombre"].insert(0, data.get("vessel_name", ""))

            self.ship_fields["Bandera / Puerto Registro"].delete(0, "end")
            self.ship_fields["Bandera / Puerto Registro"].insert(
                0, data.get("flag_port_registry", "")
            )

            self.ship_fields["GRT"].delete(0, "end")
            self.ship_fields["GRT"].insert(0, data.get("grt", ""))

            self.ship_fields["NRT"].delete(0, "end")
            self.ship_fields["NRT"].insert(0, data.get("nrt", ""))

            self.ship_fields["IMO Nº"].delete(0, "end")
            self.ship_fields["IMO Nº"].insert(0, data.get("imo_no", ""))

            self.ship_fields["Año Construcción"].delete(0, "end")
            self.ship_fields["Año Construcción"].insert(0, data.get("build_year", ""))

            # ================= TEXT AREAS =================
            self.process_text.delete("1.0", "end")
            self.process_text.insert("1.0", data.get("process_text", ""))

            self.findings_doc.delete("1.0", "end")
            self.findings_doc.insert("1.0", data.get("findings_documental_text", ""))

            self.findings_oper.delete("1.0", "end")
            self.findings_oper.insert("1.0", data.get("findings_operational_text", ""))

            self.findings_inc.delete("1.0", "end")
            self.findings_inc.insert("1.0", data.get("incidents_text", ""))

            self.conclusion_text.delete("1.0", "end")
            self.conclusion_text.insert("1.0", data.get("conclusion_text", ""))

            # 🔥 HABILITAR GUARDAR CAMBIOS
            self.btn_save_changes.config(state="normal")

        except Exception as e:
            messagebox.showerror("Error", str(e))
