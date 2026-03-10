import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI

from Modulos.Informes.vessel_cargo_condition_survey.popup_ai_maritime_control import PopupAIMaritimeControl
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare

from Modulos.Informes.crane_inspection.popup_ai_crane_inspection_control import PopupAICraneInspectionControl

import api_client


class CraneInspectionForm(ttk.Frame):
    """
    ERP-SOM — Crane Inspection Survey Form (Frontend Only)

    Requerimientos clave:
    - Selector Reporte: MISMA API / MISMO POPUP (Draft selector) y autofill.
    - Home: MISMO comportamiento (volver a InformesHomeUI).
    - Enviar a revisión: se conecta después (queda stub).
    - Improve IA Maritime: integrado (usa PopupAIMaritimeControl + PopupAICompare).
    - Fechas: DateEntry ISO yyyy-mm-dd + al salir del campo -> LONG en inglés.
    - Horas: 2 cuadros (HH / MM).
    - Crane Inspection checklist: checkbox + estado + 3 comentarios por punto.
    - Remarks by Crane: dropdown crane (1..4) + hasta 10 bullets.
    - Recommendations: hasta 10 bullets.
    - Grabs Condition Survey: hasta 10 bullets.
    - Conclusion: hasta 20 bullets.
    - Enclosure: Link Picture (1 campo).
    """

    MAX_REMARKS_BY_CRANE = 10
    MAX_RECOMMENDATIONS = 10
    MAX_GRABS = 10
    MAX_CONCLUSION = 20

    CRANES = ["Crane 1", "Crane 2", "Crane 3", "Crane 4"]

    CRANE_INSPECTION_STATUS_OPTIONS = [
        "",
        "Clean and no obstacles",
        "Clean",
        "Working",
        "Not working",
        "Greased",
        "Negative impressions",
        "Free to rotate / Unreadable scale",
        "No trunnion",
    ]

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        # =====================================================
        # CONTROL DE EDICIÓN
        # =====================================================

        self.record_id = None
        self.is_edit_mode = False

        self.pack(fill="both", expand=True)

        self.vars = {}
        self._bullet_containers = {}   # key -> frame
        self._bullet_lines = {}        # key -> list[tk.Text]

        # Checklist storage
        self.crane_points = []         # list[dict] per point

        self._build_ui()

    # =========================================================
    # VAR HELPER
    # =========================================================
    def _v(self, key):
        if key not in self.vars:
            self.vars[key] = tk.StringVar()
        return self.vars[key]

    def _b(self, key):
        # BooleanVar helper
        if key not in self.vars:
            self.vars[key] = tk.BooleanVar(value=False)
        v = self.vars[key]
        if not isinstance(v, tk.BooleanVar):
            self.vars[key] = tk.BooleanVar(value=False)
        return self.vars[key]

    # =========================================================
    # UI ROOT
    # =========================================================
    def _build_ui(self):

        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(
            topbar,
            text="CRANE INSPECTION SURVEY",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        btn_frame = ttk.Frame(topbar)
        btn_frame.pack(side="right")

        ttk.Button(
            btn_frame,
            text="Seleccionar Reporte",
            command=self._select_service
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="Improve IA Maritime",
            command=self._improve_ai_maritime
        ).pack(side="left", padx=4)

        # =====================================================
        # BOTÓN CREATE
        # =====================================================

        self.btn_submit = ttk.Button(
            btn_frame,
            text="Enviar a Revisión",
            command=self._create_report
        )
        self.btn_submit.pack(side="left", padx=4)

        # =====================================================
        # BOTÓN UPDATE (solo visible en EDIT MODE)
        # =====================================================

        self.btn_update = ttk.Button(
            btn_frame,
            text="Guardar Cambios",
            command=self._update_report
        )

        ttk.Button(
            btn_frame,
            text="Home",
            command=self._go_home
        ).pack(side="left", padx=4)

        # -------------------------
        # Scrollable container
        # -------------------------
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)

        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        # -------------------------
        # Sections
        # -------------------------
        self._build_header_section()
        self._build_introduction_section()
        self._build_cranes_gear_survey_section()
        self._build_crane_inspection_section()
        self._build_remarks_by_crane_section()
        self._build_bullet_section("Recommendations", "recommendations", max_lines=self.MAX_RECOMMENDATIONS)
        self._build_bullet_section("GRABS CONDITION SURVEY", "grabs_condition", max_lines=self.MAX_GRABS)
        self._build_bullet_section("CONCLUSION", "conclusion", max_lines=self.MAX_CONCLUSION)
        self._build_enclosure_section()


    @property
    def recommendations_lines(self):
        return self._bullet_lines.get("recommendations", [])


    @property
    def grabs_condition_lines(self):
        return self._bullet_lines.get("grabs_condition", [])


    @property
    def conclusion_lines(self):
        return self._bullet_lines.get("conclusion", [])


    @property
    def remarks_crane_lines(self):

        merged = []

        for crane in self.CRANES:

            key = f"remarks_{crane}"

            merged.extend(
                self._bullet_lines.get(key, [])
            )

        return merged

        ttk.Label(self.scroll_frame, text="").pack(pady=10)

    # =========================================================
    # DATE/TIME FIELD (ISO + VISUAL LONG)
    #  - Igual que tu patrón actual (DateEntry yyyy-mm-dd + FocusOut => LONG) :contentReference[oaicite:3]{index=3}
    # =========================================================
    def _datetime_field(self, parent, label, key_prefix, row, col):

        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col + 1, sticky="w", padx=5, pady=3)

        date_entry = DateEntry(
            frame,
            textvariable=self._v(f"{key_prefix}_date"),
            width=18,
            locale="en_US",
            date_pattern="yyyy-mm-dd"
        )
        date_entry.pack(side="left")

        date_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long(f"{key_prefix}_date")
        )

        ttk.Entry(
            frame,
            textvariable=self._v(f"{key_prefix}_hour"),
            width=3
        ).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text=":").pack(side="left")

        ttk.Entry(
            frame,
            textvariable=self._v(f"{key_prefix}_minute"),
            width=3
        ).pack(side="left")

    def _format_date_long(self, var_key):
        """
        Convierte ISO yyyy-mm-dd -> 'Month dd, YYYY' al salir del campo.
        Si ya está LONG válido, no toca.
        (Mismo enfoque que ya usas) :contentReference[oaicite:4]{index=4}
        """
        value = (self._v(var_key).get() or "").strip()
        if not value:
            return

        # ISO -> LONG
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            self._v(var_key).set(dt.strftime("%B %d, %Y"))
            return
        except Exception:
            pass

        # Ya LONG válido -> no tocar
        try:
            datetime.strptime(value, "%B %d, %Y")
            return
        except Exception:
            return

    # =========================================================
    # BASIC ENTRIES
    # =========================================================
    def _ro_entry(self, parent, label, key, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=3)
        e = ttk.Entry(parent, textvariable=self._v(key))
        e.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=3)
        e.configure(state="readonly")

    def _entry(self, parent, label, key, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=3)
        e = ttk.Entry(parent, textvariable=self._v(key))
        e.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=3)

    # =========================================================
    # HEADER (Num Informe, Buque, GRT, NRT, Cliente, Puerto, País, Fecha LONG)
    # =========================================================
    def _build_header_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Header")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        self._ro_entry(inner, "Report Number", "report_number", 0, 0)
        self._entry(inner, "Vessel Name", "vessel", 0, 2)

        self._entry(inner, "GRT", "grt", 1, 0)
        self._entry(inner, "NRT", "nrt", 1, 2)

        self._ro_entry(inner, "Client", "client", 2, 0)
        self._ro_entry(inner, "Port", "port", 2, 2)

        self._ro_entry(inner, "Country", "country", 3, 0)
        self._datetime_field(inner, "Report Date", "report", 3, 2)

    # =========================================================
    # INTRODUCTION (Imagen 1)
    #  "On <date>, we were appointed ... in MV <vessel> at <port>, <country>."
    # =========================================================
    def _build_introduction_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Introduction")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        self._datetime_field(inner, "Inspection Date", "intro_inspection", 0, 0)

        # Texto editable final (por si quieres ajustarlo a mano)
        ttk.Label(inner, text="Introduction Text").grid(row=1, column=0, sticky="w", padx=5, pady=3)

        self.intro_text = tk.Text(inner, height=4)
        self.intro_text.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

        # Botón para autogenerar la frase desde campos
        ttk.Button(
            inner,
            text="Auto-fill Introduction",
            command=self._autofill_introduction_text
        ).grid(row=0, column=2, sticky="e", padx=5, pady=3)

    def _autofill_introduction_text(self):

        date_val = self._v("intro_inspection_date").get().strip()
        vessel = self._v("vessel").get().strip()
        port = self._v("port").get().strip()
        country = self._v("country").get().strip()

        # Forzar LONG si viene ISO
        if date_val:
            try:
                dt = datetime.strptime(date_val, "%Y-%m-%d")
                date_val = dt.strftime("%B %d, %Y")
            except Exception:
                pass

        sentence = f"On {date_val or '[DATE]'}, we were appointed to carry out a crane inspection survey in MV {vessel or '[VESSEL]'} at {port or '[PORT]'}, {country or '[COUNTRY]'}."

        self.intro_text.delete("1.0", "end")
        self.intro_text.insert("1.0", sentence)

    # =========================================================
    # CRANES GEAR SURVEY (Imagen 2)
    # =========================================================
    def _build_cranes_gear_survey_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="CRANES GEAR SURVEY")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        # 1) Start date/time and End date/time
        self._datetime_field(inner, "Survey Start (Date/Time)", "gear_start", 0, 0)
        self._datetime_field(inner, "Survey End (Date/Time)", "gear_end", 0, 2)

        # 2) Condition
        ttk.Label(inner, text="2. Condition (shortcomings / notes)").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        self.gear_condition = tk.Text(inner, height=3)
        self.gear_condition.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

        # 3) Hoisting & luffing wires (point 3)
        ttk.Label(inner, text="3. Hoisting & Luffing Wires (found as)").grid(
            row=2, column=0, sticky="w", padx=5, pady=3
        )
        self.gear_wires = tk.Text(inner, height=3)
        self.gear_wires.grid(row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

        # 4) Hoisting & luffing sheaves (point 4)
        ttk.Label(inner, text="4. Hoisting & Luffing Sheaves (impressions)").grid(
            row=3, column=0, sticky="w", padx=5, pady=3
        )
        self.gear_sheaves = tk.Text(inner, height=3)
        self.gear_sheaves.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

        # 5) Operability (point 5)
        ttk.Label(inner, text="5. Operability Inspection (notes)").grid(
            row=4, column=0, sticky="w", padx=5, pady=3
        )
        self.gear_operability = tk.Text(inner, height=3)
        self.gear_operability.grid(row=4, column=1, columnspan=3, sticky="ew", padx=5, pady=3)

    # =========================================================
    # CRANE INSPECTION (Imagen 3 y 4)
    #  - Cada punto: checkbox realizado + estado + 3 comentarios
    # =========================================================
    # =========================================================
    # CRANE INSPECTION (Checklist)
    # =========================================================
    def _build_crane_inspection_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Crane Inspection (Checklist)")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        # Permitir expansión
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)
        inner.columnconfigure(4, weight=1)
        inner.columnconfigure(5, weight=1)

        # -----------------------------------------------------
        # CHECKLIST ITEMS (15 EXACTOS)
        # -----------------------------------------------------

        items = [
            "1. Crane Access",
            "2. Crane machinery space",
            "3. Crane operator cabin",
            "4. Crane jib head sheaves",
            "5. Hoisting wire end pin",
            "6. Luffing wire end pin",
            "7. Crane wire rope visual inspection",

            # NUEVO ITEM
            "8. Crane housing top sheaves",

            "9. Luffing center sheave visual inspection",

            # NUEVO ITEM
            "10. Cargo block sheave shaft",

            "11. Slack hoisting wire limit",
            "12. Crane jib angle limits",
            "13. Crane jib angle indicator",
            "14. Crane hoisting wire limits (upper/slack)",
            "15. Pedestal / Light project",
        ]

        for idx, label in enumerate(items, start=1):
            self._add_crane_check_row(inner, idx, label)

    def _add_crane_check_row(self, parent, row_idx, item_label):

        done_key = f"ci_{row_idx}_done"
        status_key = f"ci_{row_idx}_status"
        s1_key = f"ci_{row_idx}_s1"
        s2_key = f"ci_{row_idx}_s2"
        s3_key = f"ci_{row_idx}_s3"

        chk = ttk.Checkbutton(parent, variable=self._b(done_key))
        chk.grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)

        ttk.Label(parent, text=item_label).grid(row=row_idx, column=1, sticky="w", padx=5, pady=2)

        ttk.Combobox(
            parent,
            textvariable=self._v(status_key),
            values=self.CRANE_INSPECTION_STATUS_OPTIONS,
            state="readonly",
            width=24
        ).grid(row=row_idx, column=2, sticky="w", padx=5, pady=2)

        ttk.Combobox(
            parent,
            textvariable=self._v(s1_key),
            values=self.CRANE_INSPECTION_STATUS_OPTIONS,
            state="readonly",
            width=20
        ).grid(row=row_idx, column=3, sticky="ew", padx=5, pady=2)

        ttk.Combobox(
            parent,
            textvariable=self._v(s2_key),
            values=self.CRANE_INSPECTION_STATUS_OPTIONS,
            state="readonly",
            width=20
        ).grid(row=row_idx, column=4, sticky="ew", padx=5, pady=2)

        ttk.Combobox(
            parent,
            textvariable=self._v(s3_key),
            values=self.CRANE_INSPECTION_STATUS_OPTIONS,
            state="readonly",
            width=20
        ).grid(row=row_idx, column=5, sticky="ew", padx=5, pady=2)

        self.crane_points.append({
            "done_key": done_key,
            "status_key": status_key,
            "s1_key": s1_key,
            "s2_key": s2_key,
            "s3_key": s3_key,
            "label": item_label
        })

    # =========================================================
    # REMARKS BY CRANE (Imagen 5)
    #  - Dropdown crane + bullets hasta 10
    # =========================================================
    def _build_remarks_by_crane_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="REMARKS BY CRANE")
        box.pack(fill="x", pady=(0, 10))

        self.remarks_blocks = {}

        for crane in self.CRANES:

            crane_box = ttk.LabelFrame(box, text=crane)
            crane_box.pack(fill="x", padx=10, pady=8)

            toolbar = ttk.Frame(crane_box)
            toolbar.pack(fill="x")

            ttk.Label(toolbar, text="Comments").pack(side="left")

            ttk.Button(
                toolbar,
                text="+",
                width=3,
                command=lambda c=crane: self._add_crane_remark(c)
            ).pack(side="right")

            container = ttk.Frame(crane_box)
            container.pack(fill="x", pady=5)

            self._bullet_containers[f"remarks_{crane}"] = container
            self._bullet_lines[f"remarks_{crane}"] = []

            self._add_crane_remark(crane)


    # =========================================================
    # ADD CRANE REMARK (SAFE)
    # =========================================================
    def _add_crane_remark(self, crane):

        key = f"remarks_{crane}"

        container = self._bullet_containers.get(key)

        if container is None:
            return

        self._bullet_containers.setdefault(key, container)

        # asegurar lista
        if key not in self._bullet_lines:
            self._bullet_lines[key] = []

        lines = self._bullet_lines[key]

        if len(lines) >= self.MAX_REMARKS_BY_CRANE:

            messagebox.showwarning(
                "Limit",
                f"Maximum {self.MAX_REMARKS_BY_CRANE} comments per crane."
            )

            return

        frame = ttk.Frame(container)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text="•").pack(side="left", padx=(0, 5))

        txt = tk.Text(frame, height=3, width=110)
        txt.pack(side="left", fill="x", expand=True)

        lines.append(txt)




    # =========================================================
    # BULLET SECTION
    # =========================================================
    def _build_bullet_section(self, title, key_prefix, max_lines=10):

        box = ttk.LabelFrame(self.scroll_frame, text=title)
        box.pack(fill="x", pady=(0, 10))

        toolbar = ttk.Frame(box)
        toolbar.pack(fill="x", padx=10, pady=(5, 0))

        ttk.Button(
            toolbar,
            text="+",
            width=3,
            command=lambda: self._add_bullet_line(
                key_prefix,
                max_lines=max_lines
            )
        ).pack(side="right")

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        # registrar container
        self._bullet_containers[key_prefix] = container

        # inicializar lista
        self._bullet_lines[key_prefix] = []

        # crear primera línea
        self._add_bullet_line(
            key_prefix,
            max_lines=max_lines
        )

    # =========================================================
    # ADD BULLET LINE (SAFE)
    # =========================================================
    def _add_bullet_line(self, key_prefix, max_lines=10, container_override=None, height=4):

        container = container_override or self._bullet_containers.get(key_prefix)

        if container is None:
            return

        # asegurar registro
        self._bullet_containers.setdefault(key_prefix, container)

        # asegurar lista
        if key_prefix not in self._bullet_lines:
            self._bullet_lines[key_prefix] = []

        lines = self._bullet_lines[key_prefix]

        if max_lines is not None and len(lines) >= max_lines:
            messagebox.showwarning(
                "Limit",
                f"Maximum {max_lines} bullet points in this section."
            )
            return

        frame = ttk.Frame(container)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text="•").pack(side="left", padx=(0, 5))

        txt = tk.Text(frame, height=height, width=110)
        txt.pack(side="left", fill="x", expand=True)

        lines.append(txt)

    # =========================================================
    # ENCLOSURE (Link Picture)
    # =========================================================
    def _build_enclosure_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="ENCLOSURE (Link Picture)")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        inner.columnconfigure(1, weight=1)

        ttk.Label(inner, text="Link Picture:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(inner, textvariable=self._v("link_picture")).grid(row=0, column=1, sticky="ew", padx=5, pady=3)

    # =========================================================
    # SELECT SERVICE (MISMO POPUP / MISMA API) + AUTOFILL
    #  - Igual patrón que tu form actual :contentReference[oaicite:6]{index=6}
    # =========================================================
    def _select_service(self):

        PopupServicioDraftSelector(
            self.parent,
            on_select=self._on_service_selected
        )

    def _on_service_selected(self, values):

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

        # Header core
        self._v("report_number").set(num_informe or "")
        self._v("vessel").set(buque or "")
        self._v("client").set(cliente or "")
        self._v("country").set(pais or "")
        self._v("port").set(puerto or "")

        # Fecha del servicio como base (si quieres)
        if fecha_inicio:
            try:
                if isinstance(fecha_inicio, datetime):
                    self._v("report_date").set(fecha_inicio.strftime("%Y-%m-%d"))
                else:
                    self._v("report_date").set(str(fecha_inicio))
            except Exception:
                self._v("report_date").set(str(fecha_inicio))
        else:
            self._v("report_date").set("")

        # Forzar LONG visual al salir (si ya está ISO)
        self._format_date_long("report_date")

        # Sugerencia: autopoblar intro inspection date si viene vacía
        if not (self._v("intro_inspection_date").get() or "").strip():
            self._v("intro_inspection_date").set(self._v("report_date").get() or "")

        # Autogenerar introduction sentence
        self._autofill_introduction_text()

    # =========================================================
    # IA BUTTON (CRANE INSPECTION POPUP)
    # =========================================================
    def _improve_ai_maritime(self):

        PopupAICraneInspectionControl(
            parent=self,
            form_instance=self,
            on_execute=self._execute_ai_improvement
        )


    def _execute_ai_improvement(self, section, language, items):
        """
        Frontend-only: intenta usar un endpoint específico si existe.
        Si aún no existe en api_client, muestra error claro (sin romper).
        """

        vessel = self._v("vessel").get()
        port = self._v("port").get()

        fn = getattr(api_client, "improve_crane_inspection_ai_api", None)
        if not callable(fn):
            messagebox.showerror(
                "IA Maritime",
                "No existe api_client.improve_crane_inspection_ai_api aún. (Lo conectamos cuando esté listo el endpoint)."
            )
            return

        response = fn(
            section=section,
            language=language,
            vessel=vessel,
            port=port,
            items=items
        )

        if not response.get("success"):
            messagebox.showerror("IA Maritime", response.get("error") or "AI processing failed.")
            return

        ai_items = response.get("items")
        if not ai_items:
            messagebox.showerror("IA Maritime", "AI returned empty response.")
            return

        PopupAICompare(
            parent=self,
            original_text="\n\n".join(items),
            ai_text="\n\n".join(ai_items),
            on_accept=lambda new_text: self._apply_ai_text(section, new_text),
            on_retry=lambda: self._execute_ai_improvement(section, language, items)
        )

    def _apply_ai_text(self, section, new_text):
        """
        Aplica el texto generado por IA a las secciones de bullets.

        Soporta:
        - Recommendations
        - Grabs Condition Survey
        - Conclusion
        - Remarks by Crane (fusionando todas las grúas)

        El texto se espera separado por doble salto de línea.
        """

        try:

            # -------------------------------------------------
            # PARSE BULLETS
            # -------------------------------------------------

            parsed = [
                b.strip()
                for b in (new_text or "").split("\n\n")
                if b.strip()
            ]

            if not parsed:
                messagebox.showwarning(
                    "IA Maritime",
                    "AI returned empty content."
                )
                return

            # -------------------------------------------------
            # SECTION MAP
            # -------------------------------------------------

            section_map = {
                "Recommendations": "recommendations",
                "RECOMMENDATIONS": "recommendations",

                "Grabs Condition Survey": "grabs_condition",
                "GRABS CONDITION SURVEY": "grabs_condition",

                "Conclusion": "conclusion",
                "CONCLUSION": "conclusion",

                "Remarks by Crane": "remarks_crane",
                "REMARKS BY CRANE": "remarks_crane",
            }

            key = section_map.get(section, section)

            # -------------------------------------------------
            # SELECT TARGET LINES
            # -------------------------------------------------

            if key == "remarks_crane":

                lines = self.remarks_crane_lines

                max_lines = (
                    self.MAX_REMARKS_BY_CRANE * len(self.CRANES)
                )

            else:

                if key not in self._bullet_lines:

                    messagebox.showwarning(
                        "IA Maritime",
                        f"Unsupported section: {section}"
                    )
                    return

                lines = self._bullet_lines.get(key, [])

                max_map = {
                    "recommendations": self.MAX_RECOMMENDATIONS,
                    "grabs_condition": self.MAX_GRABS,
                    "conclusion": self.MAX_CONCLUSION
                }

                max_lines = max_map.get(key, 10)

            # -------------------------------------------------
            # CLEAR EXISTING CONTENT
            # -------------------------------------------------

            for txt in lines:
                try:
                    txt.delete("1.0", "end")
                except Exception:
                    pass

            # -------------------------------------------------
            # ENSURE ENOUGH BULLET LINES
            # -------------------------------------------------

            if key != "remarks_crane":

                while len(lines) < len(parsed) and len(lines) < max_lines:

                    self._add_bullet_line(
                        key,
                        max_lines=max_lines
                    )

                    lines = self._bullet_lines.get(key, [])

            # -------------------------------------------------
            # INSERT TEXT
            # -------------------------------------------------

            for i, block in enumerate(parsed):

                if i >= len(lines):
                    break

                try:
                    lines[i].delete("1.0", "end")
                    lines[i].insert("1.0", block)
                except Exception:
                    pass

        except Exception as e:

            messagebox.showerror(
                "IA Maritime",
                str(e)
            )



    # =========================================================
    # BUILD PAYLOAD (FULL 1:1 WITH DB)
    # =========================================================
    def _build_payload(self):

        try:

            payload = {}

            # ==================================================
            # VALIDATION
            # ==================================================

            if not self._v("report_number").get().strip():
                raise Exception("Report Number is required.")

            # ==================================================
            # STATUS
            # ==================================================

            payload["status"] = "Pending for review"

            # ==================================================
            # HEADER
            # ==================================================

            payload["report_number"] = self._v("report_number").get()
            payload["vessel"] = self._v("vessel").get()
            payload["client"] = self._v("client").get()
            payload["port"] = self._v("port").get()
            payload["country"] = self._v("country").get()

            payload["report_date"] = self._normalize_date(
                self._v("report_date").get()
            )

            payload["grt"] = self._v("grt").get()
            payload["nrt"] = self._v("nrt").get()

            # ==================================================
            # INTRODUCTION
            # ==================================================

            payload["intro_text"] = self.intro_text.get("1.0", "end").strip()

            payload["intro_inspection_date"] = self._normalize_date(
                self._v("intro_inspection_date").get()
            )

            payload["intro_inspection_hour"] = self._v(
                "intro_inspection_hour"
            ).get()

            payload["intro_inspection_minute"] = self._v(
                "intro_inspection_minute"
            ).get()

            # ==================================================
            # CRANES GEAR SURVEY
            # ==================================================

            payload["gear_condition"] = self.gear_condition.get("1.0", "end").strip()
            payload["gear_wires"] = self.gear_wires.get("1.0", "end").strip()
            payload["gear_sheaves"] = self.gear_sheaves.get("1.0", "end").strip()
            payload["gear_operability"] = self.gear_operability.get("1.0", "end").strip()

            payload["gear_start_date"] = self._normalize_date(
                self._v("gear_start_date").get()
            )

            payload["gear_start_hour"] = self._v("gear_start_hour").get()
            payload["gear_start_minute"] = self._v("gear_start_minute").get()

            payload["gear_end_date"] = self._normalize_date(
                self._v("gear_end_date").get()
            )

            payload["gear_end_hour"] = self._v("gear_end_hour").get()
            payload["gear_end_minute"] = self._v("gear_end_minute").get()

            # ==================================================
            # CRANE CHECKLIST (15 ITEMS EXACTLY AS DB)
            # ==================================================

            checklist_map = [
                "crane_access",
                "crane_machinery_space",
                "crane_operator_cabin",
                "crane_jib_head_sheaves",
                "hoisting_wire_end_pin",
                "luffing_wire_end_pin",
                "crane_wire_visual",
                "crane_housing_sheaves",
                "luffing_center_sheave",
                "cargo_block_sheave",
                "slack_hoisting_limit",
                "crane_jib_angle_limits",
                "crane_jib_angle_indicator",
                "crane_hoisting_limits",
                "pedestal_light_project"
            ]

            for point, prefix in zip(self.crane_points, checklist_map):

                payload[f"{prefix}_done"] = bool(
                    self._b(point["done_key"]).get()
                )

                payload[f"{prefix}_status"] = self._v(
                    point["status_key"]
                ).get()

                payload[f"{prefix}_status1"] = self._v(
                    point["s1_key"]
                ).get()

                payload[f"{prefix}_status2"] = self._v(
                    point["s2_key"]
                ).get()

                payload[f"{prefix}_status3"] = self._v(
                    point["s3_key"]
                ).get()

            # ==================================================
            # REMARKS BY CRANE (4 CRANES × 10)
            # ==================================================

            for crane in self.CRANES:

                key = f"remarks_{crane}"
                lines = self._bullet_lines.get(key, [])

                crane_num = crane.split()[-1]

                for i in range(10):

                    value = ""

                    if i < len(lines):
                        value = lines[i].get("1.0", "end").strip()

                    payload[f"crane{crane_num}_remark_{i+1}"] = value

            # ==================================================
            # RECOMMENDATIONS (10)
            # ==================================================

            rec_lines = self._bullet_lines.get("recommendations", [])

            for i in range(10):

                value = ""

                if i < len(rec_lines):
                    value = rec_lines[i].get("1.0", "end").strip()

                payload[f"recommendation_{i+1}"] = value

            # ==================================================
            # GRABS CONDITION SURVEY (10)
            # ==================================================

            grab_lines = self._bullet_lines.get("grabs_condition", [])

            for i in range(10):

                value = ""

                if i < len(grab_lines):
                    value = grab_lines[i].get("1.0", "end").strip()

                payload[f"grabs_condition_{i+1}"] = value

            # ==================================================
            # CONCLUSION (20)
            # ==================================================

            conclusion_lines = self._bullet_lines.get("conclusion", [])

            for i in range(20):

                value = ""

                if i < len(conclusion_lines):
                    value = conclusion_lines[i].get("1.0", "end").strip()

                payload[f"conclusion_{i+1}"] = value

            # ==================================================
            # ENCLOSURE
            # ==================================================

            payload["link_picture"] = self._v("link_picture").get()

            return payload

        except Exception as e:

            messagebox.showerror(
                "Unexpected Error",
                str(e)
            )

            return None


    def _normalize_date(self, value):

        value = (value or "").strip()

        if not value:
            return None

        try:
            dt = datetime.strptime(value, "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return value

    # =====================================================
    # LOAD RECORD (REVIEW MODE)
    # =====================================================
    def load_record(self, data):

        try:

            if not isinstance(data, dict):
                return

            # =====================================================
            # NORMALIZE API RESPONSE
            # =====================================================

            if "data" in data and isinstance(data["data"], dict):
                data = data["data"]

            try:
                self.update_idletasks()
            except Exception:
                pass

            # =====================================================
            # EDIT MODE
            # =====================================================

            self.record_id = data.get("id")
            self.is_edit_mode = True

            try:

                if hasattr(self, "btn_submit"):
                    self.btn_submit.pack_forget()

                if hasattr(self, "btn_update"):
                    self.btn_update.pack(side="left", padx=4)

            except Exception:
                pass

            # =====================================================
            # HEADER
            # =====================================================

            self._v("report_number").set(str(data.get("report_number") or ""))
            self._v("vessel").set(str(data.get("vessel") or ""))
            self._v("client").set(str(data.get("client") or ""))
            self._v("port").set(str(data.get("port") or ""))
            self._v("country").set(str(data.get("country") or ""))

            self._v("grt").set(str(data.get("grt") or ""))
            self._v("nrt").set(str(data.get("nrt") or ""))

            report_date = data.get("report_date")

            if report_date:
                self._v("report_date").set(str(report_date))
                try:
                    self._format_date_long("report_date")
                except Exception:
                    pass

            # =====================================================
            # INTRO TEXT
            # =====================================================

            try:

                if hasattr(self, "intro_text"):
                    self.intro_text.delete("1.0", "end")
                    self.intro_text.insert(
                        "1.0",
                        str(data.get("intro_text") or "")
                    )

            except Exception:
                pass

            self._v("intro_inspection_date").set(str(data.get("intro_inspection_date") or ""))
            self._v("intro_inspection_hour").set(str(data.get("intro_inspection_hour") or ""))
            self._v("intro_inspection_minute").set(str(data.get("intro_inspection_minute") or ""))

            # =====================================================
            # GEAR SURVEY
            # =====================================================

            self._v("gear_start_date").set(str(data.get("gear_start_date") or ""))
            self._v("gear_start_hour").set(str(data.get("gear_start_hour") or ""))
            self._v("gear_start_minute").set(str(data.get("gear_start_minute") or ""))

            self._v("gear_end_date").set(str(data.get("gear_end_date") or ""))
            self._v("gear_end_hour").set(str(data.get("gear_end_hour") or ""))
            self._v("gear_end_minute").set(str(data.get("gear_end_minute") or ""))

            try:

                self.gear_condition.delete("1.0", "end")
                self.gear_condition.insert("1.0", str(data.get("gear_condition") or ""))

                self.gear_wires.delete("1.0", "end")
                self.gear_wires.insert("1.0", str(data.get("gear_wires") or ""))

                self.gear_sheaves.delete("1.0", "end")
                self.gear_sheaves.insert("1.0", str(data.get("gear_sheaves") or ""))

                self.gear_operability.delete("1.0", "end")
                self.gear_operability.insert("1.0", str(data.get("gear_operability") or ""))

            except Exception:
                pass

            # =====================================================
            # CHECKLIST
            # =====================================================

            checklist_map = [
                "crane_access",
                "crane_machinery_space",
                "crane_operator_cabin",
                "crane_jib_head_sheaves",
                "hoisting_wire_end_pin",
                "luffing_wire_end_pin",
                "crane_wire_visual",
                "crane_housing_sheaves",
                "luffing_center_sheave",
                "cargo_block_sheave",
                "slack_hoisting_limit",
                "crane_jib_angle_limits",
                "crane_jib_angle_indicator",
                "crane_hoisting_limits",
                "pedestal_light_project"
            ]

            for i, point in enumerate(self.crane_points):

                if i >= len(checklist_map):
                    break

                prefix = checklist_map[i]

                try:
                    self._b(point["done_key"]).set(bool(data.get(f"{prefix}_done")))
                except Exception:
                    pass

                try:
                    self._v(point["status_key"]).set(str(data.get(f"{prefix}_status") or ""))
                    self._v(point["s1_key"]).set(str(data.get(f"{prefix}_status1") or ""))
                    self._v(point["s2_key"]).set(str(data.get(f"{prefix}_status2") or ""))
                    self._v(point["s3_key"]).set(str(data.get(f"{prefix}_status3") or ""))
                except Exception:
                    pass

            # =====================================================
            # RESET BULLETS (SAFE RESET)
            # =====================================================

            for key in list(self._bullet_containers.keys()):

                container = self._bullet_containers.get(key)

                if not container:
                    continue

                try:

                    for widget in container.winfo_children():
                        widget.destroy()

                except Exception:
                    pass

                # reset line registry
                self._bullet_lines[key] = []

            # =====================================================
            # SAFE BULLET LOADER
            # =====================================================

            def _load_section(prefix, key, max_lines):

                container = self._bullet_containers.get(key)

                if not container:
                    return

                values = []

                for i in range(1, max_lines + 1):

                    v = data.get(f"{prefix}_{i}")

                    if v is None:
                        continue

                    v = str(v).strip()

                    if not v:
                        continue

                    values.append(v)

                # si no hay valores, crear 1 línea vacía
                if not values:

                    self._add_bullet_line(
                        key,
                        max_lines=max_lines
                    )

                    return

                # reconstruir líneas
                for v in values:

                    self._add_bullet_line(
                        key,
                        max_lines=max_lines
                    )

                    txt = self._bullet_lines[key][-1]

                    txt.delete("1.0", "end")
                    txt.insert("1.0", v)

            # =====================================================
            # REMARKS BY CRANE
            # =====================================================

            for crane in self.CRANES:

                crane_num = crane.split()[-1]
                key = f"remarks_{crane}"

                values = []

                for i in range(1, self.MAX_REMARKS_BY_CRANE + 1):

                    v = data.get(f"crane{crane_num}_remark_{i}")

                    if v:
                        values.append(str(v))

                if not values:
                    self._add_crane_remark(crane)
                    continue

                for v in values:

                    self._add_crane_remark(crane)

                    txt = self._bullet_lines[key][-1]

                    txt.delete("1.0", "end")
                    txt.insert("1.0", v)

            # =====================================================
            # BULLET SECTIONS
            # =====================================================

            _load_section("recommendation", "recommendations", self.MAX_RECOMMENDATIONS)
            _load_section("grabs_condition", "grabs_condition", self.MAX_GRABS)
            _load_section("conclusion", "conclusion", self.MAX_CONCLUSION)

            # =====================================================
            # ENCLOSURE
            # =====================================================

            try:
                self._v("link_picture").set(str(data.get("link_picture") or ""))
            except Exception:
                pass

        except Exception as e:

            try:
                messagebox.showerror("Load Record Error", str(e))
            except Exception:
                pass

    # =========================================================
    # UPDATE REPORT
    # =========================================================
    def _update_report(self):

        try:

            if not self.record_id:
                messagebox.showerror(
                    "Update Error",
                    "No record ID loaded."
                )
                return

            payload = self._build_payload()

            response = api_client.update_crane_inspection_api(
                self.record_id,
                payload
            )

            if not response.get("success"):
                messagebox.showerror(
                    "Error",
                    response.get("error") or "Failed to update report"
                )
                return

            messagebox.showinfo(
                "Success",
                "Crane Inspection report updated successfully."
            )

        except Exception as e:
            messagebox.showerror("Unexpected Error", str(e))


    # =========================================================
    # CREATE REPORT
    # =========================================================
    def _create_report(self):

        try:

            payload = self._build_payload()

            if not isinstance(payload, dict):
                return

            response = api_client.create_crane_inspection_api(
                payload
            )

            if not response.get("success"):

                messagebox.showerror(
                    "Error",
                    response.get("error") or "Failed to create report"
                )
                return

            report_id = response.get("id")

            messagebox.showinfo(
                "Success",
                f"Crane Inspection report created successfully.\n\nID: {report_id}"
            )

            # después de crear puede pasar a modo edición
            try:
                if report_id:
                    self.record_id = report_id
                    self.is_edit_mode = True

                    if hasattr(self, "btn_submit"):
                        self.btn_submit.pack_forget()

                    if hasattr(self, "btn_update"):
                        self.btn_update.pack(side="left", padx=4)

            except Exception:
                pass

        except Exception as e:

            messagebox.showerror(
                "Unexpected Error",
                str(e)
            )



    # =========================================================
    # HOME
    # =========================================================
    def _go_home(self):
        try:
            self.destroy()
            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )
        except Exception as e:
            messagebox.showerror("Home", str(e))