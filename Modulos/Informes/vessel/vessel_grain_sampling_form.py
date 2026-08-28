import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from api_client import (
    improve_grain_sampling_api,
    create_vessel_grain_sampling_api,
)
from Modulos.Informes.date_utils import to_db_date, to_db_datetime, to_long_english_date

from Modulos.Informes.popup.popup_ai_compare import PopupAICompare
from Modulos.Informes.popup.popup_grain_service_selector import PopupGrainServiceSelector


class GrainSamplingVesselForm(ttk.Frame):

    DEFAULT_LEGAL = (
        "EL PRESENTE INFORME SE EMITE EN BUENA FE SIN PERJUICIO Y EN BENEFICIO "
        "DE LOS INTERESADOS, Y NOS RESERVAMOS EL DERECHO DE MODIFICARLO Y/O "
        "AMPLIARLO EN CASO DE QUE TENGAMOS CONOCIMIENTO DE NUEVOS DATOS."
    )

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        try:
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        self.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_scrollable_form()

    # =========================================================
    # HEADER
    # =========================================================
    # =========================================================
    # HEADER
    # =========================================================
    def _build_header(self):

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="Vessel Grain Sampling Report",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        # ======================================================
        # 🔥 BACK 100% FORZADO A HOME (SIN DEPENDER DE on_back)
        # ======================================================
        def _go_home():

            try:
                from Modulos.Informes.informes_home_ui import InformesHomeUI

                # 🔥 destruir TODO el contenido del parent (clave)
                for widget in self.parent.winfo_children():
                    widget.destroy()

                # 🔥 reconstruir HOME correctamente
                home = InformesHomeUI(
                    self.parent,
                    usuario=self.usuario,
                    rol=self.rol
                )

                home.pack(fill="both", expand=True)

            except Exception as e:
                messagebox.showerror("Navigation Error", str(e))

        ttk.Button(
            header,
            text="Back",
            command=_go_home  # 🔥 SIEMPRE usa este (no on_back)
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

        # 🔥 ACTIVAR SCROLL CON RUEDA (VERSIÓN PRO)
        self._bind_mousewheel(canvas)

        self._section_selector()
        self._section_main_data()
        self._section_ship()  
        self._section_times()
        self._section_products()
        self._section_sampling()
        self._section_conclusion()
        self._section_actions()

    # =========================================================
    # CERT SELECTOR + BOTÓN POPUP
    # =========================================================
    def _section_selector(self):

        frm = ttk.LabelFrame(self.form, text="Report Header")
        frm.pack(fill="x", pady=10)

        # CERT Nº
        ttk.Label(frm, text="CERT Nº").grid(row=0, column=0, sticky="w", padx=5)

        self.cert_no = ttk.Entry(frm, width=25)
        self.cert_no.grid(row=0, column=1, padx=5)

        # 🔎 BOTÓN PARA ABRIR POPUP
        ttk.Button(
            frm,
            text="🔎",
            width=3,
            command=self._open_service_selector
        ).grid(row=0, column=2, padx=5)

        # PUERTO (AUTO - BLOQUEADO)
        ttk.Label(frm, text="Puerto").grid(row=1, column=0, sticky="w", padx=5)

        self.port_entry = ttk.Entry(frm, width=35, state="readonly")
        self.port_entry.grid(row=1, column=1, padx=5, columnspan=2)

        # Fecha
        ttk.Label(frm, text="Fecha").grid(row=1, column=3, sticky="w", padx=5)

        self.inspection_date = DateEntry(
            frm,
            width=12,
            date_pattern="yyyy-mm-dd"
        )
        self.inspection_date.grid(row=1, column=4, padx=5)
        self.inspection_date.bind("<<DateEntrySelected>>", self._format_inspection_date_long)

    # =========================================================
    # MAIN DATA (AUTO FROM POPUP - READONLY)
    # =========================================================
    def _format_inspection_date_long(self, event=None):
        self.inspection_date.delete(0, "end")
        self.inspection_date.insert(0, to_long_english_date(self.inspection_date.get_date()))


    def _section_main_data(self):

        frm = ttk.LabelFrame(self.form, text="Main Information")
        frm.pack(fill="x", pady=10)

        # BUQUE (AUTO - BLOQUEADO)
        ttk.Label(frm, text="Buque").grid(row=0, column=0, sticky="w", padx=5)
        self.vessel_entry = ttk.Entry(frm, width=35, state="readonly")
        self.vessel_entry.grid(row=0, column=1, padx=5)

        # CLIENTE (AUTO - BLOQUEADO)
        ttk.Label(frm, text="Cliente").grid(row=1, column=0, sticky="w", padx=5)
        self.client_entry = ttk.Entry(frm, width=35, state="readonly")
        self.client_entry.grid(row=1, column=1, padx=5)

        # CAPITAN (MANUAL)
        ttk.Label(frm, text="Capitán").grid(row=2, column=0, sticky="w", padx=5)
        self.captain = ttk.Entry(frm, width=30)
        self.captain.grid(row=2, column=1, padx=5)

        # PRIMER OFICIAL (MANUAL)
        ttk.Label(frm, text="Primer Oficial").grid(row=3, column=0, sticky="w", padx=5)
        self.chief_officer = ttk.Entry(frm, width=30)
        self.chief_officer.grid(row=3, column=1, padx=5)


    # =========================================================
    # SECTION 2 — BUQUE (SEGÚN TEMPLATE WORD)
    # =========================================================
    def _section_ship(self):

        frm = ttk.LabelFrame(self.form, text="2. BUQUE")
        frm.pack(fill="x", pady=10)

        # 2.1 Nombre (AUTO)
        ttk.Label(frm, text="2.1 Nombre").grid(row=0, column=0, sticky="w", padx=5)

        self.ship_name = ttk.Entry(frm, width=35, state="readonly")
        self.ship_name.grid(row=0, column=1, padx=5)

        # 2.2 Bandera / Puerto de Registro
        ttk.Label(frm, text="2.2 Bandera / Puerto de Registro").grid(row=1, column=0, sticky="w", padx=5)
        self.ship_flag = ttk.Entry(frm, width=35)
        self.ship_flag.grid(row=1, column=1, padx=5)

        # 2.3 GRT
        ttk.Label(frm, text="2.3 GRT").grid(row=2, column=0, sticky="w", padx=5)
        self.ship_grt = ttk.Entry(frm, width=20)
        self.ship_grt.grid(row=2, column=1, padx=5)

        # 2.4 NRT
        ttk.Label(frm, text="2.4 NRT").grid(row=3, column=0, sticky="w", padx=5)
        self.ship_nrt = ttk.Entry(frm, width=20)
        self.ship_nrt.grid(row=3, column=1, padx=5)

        # 2.5 IMO Nº
        ttk.Label(frm, text="2.5 IMO Nº").grid(row=4, column=0, sticky="w", padx=5)
        self.ship_imo = ttk.Entry(frm, width=20)
        self.ship_imo.grid(row=4, column=1, padx=5)

        # 2.6 Año Construcción (SOLO AÑO)
        ttk.Label(frm, text="2.6 Año de Construcción").grid(row=5, column=0, sticky="w", padx=5)

        current_year = datetime.now().year
        years = [str(y) for y in range(current_year, 1950, -1)]

        self.ship_year = ttk.Combobox(
            frm,
            values=years,
            width=10,
            state="readonly"
        )
        self.ship_year.grid(row=5, column=1, padx=5)


    # =========================================================
    # SECTION 3 — TIEMPOS (SEGÚN TEMPLATE WORD)
    # =========================================================
    def _section_times(self):

        frm = ttk.LabelFrame(self.form, text="3. TIEMPOS")
        frm.pack(fill="x", pady=10)

        self.times = {}

        fields = [
            ("arrival_buoy_time", "3.1 Arribo Boya de Mar"),
            ("nor_tendered_time", "3.2 N.O.R Tendered"),
            ("holds_opening_time", "3.3 Apertura de Bodegas"),
            ("surveyors_onboard_time", "3.4 Surveyors a bordo"),
            ("seals_verification_time", "3.5 Verificación de Sellos"),
            ("sampling_start_time", "3.6 Inicio de Muestreo"),
            ("sampling_end_time", "3.7 Finalización Muestreo"),
            ("surveyors_disembark_time", "3.8 Surveyors Desembarcando"),
        ]

        for i, (key, label) in enumerate(fields):
            self.times[key] = self._datetime_picker(frm, label, i)

    # =========================================================
    # PRODUCTS (CUADRO ESTRUCTURADO COMO WORD)
    # =========================================================
    def _section_products(self):

        frm = ttk.LabelFrame(self.form, text="PRODUCTOS")
        frm.pack(fill="x", pady=10)

        # Línea superior
        ttk.Label(frm, text="Tonelaje Total (MT)").grid(row=0, column=0, sticky="w", padx=5)
        self.tonnage = ttk.Entry(frm, width=20)
        self.tonnage.grid(row=0, column=1, padx=5)

        ttk.Label(frm, text="Bodegas (ej: 1-4-5)").grid(row=0, column=2, sticky="w", padx=5)
        self.holds = ttk.Entry(frm, width=20)
        self.holds.grid(row=0, column=3, padx=5)

        # Tabla por bodega
        table = ttk.Frame(frm)
        table.grid(row=1, column=0, columnspan=4, pady=10)

        headers = ["PRODUCTO", "BODEGA", "TONELAJE (MT)"]
        for c, h in enumerate(headers):
            ttk.Label(
                table,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=c, padx=5, pady=3)

        self.hold_rows = []

        for r in range(5):
            product_entry = ttk.Entry(table, width=25)
            product_entry.grid(row=r + 1, column=0, padx=5)
            product_entry.insert(0, "MAIZ AMARILLO")

            hold_entry = ttk.Entry(table, width=10)
            hold_entry.grid(row=r + 1, column=1, padx=5)
            hold_entry.insert(0, str(r + 1))

            ton_entry = ttk.Entry(table, width=15)
            ton_entry.grid(row=r + 1, column=2, padx=5)

            self.hold_rows.append({
                "product": product_entry,
                "hold": hold_entry,
                "tonnage": ton_entry
            })

    # =========================================================
    # SAMPLING DETAILS (4.1 - 4.7 ESTRUCTURADO)
    # =========================================================
    def _section_sampling(self):

        frm = ttk.LabelFrame(self.form, text="4. TOMA DE MUESTRAS")
        frm.pack(fill="x", pady=10)

        # 4.1 BUQUE (AUTO - BLOQUEADO)
        ttk.Label(frm, text="Buque").grid(row=0, column=0, sticky="w", padx=5)
        self.sample_vessel_entry = ttk.Entry(frm, width=30, state="readonly")
        self.sample_vessel_entry.grid(row=0, column=1, padx=5)

        # 4.1 CLIENTE (AUTO - BLOQUEADO)
        ttk.Label(frm, text="Cliente").grid(row=0, column=2, sticky="w", padx=5)
        self.sample_client_entry = ttk.Entry(frm, width=30, state="readonly")
        self.sample_client_entry.grid(row=0, column=3, padx=5)

        # 4.2 Fecha / Hora
        ttk.Label(frm, text="Fecha Supervisión").grid(row=1, column=0, sticky="w", padx=5)
        self.supervision_datetime = self._datetime_picker(frm, "", 1)

        # Representante MAG
        ttk.Label(frm, text="Representante MAG").grid(row=2, column=0, sticky="w", padx=5)
        self.mag_rep = ttk.Entry(frm, width=30)
        self.mag_rep.grid(row=2, column=1, padx=5)

        # Bodegas muestreadas
        ttk.Label(frm, text="Bodegas Muestreadas").grid(row=3, column=0, sticky="w", padx=5)
        self.sampled_holds = ttk.Entry(frm, width=30)
        self.sampled_holds.grid(row=3, column=1, padx=5)

        # 4.5 / 4.6 / 4.7
        ttk.Label(
            frm,
            text="Puntos de Muestreo por Bodega",
            font=("Segoe UI", 9, "bold")
        ).grid(row=4, column=0, columnspan=4, pady=(10, 5))

        self.sampling_points = []

        positions = [
            "Proa Babor",
            "Proa Estribor",
            "Centro",
            "Popa Babor",
            "Popa Estribor"
        ]

        for i in range(5):
            row_base = 5 + (i * 6)

            ttk.Label(frm, text=f"Bodega Nº").grid(row=row_base, column=0, sticky="w", padx=5)
            hold_entry = ttk.Entry(frm, width=10)
            hold_entry.grid(row=row_base, column=1, padx=5)

            point_entries = {}

            for j, pos in enumerate(positions):
                ttk.Label(frm, text=pos).grid(row=row_base + j + 1, column=0, sticky="e", padx=5)
                entry = ttk.Entry(frm, width=5)
                entry.grid(row=row_base + j + 1, column=1, sticky="w", padx=5)
                point_entries[pos] = entry

            self.sampling_points.append({
                "hold": hold_entry,
                "points": point_entries
            })

    # =========================================================
    # CONCLUSION
    # =========================================================
    def _section_conclusion(self):

        frm = ttk.LabelFrame(self.form, text="Conclusion")
        frm.pack(fill="both", expand=True, pady=10)

        self.conclusion = tk.Text(frm, height=6, wrap="word")
        self.conclusion.pack(fill="both", expand=True, padx=5, pady=5)

    # =========================================================
    # ACTIONS
    # =========================================================
    def _section_actions(self):

        frm = ttk.Frame(self.form)
        frm.pack(fill="x", pady=20)

        ttk.Button(
            frm,
            text="Mejorar conclusion con PORTIA",
            command=self._improve_conclusion
        ).pack(side="left", padx=5)

        ttk.Button(
            frm,
            text="Crear Informe",
            command=self._create_report
        ).pack(side="right", padx=5)

    # =========================================================
    # AI
    # =========================================================
    def _improve_conclusion(self):

        text = self.conclusion.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Warning", "No conclusion text.")
            return

        language = self._ask_ai_language()
        if not language:
            return

        try:
            ai_text = improve_grain_sampling_api(
                text=text,
                vessel=self.vessel_entry.get(),
                location=self.port_entry.get(),
                product="Maíz Amarillo",
                authority=self.client_entry.get(),
                language=language  # 🔥 Nuevo parámetro
            )

            PopupAICompare(
                self,
                original_text=text,
                ai_text=ai_text,
                on_accept=lambda t: self._apply_ai_text(t),
                on_retry=lambda: self._improve_conclusion()
            )

        except Exception as e:
            messagebox.showerror("PORTIA Error", str(e))

    # =========================================================
    # CREATE — 100% ALIGNED WITH DB STRUCTURE
    # =========================================================
    def _create_report(self):

        hold_values = []

        for row in self.hold_rows:
            hold_values.append({
                "product": row["product"].get(),
                "hold": row["hold"].get(),
                "tonnage": row["tonnage"].get()
            })

        while len(hold_values) < 5:
            hold_values.append({"product": None, "hold": None, "tonnage": None})

        sample_values = []

        for sp in self.sampling_points:
            sample_values.append({
                "hold": sp["hold"].get(),
                "proa_babor": sp["points"]["Proa Babor"].get(),
                "proa_estribor": sp["points"]["Proa Estribor"].get(),
                "centro": sp["points"]["Centro"].get(),
                "popa_babor": sp["points"]["Popa Babor"].get(),
                "popa_estribor": sp["points"]["Popa Estribor"].get(),
            })

        while len(sample_values) < 5:
            sample_values.append({
                "hold": None,
                "proa_babor": None,
                "proa_estribor": None,
                "centro": None,
                "popa_babor": None,
                "popa_estribor": None,
            })

        payload = {

            "cert_no": self.cert_no.get(),
            "place_date": to_db_date(self.inspection_date.get()),

            "vessel_name": self.vessel_entry.get(),
            "requested_by": self.client_entry.get(),
            "captain": self.captain.get(),
            "chief_officer": self.chief_officer.get(),

            "ship_flag": self.ship_flag.get(),
            "ship_grt": self.ship_grt.get(),
            "ship_nrt": self.ship_nrt.get(),
            "ship_imo": self.ship_imo.get(),
            "ship_year": self.ship_year.get(),

            "arrival_buoy_time": self.times["arrival_buoy_time"]["get"](),
            "nor_tendered_time": self.times["nor_tendered_time"]["get"](),
            "holds_opening_time": self.times["holds_opening_time"]["get"](),
            "surveyors_onboard_time": self.times["surveyors_onboard_time"]["get"](),
            "seals_verification_time": self.times["seals_verification_time"]["get"](),
            "sampling_start_time": self.times["sampling_start_time"]["get"](),
            "sampling_end_time": self.times["sampling_end_time"]["get"](),
            "surveyors_disembark_time": self.times["surveyors_disembark_time"]["get"](),

            "hold1_product": hold_values[0]["product"],
            "hold1_hold": hold_values[0]["hold"],
            "hold1_tonnage": hold_values[0]["tonnage"],
            "hold2_product": hold_values[1]["product"],
            "hold2_hold": hold_values[1]["hold"],
            "hold2_tonnage": hold_values[1]["tonnage"],
            "hold3_product": hold_values[2]["product"],
            "hold3_hold": hold_values[2]["hold"],
            "hold3_tonnage": hold_values[2]["tonnage"],
            "hold4_product": hold_values[3]["product"],
            "hold4_hold": hold_values[3]["hold"],
            "hold4_tonnage": hold_values[3]["tonnage"],
            "hold5_product": hold_values[4]["product"],
            "hold5_hold": hold_values[4]["hold"],
            "hold5_tonnage": hold_values[4]["tonnage"],

            "products_total": self.tonnage.get(),

            "sample1_hold": sample_values[0]["hold"],
            "sample1_proa_babor": sample_values[0]["proa_babor"],
            "sample1_proa_estribor": sample_values[0]["proa_estribor"],
            "sample1_centro": sample_values[0]["centro"],
            "sample1_popa_babor": sample_values[0]["popa_babor"],
            "sample1_popa_estribor": sample_values[0]["popa_estribor"],

            "sample2_hold": sample_values[1]["hold"],
            "sample2_proa_babor": sample_values[1]["proa_babor"],
            "sample2_proa_estribor": sample_values[1]["proa_estribor"],
            "sample2_centro": sample_values[1]["centro"],
            "sample2_popa_babor": sample_values[1]["popa_babor"],
            "sample2_popa_estribor": sample_values[1]["popa_estribor"],

            "sample3_hold": sample_values[2]["hold"],
            "sample3_proa_babor": sample_values[2]["proa_babor"],
            "sample3_proa_estribor": sample_values[2]["proa_estribor"],
            "sample3_centro": sample_values[2]["centro"],
            "sample3_popa_babor": sample_values[2]["popa_babor"],
            "sample3_popa_estribor": sample_values[2]["popa_estribor"],

            "sample4_hold": sample_values[3]["hold"],
            "sample4_proa_babor": sample_values[3]["proa_babor"],
            "sample4_proa_estribor": sample_values[3]["proa_estribor"],
            "sample4_centro": sample_values[3]["centro"],
            "sample4_popa_babor": sample_values[3]["popa_babor"],
            "sample4_popa_estribor": sample_values[3]["popa_estribor"],

            "sample5_hold": sample_values[4]["hold"],
            "sample5_proa_babor": sample_values[4]["proa_babor"],
            "sample5_proa_estribor": sample_values[4]["proa_estribor"],
            "sample5_centro": sample_values[4]["centro"],
            "sample5_popa_babor": sample_values[4]["popa_babor"],
            "sample5_popa_estribor": sample_values[4]["popa_estribor"],

            "supervision": self.supervision_datetime["get"](),
            "conclusion": self.conclusion.get("1.0", "end").strip(),

            "status": "Created"
        }

        try:
            result = create_vessel_grain_sampling_api(payload)

            messagebox.showinfo(
                "Success",
                f"Informe creado correctamente.\nID: {result.get('id')}"
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # DATETIME PICKER (igual container)
    # =========================================================
    def _datetime_picker(self, parent, label, row):

        if label:
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="w")

        date_var = tk.StringVar()
        date_entry = DateEntry(frame, textvariable=date_var, date_pattern="yyyy-mm-dd")
        date_entry.pack(side="left")
        date_entry.bind(
            "<<DateEntrySelected>>",
            lambda event: date_var.set(to_long_english_date(date_var.get()))
        )

        hour_var = tk.StringVar(value="00")
        minute_var = tk.StringVar(value="00")

        ttk.Spinbox(frame, from_=0, to=23, width=3, textvariable=hour_var, format="%02.0f").pack(side="left")
        ttk.Label(frame, text=":").pack(side="left")
        ttk.Spinbox(frame, from_=0, to=59, width=3, textvariable=minute_var, format="%02.0f").pack(side="left")

        def get_value():
            return to_db_datetime(date_var.get(), hour_var.get(), minute_var.get()) or None

        return {"get": get_value}


    # =========================================================
    # OPEN SERVICE SELECTOR POPUP
    # =========================================================
    def _open_service_selector(self):

        PopupGrainServiceSelector(
            self,
            on_select=self._apply_selected_service
        )

    # =========================================================
    # APPLY SELECTED SERVICE DATA TO FORM
    # =========================================================
    def _apply_selected_service(self, data):

        if not data:
            return

        # CERT Nº
        self.cert_no.delete(0, "end")
        self.cert_no.insert(0, data.get("num_informe") or "")

        # PUERTO (AUTO - READONLY)
        puerto = data.get("puerto")
        if puerto:
            self.port_entry.config(state="normal")
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, puerto)
            self.port_entry.config(state="readonly")

        # BUQUE (AUTO - READONLY)
        buque = data.get("buque")
        if buque:
            self.vessel_entry.config(state="normal")
            self.vessel_entry.delete(0, "end")
            self.vessel_entry.insert(0, buque)
            self.vessel_entry.config(state="readonly")

            self.sample_vessel_entry.config(state="normal")
            self.sample_vessel_entry.delete(0, "end")
            self.sample_vessel_entry.insert(0, buque)
            self.sample_vessel_entry.config(state="readonly")

            self.ship_name.config(state="normal")
            self.ship_name.delete(0, "end")
            self.ship_name.insert(0, buque)
            self.ship_name.config(state="readonly")

        # CLIENTE (AUTO - READONLY)
        cliente = data.get("cliente")
        if cliente:
            self.client_entry.config(state="normal")
            self.client_entry.delete(0, "end")
            self.client_entry.insert(0, cliente)
            self.client_entry.config(state="readonly")

            self.sample_client_entry.config(state="normal")
            self.sample_client_entry.delete(0, "end")
            self.sample_client_entry.insert(0, cliente)
            self.sample_client_entry.config(state="readonly")



    def _ask_ai_language(self):

        win = tk.Toplevel(self)
        win.title("PORTIA Language")
        win.geometry("300x150")
        win.transient(self)
        win.grab_set()

        ttk.Label(
            win,
            text="¿En qué idioma desea la mejora del texto?",
            wraplength=250
        ).pack(pady=15)

        result = {"lang": None}

        def select(lang):
            result["lang"] = lang
            win.destroy()

        ttk.Button(win, text="Español", command=lambda: select("ES")).pack(pady=5)
        ttk.Button(win, text="English", command=lambda: select("EN")).pack(pady=5)

        self.wait_window(win)

        return result["lang"]


    # =========================================================
    # MOUSE SCROLL (WHEEL) — UNIVERSAL / ROBUSTO
    # =========================================================
    def _bind_mousewheel(self, canvas):

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_mousewheel_linux_down(event):
            canvas.yview_scroll(1, "units")

        # activar solo cuando el mouse entra al form (clave para Tkinter)
        def _bind(_):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel_linux_up)
            canvas.bind_all("<Button-5>", _on_mousewheel_linux_down)

        def _unbind(_):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        self.form.bind("<Enter>", _bind)
        self.form.bind("<Leave>", _unbind)
