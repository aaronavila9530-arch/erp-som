import csv
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    hr_medical_network_filters_api,
    hr_medical_network_search_api,
)


class VistaRedMedicaHHRR(ttk.Frame):
    def __init__(self, parent, usuario=None, rol=None):
        super().__init__(parent)
        self.usuario = usuario
        self.rol = rol
        self.filters = {}
        self.rows = []
        self.current_row = None
        self._sort_state = {}
        self._loading_filters = False
        self._build_ui()
        self._load_filters()
        self._buscar()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self._build_styles()

        header = ttk.Frame(self, style="Medical.Surface.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Red medica", style="Medical.Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Encuentra profesionales por ubicacion, especialidad, tipo de atencion, centro o nombre.",
            style="Medical.Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        actions = ttk.Frame(header)
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(actions, text="Copiar detalle", command=self._copiar_detalle).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Exportar resultado", command=self._exportar).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Actualizar", command=self._refresh).pack(side="left")

        self._build_kpis()
        self._build_filters()
        self._build_quick_bar()
        self._build_body()

    def _build_styles(self):
        style = ttk.Style(self)
        style.configure("Medical.Title.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Medical.KpiTitle.TLabel", font=("Segoe UI", 8), foreground="#475467")
        style.configure("Medical.KpiValue.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0f4c81")
        style.configure("Medical.Muted.TLabel", foreground="#475467")
        style.configure("Medical.DetailTitle.TLabel", font=("Segoe UI", 12, "bold"), foreground="#0f4c81")
        style.configure("Medical.DetailValue.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Medical.Surface.TFrame", background="#f5f7fb")

    def _build_kpis(self):
        bar = ttk.Frame(self)
        bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 8))
        for col in range(5):
            bar.columnconfigure(col, weight=1)
        self.kpi_total = tk.StringVar(value="0")
        self.kpi_visible = tk.StringVar(value="0")
        self.kpi_professionals = tk.StringVar(value="0")
        self.kpi_specialties = tk.StringVar(value="0")
        self.kpi_provinces = tk.StringVar(value="0")
        for col, title, var in (
            (0, "Registros red", self.kpi_total),
            (1, "Resultado visible", self.kpi_visible),
            (2, "Profesionales", self.kpi_professionals),
            (3, "Especialidades", self.kpi_specialties),
            (4, "Provincias", self.kpi_provinces),
        ):
            self._kpi_card(bar, col, title, var)

    def _kpi_card(self, parent, col, title, variable):
        frame = ttk.LabelFrame(parent, text=title)
        frame.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0), ipady=4)
        ttk.Label(frame, textvariable=variable, style="Medical.KpiValue.TLabel").pack(anchor="w", padx=10, pady=(2, 2))

    def _build_filters(self):
        filters = ttk.LabelFrame(self, text="Filtros")
        filters.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))
        for col in range(10):
            filters.columnconfigure(col, weight=1)

        self.q_var = tk.StringVar()
        self.province_var = tk.StringVar()
        self.canton_var = tk.StringVar()
        self.district_var = tk.StringVar()
        self.specialty_var = tk.StringVar()
        self.consultation_var = tk.StringVar()
        self.service_var = tk.StringVar()
        self.clinic_var = tk.StringVar()

        ttk.Label(filters, text="Busqueda libre").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        search = ttk.Entry(filters, textvariable=self.q_var)
        search.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        search.bind("<Return>", lambda _e: self._buscar())
        search.bind("<KeyRelease>", self._schedule_search)

        self.cbo_province = self._combo(filters, "Provincia", self.province_var, 2)
        self.cbo_canton = self._combo(filters, "Canton", self.canton_var, 3)
        self.cbo_district = self._combo(filters, "Distrito", self.district_var, 4)
        self.cbo_specialty = self._combo(filters, "Especialidad", self.specialty_var, 5, width=28)
        self.cbo_consultation = self._combo(filters, "Consulta", self.consultation_var, 6)
        self.cbo_service = self._combo(filters, "Servicio", self.service_var, 7)

        ttk.Label(filters, text="Centro / lugar").grid(row=2, column=0, sticky="w", padx=8, pady=(2, 2))
        self.cbo_clinic = ttk.Combobox(filters, textvariable=self.clinic_var, state="readonly", width=38)
        self.cbo_clinic.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 10))
        self.cbo_clinic.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Button(filters, text="Buscar", command=self._buscar).grid(row=3, column=5, sticky="ew", padx=8, pady=(0, 10))
        ttk.Button(filters, text="Limpiar", command=self._limpiar).grid(row=3, column=6, sticky="ew", padx=8, pady=(0, 10))
        ttk.Button(filters, text="Ver todo", command=self._ver_todo).grid(row=3, column=7, sticky="ew", padx=8, pady=(0, 10))

    def _build_quick_bar(self):
        quick = ttk.Frame(self)
        quick.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))
        ttk.Label(quick, text="Accesos rapidos:", style="Medical.Muted.TLabel").pack(side="left", padx=(0, 8))
        for text, cmd in (
            ("Medicina General", lambda: self._quick_specialty("Medicina General")),
            ("Odontologia", lambda: self._quick_specialty("Odontologia")),
            ("Psicologia", lambda: self._quick_specialty("Psicologia")),
            ("Virtual", lambda: self._quick_consulta("Presencial y Virtual")),
            ("San Jose", lambda: self._quick_province("SAN JOSE")),
            ("Alajuela", lambda: self._quick_province("ALAJUELA")),
        ):
            ttk.Button(quick, text=text, command=cmd).pack(side="left", padx=(0, 5))
        self.result_var = tk.StringVar(value="")
        ttk.Label(quick, textvariable=self.result_var, font=("Segoe UI", 10, "bold")).pack(side="right")

    def _build_body(self):
        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=4, column=0, sticky="nsew", padx=14, pady=(0, 12))

        table_frame = ttk.Frame(body)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        body.add(table_frame, weight=4)

        columns = (
            "tasacion_id",
            "professional_name",
            "specialty",
            "consultation_type",
            "service_type",
            "clinic_name",
            "province",
            "canton",
            "district",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=24)
        headings = {
            "tasacion_id": "ID",
            "professional_name": "Medico / profesional",
            "specialty": "Especialidad",
            "consultation_type": "Consulta",
            "service_type": "Servicio",
            "clinic_name": "Lugar / consultorio",
            "province": "Provincia",
            "canton": "Canton",
            "district": "Distrito",
        }
        widths = {
            "tasacion_id": 90,
            "professional_name": 240,
            "specialty": 170,
            "consultation_type": 130,
            "service_type": 130,
            "clinic_name": 260,
            "province": 105,
            "canton": 120,
            "district": 120,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=widths[col], anchor="w", stretch=True)
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.tag_configure("even", background="#eef7f2")
        self.tree.tag_configure("virtual", foreground="#0f766e")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._detalle)

        detail = ttk.LabelFrame(body, text="Detalle seleccionado")
        detail.columnconfigure(0, weight=1)
        body.add(detail, weight=1)

        self.detail_title = tk.StringVar(value="Selecciona un profesional")
        self.detail_body = tk.StringVar(value="Aqui veras especialidad, centro, modalidad y ubicacion completa.")
        ttk.Label(detail, textvariable=self.detail_title, style="Medical.DetailTitle.TLabel", wraplength=330).grid(
            row=0, column=0, sticky="ew", padx=12, pady=(12, 8)
        )
        ttk.Label(detail, textvariable=self.detail_body, justify="left", wraplength=330).grid(
            row=1, column=0, sticky="nsew", padx=12, pady=(0, 12)
        )
        ttk.Button(detail, text="Copiar detalle", command=self._copiar_detalle).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        ttk.Button(detail, text="Filtrar por esta especialidad", command=self._filter_selected_specialty).grid(
            row=3, column=0, sticky="ew", padx=12, pady=(0, 8)
        )
        ttk.Button(detail, text="Filtrar por esta ubicacion", command=self._filter_selected_location).grid(
            row=4, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

    def _combo(self, parent, label, variable, col, width=20):
        ttk.Label(parent, text=label).grid(row=0, column=col, sticky="w", padx=8, pady=(8, 2))
        combo = ttk.Combobox(parent, textvariable=variable, state="readonly", width=width)
        combo.grid(row=1, column=col, sticky="ew", padx=8, pady=(0, 8))
        combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        return combo

    def _values(self, key):
        values = sorted({str(v).strip() for v in (self.filters.get(key) or []) if str(v or "").strip()})
        return [""] + values

    def _load_filters(self, cascade=False):
        try:
            self._loading_filters = True
            self.filters = hr_medical_network_filters_api(**(self._filter_scope() if cascade else {}))
            summary = self.filters.get("summary") or {}
            self.kpi_total.set(f"{int(summary.get('total') or 0):,}")
            self.kpi_professionals.set(f"{int(summary.get('professionals') or 0):,}")
            self.kpi_specialties.set(f"{int(summary.get('specialties') or 0):,}")
            self.kpi_provinces.set(f"{int(summary.get('provinces') or 0):,}")
            self._set_combo_values(self.cbo_province, self.province_var, "provinces")
            self._set_combo_values(self.cbo_canton, self.canton_var, "cantons")
            self._set_combo_values(self.cbo_district, self.district_var, "districts")
            self._set_combo_values(self.cbo_specialty, self.specialty_var, "specialties")
            self._set_combo_values(self.cbo_consultation, self.consultation_var, "consultation_types")
            self._set_combo_values(self.cbo_service, self.service_var, "service_types")
            self._set_combo_values(self.cbo_clinic, self.clinic_var, "clinics")
        except Exception as exc:
            messagebox.showerror("Red medica", f"No se pudieron cargar filtros:\n{exc}")
        finally:
            self._loading_filters = False

    def _set_combo_values(self, combo, variable, key):
        values = self._values(key)
        combo.config(values=values)
        if variable.get().strip() and variable.get().strip() not in values:
            variable.set("")

    def _filter_scope(self):
        data = {
            "q": self.q_var.get().strip(),
            "province": self.province_var.get().strip(),
            "canton": self.canton_var.get().strip(),
            "district": self.district_var.get().strip(),
            "specialty": self.specialty_var.get().strip(),
            "consultation_type": self.consultation_var.get().strip(),
            "service_type": self.service_var.get().strip(),
            "clinic": self.clinic_var.get().strip(),
        }
        return {key: value for key, value in data.items() if value not in ("", None)}

    def _params(self, page_size=400):
        data = {
            "q": self.q_var.get().strip(),
            "province": self.province_var.get().strip(),
            "canton": self.canton_var.get().strip(),
            "district": self.district_var.get().strip(),
            "specialty": self.specialty_var.get().strip(),
            "consultation_type": self.consultation_var.get().strip(),
            "service_type": self.service_var.get().strip(),
            "clinic": self.clinic_var.get().strip(),
            "page": 1,
            "page_size": page_size,
        }
        return {key: value for key, value in data.items() if value not in ("", None)}

    def _schedule_search(self, _event=None):
        if hasattr(self, "_search_after"):
            self.after_cancel(self._search_after)
        self._search_after = self.after(350, self._cascade_and_search)

    def _on_filter_changed(self, _event=None):
        if self._loading_filters:
            return
        self._cascade_and_search()

    def _cascade_and_search(self):
        self._load_filters(cascade=True)
        self._buscar()

    def _buscar(self):
        try:
            data = hr_medical_network_search_api(**self._params())
            self.rows = data.get("data") or []
            total = int(data.get("total") or 0)
            self._render_rows()
            visible = len(self.rows)
            extra = " | mostrando primeros 400" if total > visible else ""
            self.result_var.set(f"{total:,} resultados{extra}")
            self.kpi_visible.set(f"{total:,}")
            if self.rows:
                first = self.tree.get_children()[0]
                self.tree.selection_set(first)
                self.tree.focus(first)
                self._on_select()
            else:
                self.current_row = None
                self.detail_title.set("Sin resultados")
                self.detail_body.set("Ajusta filtros o limpia la busqueda para ampliar la red disponible.")
        except Exception as exc:
            messagebox.showerror("Red medica", f"No se pudo buscar:\n{exc}")

    def _render_rows(self):
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.rows):
            tags = ["even" if idx % 2 == 0 else "odd"]
            if "virtual" in str(row.get("consultation_type") or "").lower():
                tags.append("virtual")
            self.tree.insert("", "end", iid=str(row.get("id")), tags=tuple(tags), values=(
                row.get("tasacion_id") or "",
                row.get("professional_name") or "",
                row.get("specialty") or "",
                row.get("consultation_type") or "",
                row.get("service_type") or "",
                row.get("clinic_name") or "",
                row.get("province") or "",
                row.get("canton") or "",
                row.get("district") or "",
            ))

    def _row_text(self, row):
        if not row:
            return ""
        return (
            f"Profesional: {row.get('professional_name') or ''}\n"
            f"Especialidad: {row.get('specialty') or ''}\n"
            f"Consulta: {row.get('consultation_type') or ''}\n"
            f"Servicio: {row.get('service_type') or ''}\n"
            f"Lugar: {row.get('clinic_name') or ''}\n"
            f"Ubicacion: {row.get('province') or ''} / {row.get('canton') or ''} / {row.get('district') or ''}\n"
            f"ID: {row.get('tasacion_id') or ''}"
        )

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        self.current_row = next((item for item in self.rows if str(item.get("id")) == str(selection[0])), None)
        if not self.current_row:
            return
        self.detail_title.set(self.current_row.get("professional_name") or "Sin nombre")
        self.detail_body.set(self._row_text(self.current_row))

    def _sort_by(self, col):
        reverse = not self._sort_state.get(col, False)
        self._sort_state[col] = reverse
        self.rows.sort(key=lambda row: str(row.get(col) or "").lower(), reverse=reverse)
        self._render_rows()

    def _limpiar(self):
        for var in (
            self.q_var,
            self.province_var,
            self.canton_var,
            self.district_var,
            self.specialty_var,
            self.consultation_var,
            self.service_var,
            self.clinic_var,
        ):
            var.set("")
        self._buscar()

    def _ver_todo(self):
        self._limpiar()

    def _refresh(self):
        self._load_filters()
        self._buscar()

    def _quick_specialty(self, specialty):
        self.specialty_var.set(specialty)
        self._buscar()

    def _quick_consulta(self, consultation):
        self.consultation_var.set(consultation)
        self._buscar()

    def _quick_province(self, province):
        self.province_var.set(province)
        self._buscar()

    def _filter_selected_specialty(self):
        if self.current_row and self.current_row.get("specialty"):
            self.specialty_var.set(self.current_row.get("specialty"))
            self._buscar()

    def _filter_selected_location(self):
        if not self.current_row:
            return
        self.province_var.set(self.current_row.get("province") or "")
        self.canton_var.set(self.current_row.get("canton") or "")
        self.district_var.set(self.current_row.get("district") or "")
        self._buscar()

    def _copiar_detalle(self):
        text = self._row_text(self.current_row)
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _exportar(self):
        if not self.rows:
            messagebox.showinfo("Red medica", "No hay resultados para exportar.")
            return
        default_name = f"red_medica_{datetime.now():%Y%m%d_%H%M}.csv"
        path = filedialog.asksaveasfilename(
            title="Exportar red medica",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        columns = [
            "tasacion_id",
            "professional_name",
            "specialty",
            "consultation_type",
            "service_type",
            "clinic_name",
            "province",
            "canton",
            "district",
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({col: row.get(col) or "" for col in columns})
        messagebox.showinfo("Red medica", f"Resultado exportado:\n{path}")

    def _detalle(self, _event=None):
        if not self.current_row:
            self._on_select()
        if self.current_row:
            messagebox.showinfo("Detalle red medica", self._row_text(self.current_row))
