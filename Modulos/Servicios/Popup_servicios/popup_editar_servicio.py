import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker
from Modulos.Servicios.date_utils import LONG_DATE_FORMAT, to_db_date, to_long_english_date
from api_client import (
    get_servicio_api,
    editar_servicio_api,
    get_servicio_surveyors_api,
    get_clientes_api,
    get_continentes_cpp_api,
    get_paises_cpp_api,
    get_puertos_cpp_api,
    get_serviciosmd_api,
    get_filtros_servicios_api,
    get_puertos_all_api,
)


class PopupEditarServicio(tk.Toplevel):
    def __init__(self, parent, consec, on_success):
        super().__init__(parent)

        self.consec = consec
        self.on_success = on_success

        self.title(f"Editar Servicio {consec}")
        self.geometry("820x760")
        self.config(bg="white")

        data = get_servicio_api(consec)
        if not data:
            messagebox.showerror("Error", "No se pudo cargar el servicio.")
            self.destroy()
            return

        self.pais_actual = (data.get("pais") or "").strip()
        self.surveyor_resumen_actual = (data.get("surveyor") or "").strip()
        self.honorarios_total_actual = data.get("honorarios", "")

        content = tk.Frame(self, bg="white")
        content.pack(padx=20, pady=18, fill="both", expand=True)

        canvas = tk.Canvas(content, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        form = tk.Frame(canvas, bg="white")
        form_window = canvas.create_window((0, 0), window=form, anchor="nw")

        def _sync_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_form_width(event):
            canvas.itemconfigure(form_window, width=event.width)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        form.bind("<Configure>", _sync_scroll_region)
        canvas.bind("<Configure>", _sync_form_width)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        form.grid_columnconfigure(0, weight=1)

        def section(title, row):
            frame = ttk.LabelFrame(form, text=title)
            frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
            frame.grid_columnconfigure(1, weight=1)
            return frame

        def label(parent, text, row, column=0):
            ttk.Label(parent, text=text).grid(
                row=row, column=column, sticky="w", padx=(12, 8), pady=6
            )

        datos = section("Datos del servicio", 0)

        label(datos, "Cliente:", 0)
        self.cmb_cliente = ttk.Combobox(datos, state="readonly", width=52)
        self.cmb_cliente.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=6)

        label(datos, "Buque / Contenedor:", 1)
        self.buque_contenedor = ttk.Entry(datos, width=52)
        self.buque_contenedor.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)

        label(datos, "Contacto:", 2)
        self.contacto = ttk.Entry(datos, width=52)
        self.contacto.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        label(datos, "Detalle:", 3)
        self.detalle = tk.Text(datos, width=52, height=3, wrap="word")
        self.detalle.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        ubicacion = section("Ubicacion y operacion", 1)

        label(ubicacion, "Continente:", 0)
        self.cmb_continente = ttk.Combobox(ubicacion, state="readonly", width=52)
        self.cmb_continente.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=6)
        self.cmb_continente.bind("<<ComboboxSelected>>", self._load_paises)

        label(ubicacion, "Pais:", 1)
        self.cmb_pais = ttk.Combobox(ubicacion, state="readonly", width=52)
        self.cmb_pais.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        self.cmb_pais.bind("<<ComboboxSelected>>", self._on_pais_selected)

        label(ubicacion, "Puerto:", 2)
        self.cmb_puerto = ttk.Combobox(ubicacion, state="readonly", width=52)
        self.cmb_puerto.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        label(ubicacion, "Operacion:", 3)
        self.cmb_operacion = ttk.Combobox(ubicacion, state="readonly", width=52)
        self.cmb_operacion.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        self._load_edit_catalogs(data)

        ejecucion = section("Ejecucion y costos", 2)
        ejecucion.grid_columnconfigure(1, weight=1)
        ejecucion.grid_columnconfigure(3, weight=1)

        label(ejecucion, "Surveyor:", 0)
        surveyor_row = tk.Frame(ejecucion)
        surveyor_row.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 12), pady=6)
        surveyor_row.grid_columnconfigure(0, weight=1)

        self.surveyor = ttk.Entry(surveyor_row, width=32)
        self.surveyor.insert(0, self.surveyor_resumen_actual)
        self.surveyor.config(state="readonly")
        self.surveyor.grid(row=0, column=0, sticky="ew")

        ttk.Button(
            surveyor_row,
            text="Agregar surveyor",
            command=lambda: self._abrir_popup_surveyors(modo="add"),
        ).grid(row=0, column=1, padx=(6, 4))

        ttk.Button(
            surveyor_row,
            text="Ver desglose",
            command=lambda: self._abrir_popup_surveyors(modo="view"),
        ).grid(row=0, column=2)

        label(ejecucion, "Honorarios:", 1)
        self.honorarios = ttk.Entry(ejecucion, width=18)
        self.honorarios.insert(0, self.honorarios_total_actual)
        self.honorarios.grid(row=1, column=1, sticky="w", padx=(0, 12), pady=6)

        label(ejecucion, "Costo Operativo:", 2)
        self.costo = ttk.Entry(ejecucion, width=18)
        self.costo.insert(0, data.get("costo_operativo", ""))
        self.costo.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=6)

        label(ejecucion, "Costo Tarjetas:", 3)
        self.costo_tarjetas = ttk.Entry(ejecucion, width=18)
        self.costo_tarjetas.insert(0, data.get("costo_tarjetas", ""))
        self.costo_tarjetas.grid(row=3, column=1, sticky="w", padx=(0, 12), pady=6)

        label(ejecucion, "Fecha Inicio:", 1, column=2)
        fecha_row = tk.Frame(ejecucion)
        fecha_row.grid(row=1, column=3, sticky="w", padx=(0, 12), pady=6)
        self.fecha_ini = ttk.Entry(fecha_row, width=18)
        self.fecha_ini.insert(0, to_long_english_date(data.get("fecha_inicio", "")))
        self.fecha_ini.pack(side="left")

        ttk.Button(
            fecha_row,
            text="Fecha",
            command=lambda: DatePicker(self, self.fecha_ini, output_format=LONG_DATE_FORMAT),
        ).pack(side="left", padx=(6, 0))

        label(ejecucion, "Hora Inicio:", 2, column=2)
        hora_row = tk.Frame(ejecucion)
        hora_row.grid(row=2, column=3, sticky="w", padx=(0, 12), pady=6)
        self.hora_ini = ttk.Entry(hora_row, width=10)
        self.hora_ini.insert(0, data.get("hora_inicio", ""))
        self.hora_ini.pack(side="left")

        ttk.Button(
            hora_row,
            text="Hora",
            command=lambda: TimePicker(self, self.hora_ini),
        ).pack(side="left", padx=(6, 0))

        self._toggle_costo_tarjetas()
        self.after(200, self._refresh_servicio_completo)

        btns = tk.Frame(self, bg="white")
        btns.pack(pady=15)

        tk.Button(
            btns,
            text="Guardar",
            bg="#86A9D9",
            font=("Segoe UI", 10, "bold"),
            command=self.guardar,
        ).pack(side="left", padx=10)

        tk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=10)

    def _normalize_name_list(self, raw):
        if isinstance(raw, dict) and "data" in raw:
            raw = raw.get("data", [])
        if not isinstance(raw, list):
            return []
        if not raw or isinstance(raw[0], str):
            return raw

        names = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("nombrecomercial")
                or item.get("nombrejuridico")
                or item.get("NombreComercial")
                or item.get("NombreJuridico")
                or item.get("nombre")
                or item.get("pais")
                or item.get("puerto")
                or item.get("name")
                or item.get("codigo")
                or item.get("Codigo")
                or ""
            )
            if name:
                names.append(str(name))
        return names

    def _meta_values(self, key):
        try:
            meta = get_filtros_servicios_api() or {}
            values = meta.get(key, [])
            return values if isinstance(values, list) else []
        except Exception as e:
            print(f"Error cargando filtros servicios {key}:", e)
            return []

    def _set_combo_values(self, combo, values, current):
        clean_values = []
        seen = set()
        for value in values or []:
            text = str(value or "").strip()
            if text and text not in seen:
                clean_values.append(text)
                seen.add(text)

        current = str(current or "").strip()
        if current and current not in seen:
            clean_values.insert(0, current)

        combo.config(values=clean_values)
        combo.set(current)

    def _load_edit_catalogs(self, data):
        try:
            clientes = self._normalize_name_list(get_clientes_api())
        except Exception as e:
            print("Error cargando clientes:", e)
            clientes = []
        self._set_combo_values(self.cmb_cliente, clientes, data.get("cliente", ""))

        self.buque_contenedor.insert(0, data.get("buque_contenedor", ""))
        self.contacto.insert(0, data.get("contacto", ""))
        self.detalle.insert("1.0", data.get("detalle", ""))

        try:
            continentes = self._normalize_name_list(get_continentes_cpp_api())
        except Exception as e:
            print("Error cargando continentes:", e)
            continentes = []
        self._set_combo_values(self.cmb_continente, continentes, data.get("continente", ""))

        self._load_paises(current=data.get("pais", ""), keep_current=True)
        self._load_puertos(current=data.get("puerto", ""), keep_current=True)

        try:
            operaciones = self._normalize_name_list(get_serviciosmd_api())
        except Exception as e:
            print("Error cargando operaciones:", e)
            operaciones = []
        if not operaciones:
            operaciones = self._meta_values("operaciones")
        self._set_combo_values(self.cmb_operacion, operaciones, data.get("operacion", ""))

    def _load_paises(self, event=None, current=None, keep_current=False):
        continente = self.cmb_continente.get().strip()
        try:
            paises = self._normalize_name_list(get_paises_cpp_api(continente)) if continente else []
        except Exception as e:
            print("Error cargando paises:", e)
            paises = []
        if not paises:
            paises = self._meta_values("paises")

        selected = current if keep_current else ""
        self._set_combo_values(self.cmb_pais, paises, selected)
        if not keep_current:
            self._set_combo_values(self.cmb_puerto, [], "")
        self.pais_actual = self.cmb_pais.get().strip()
        self._toggle_costo_tarjetas()

    def _load_puertos(self, event=None, current=None, keep_current=False):
        pais = self.cmb_pais.get().strip()
        try:
            puertos = self._normalize_name_list(get_puertos_cpp_api(pais)) if pais else []
        except Exception as e:
            print("Error cargando puertos:", e)
            puertos = []
        if not puertos:
            try:
                puertos = self._normalize_name_list(get_puertos_all_api())
            except Exception as e:
                print("Error cargando todos los puertos:", e)
                puertos = []
        if not puertos:
            puertos = self._meta_values("puertos")

        selected = current if keep_current else ""
        self._set_combo_values(self.cmb_puerto, puertos, selected)

    def _on_pais_selected(self, event=None):
        self.pais_actual = self.cmb_pais.get().strip()
        self._load_puertos()
        self._toggle_costo_tarjetas()

    def _toggle_costo_tarjetas(self, event=None):
        if not hasattr(self, "surveyor") or not hasattr(self, "costo_tarjetas"):
            return

        surveyor = (self.surveyor.get() or "").strip()
        pais = (self.cmb_pais.get() if hasattr(self, "cmb_pais") else self.pais_actual).strip()

        permitir = (
            pais.lower() != "costa rica"
            and "pabel pena barreto" in surveyor.lower().replace("ñ", "n")
        )

        if permitir:
            self.costo_tarjetas.config(state="normal")
        else:
            self.costo_tarjetas.delete(0, tk.END)
            self.costo_tarjetas.config(state="disabled")

    def guardar(self):
        def _to_float_or_none(valor):
            valor = (valor or "").strip()
            if valor == "":
                return None
            valor = valor.replace(",", ".")
            try:
                return float(valor)
            except Exception:
                return None

        surveyor = (self.surveyor.get() or "").strip()
        pais = (self.cmb_pais.get() or "").strip()
        permitir_tarjeta = (
            pais.lower() != "costa rica"
            and "pabel pena barreto" in surveyor.lower().replace("ñ", "n")
        )

        payload = {
            "cliente": self.cmb_cliente.get().strip(),
            "buque_contenedor": self.buque_contenedor.get().strip(),
            "contacto": self.contacto.get().strip(),
            "detalle": self.detalle.get("1.0", "end-1c").strip(),
            "continente": self.cmb_continente.get().strip(),
            "pais": pais,
            "puerto": self.cmb_puerto.get().strip(),
            "operacion": self.cmb_operacion.get().strip(),
            "surveyor": surveyor,
            "honorarios": _to_float_or_none(self.honorarios.get()),
            "costo_operativo": _to_float_or_none(self.costo.get()),
            "fecha_inicio": to_db_date(self.fecha_ini.get().strip()),
            "hora_inicio": self.hora_ini.get().strip(),
            "costo_tarjetas": (
                _to_float_or_none(self.costo_tarjetas.get()) if permitir_tarjeta else None
            ),
        }

        resp = editar_servicio_api(self.consec, payload)

        if resp.get("status") == "ok":
            messagebox.showinfo("OK", "Servicio actualizado correctamente.")
            self.on_success()
            self.destroy()
            return

        err = resp.get("error") or resp.get("detail") or "Error desconocido"
        messagebox.showerror("Error", err)

    def _abrir_popup_surveyors(self, modo="view"):
        try:
            from Modulos.Servicios.Popup_servicios.popup_surveyors_servicio import (
                PopupSurveyorsServicio,
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo importar popup_surveyors_servicio.py:\n{str(e)}",
            )
            return

        try:
            PopupSurveyorsServicio(
                self,
                self.consec,
                modo=modo,
                on_saved=self._on_surveyors_saved,
            )
        except TypeError:
            try:
                PopupSurveyorsServicio(
                    self,
                    self.consec,
                    on_saved=self._on_surveyors_saved,
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"No se pudo abrir el popup de surveyors:\n{str(e)}",
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el popup de surveyors:\n{str(e)}",
            )

    def _on_surveyors_saved(self, resumen):
        self._refresh_servicio_completo()
        self._refresh_surveyors_from_api()

    def _refresh_servicio_completo(self):
        try:
            data = get_servicio_api(self.consec) or {}
            self.surveyor_resumen_actual = (data.get("surveyor") or "").strip()
            self.honorarios_total_actual = data.get("honorarios", 0)
        except Exception:
            self.surveyor_resumen_actual = ""
            self.honorarios_total_actual = 0

        self.surveyor.config(state="normal")
        self.surveyor.delete(0, tk.END)
        self.surveyor.insert(0, self.surveyor_resumen_actual)
        self.surveyor.config(state="readonly")

        self.honorarios.config(state="normal")
        self.honorarios.delete(0, tk.END)
        self.honorarios.insert(0, str(self.honorarios_total_actual))

        self._toggle_costo_tarjetas()

    def _refresh_surveyors_from_api(self):
        try:
            resp = get_servicio_surveyors_api(self.consec)
            if isinstance(resp, dict):
                data = resp.get("data", []) or []
            elif isinstance(resp, list):
                data = resp
            else:
                data = []
        except Exception:
            data = []

        if not data:
            self.surveyor_resumen_actual = ""
            self.honorarios_total_actual = 0
        else:
            cantidad = len(data)
            total = sum(float(x.get("honorario") or 0) for x in data)
            if cantidad == 1:
                resumen = data[0].get("surveyor_nombre", "")
            else:
                resumen = f"Varios ({cantidad})"
            self.surveyor_resumen_actual = resumen
            self.honorarios_total_actual = total

        self.surveyor.config(state="normal")
        self.surveyor.delete(0, tk.END)
        self.surveyor.insert(0, self.surveyor_resumen_actual)
        self.surveyor.config(state="readonly")

        self.honorarios.config(state="normal")
        self.honorarios.delete(0, tk.END)
        self.honorarios.insert(0, str(self.honorarios_total_actual))

        self._toggle_costo_tarjetas()
