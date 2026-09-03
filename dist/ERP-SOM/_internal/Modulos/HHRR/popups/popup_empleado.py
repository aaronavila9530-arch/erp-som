import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_date, to_db_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "si", "sí", "y"}


class PopupEmpleado(tk.Toplevel):
    """
    Popup unificado para EMPLEADOS

    Modos:
    - "nuevo"     -> crea (POST)
    - "ver"       -> solo lectura
    - "editar"    -> modifica (PUT)

    Estructura: Notebook por secciones (similar a tu popup adjunto),
    alineado a la tabla empleados.
    """

    def __init__(
        self,
        parent,
        modo: str = "nuevo",
        empleado: dict | None = None,
        codigo_generado: str | None = None,
        on_save=None
    ):
        super().__init__(parent)

        self.modo = (modo or "nuevo").lower()
        if self.modo not in ("nuevo", "ver", "editar"):
            self.modo = "nuevo"

        self.empleado = empleado or {}
        self.on_save = on_save

        # Código: si es nuevo viene desde UI principal, si no viene del empleado
        self.codigo_generado = codigo_generado or self.empleado.get("codigo") or ""

        titulo = "Empleado"
        if self.modo == "nuevo":
            titulo = "Nuevo empleado"
        elif self.modo == "ver":
            titulo = "Ver empleado"
        elif self.modo == "editar":
            titulo = "Modificar empleado"

        self.title(titulo)
        self.geometry("780x620")
        self.resizable(False, False)

        # =====================================================
        # VARIABLES (1:1 con tabla empleados)
        # =====================================================
        # Identificación / Usuario
        self.var_id = tk.StringVar(value=str(self.empleado.get("id") or ""))
        self.var_codigo = tk.StringVar(value=self.codigo_generado)
        self.var_cedula_id = tk.StringVar(value=str(self.empleado.get("cedula_id") or ""))
        self.var_usuario = tk.StringVar(value=str(self.empleado.get("usuario") or ""))

        # Datos personales
        self.var_nombre = tk.StringVar(value=str(self.empleado.get("nombre") or ""))
        self.var_apellidos = tk.StringVar(value=str(self.empleado.get("apellidos") or ""))
        self.var_estado_civil = tk.StringVar(value=str(self.empleado.get("estado_civil") or ""))
        self.var_genero = tk.StringVar(value=str(self.empleado.get("genero") or ""))
        self.var_nacionalidad = tk.StringVar(value=str(self.empleado.get("nacionalidad") or ""))
        self.var_fecha_nacimiento = tk.StringVar(value=to_long_english_date(self.empleado.get("fecha_nacimiento") or ""))
        self.var_edad = tk.StringVar(value=str(self.empleado.get("edad") or ""))

        # Contacto y dirección
        self.var_prefijo = tk.StringVar(value=str(self.empleado.get("prefijo") or ""))
        self.var_telefono = tk.StringVar(value=str(self.empleado.get("telefono") or ""))
        self.var_provincia = tk.StringVar(value=str(self.empleado.get("provincia") or ""))
        self.var_canton = tk.StringVar(value=str(self.empleado.get("canton") or ""))
        self.var_distrito = tk.StringVar(value=str(self.empleado.get("distrito") or ""))
        self.var_direccion = tk.StringVar(value=str(self.empleado.get("direccion") or ""))

        # Laboral
        self.var_jornada = tk.StringVar(value=str(self.empleado.get("jornada") or ""))
        self.var_salario = tk.StringVar(value=str(self.empleado.get("salario") or ""))
        self.var_pago = tk.StringVar(value=str(self.empleado.get("pago") or ""))
        self.var_banco = tk.StringVar(value=str(self.empleado.get("banco") or ""))
        self.var_cuenta_iban = tk.StringVar(value=str(self.empleado.get("cuenta_iban") or ""))
        self.var_moneda = tk.StringVar(value=str(self.empleado.get("moneda") or ""))
        self.var_fecha_ingreso = tk.StringVar(value=to_long_english_date(self.empleado.get("fecha_ingreso") or ""))
        self.var_horas_contratadas = tk.StringVar(value=str(self.empleado.get("horas_contratadas") or ""))
        self.var_horas_tope_ordinario = tk.StringVar(value=str(self.empleado.get("horas_tope_ordinario") or ""))
        self.var_horas_tope_maximo = tk.StringVar(value=str(self.empleado.get("horas_tope_maximo") or ""))
        self.var_tarifa_hora_extra = tk.StringVar(value=str(self.empleado.get("tarifa_hora_extra") or ""))
        self.var_pago_minimo_garantizado = tk.BooleanVar(value=_as_bool(self.empleado.get("pago_minimo_garantizado")))
        self.var_vacaciones = tk.StringVar(value=str(self.empleado.get("vacaciones") or ""))
        self.var_estado = tk.StringVar(value=str(self.empleado.get("estado") or ""))

        # Salud y emergencia
        self.var_enfermedades = tk.StringVar(value=str(self.empleado.get("enfermedades") or ""))
        self.var_contacto_emergencia = tk.StringVar(value=str(self.empleado.get("contacto_emergencia") or ""))
        self.var_telefono_emergencia = tk.StringVar(value=str(self.empleado.get("telefono_emergencia") or ""))

        # Activos
        self.var_activo1 = tk.StringVar(value=str(self.empleado.get("activo1") or ""))
        self.var_marca1 = tk.StringVar(value=str(self.empleado.get("marca1") or ""))
        self.var_serial1 = tk.StringVar(value=str(self.empleado.get("serial1") or ""))

        self.var_activo2 = tk.StringVar(value=str(self.empleado.get("activo2") or ""))
        self.var_marca2 = tk.StringVar(value=str(self.empleado.get("marca2") or ""))
        self.var_serial2 = tk.StringVar(value=str(self.empleado.get("serial2") or ""))

        self.var_activo3 = tk.StringVar(value=str(self.empleado.get("activo3") or ""))
        self.var_marca3 = tk.StringVar(value=str(self.empleado.get("marca3") or ""))
        self.var_serial3 = tk.StringVar(value=str(self.empleado.get("serial3") or ""))

        # Read-only helpers
        self._readonly = (self.modo == "ver")

        self._build()
        self._apply_mode()

        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

    # =====================================================
    # UI
    # =====================================================
    def _build(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        tab3 = ttk.Frame(notebook)
        tab4 = ttk.Frame(notebook)
        tab5 = ttk.Frame(notebook)

        notebook.add(tab1, text="Datos personales")
        notebook.add(tab2, text="Contacto y dirección")
        notebook.add(tab3, text="Laboral y pagos")
        notebook.add(tab4, text="Emergencia y salud")
        notebook.add(tab5, text="Activos")

        # -------------------------------------------------
        # TAB 1: Datos personales + Identificación
        # -------------------------------------------------
        tab1.columnconfigure(1, weight=1)
        tab1.columnconfigure(3, weight=1)

        row = 0
        ttk.Label(tab1, text="Código").grid(row=row, column=0, padx=10, pady=(10, 6), sticky="w")
        self.ent_codigo = ttk.Entry(tab1, textvariable=self.var_codigo, width=22)
        self.ent_codigo.grid(row=row, column=1, padx=10, pady=(10, 6), sticky="w")

        ttk.Label(tab1, text="Cédula ID").grid(row=row, column=2, padx=10, pady=(10, 6), sticky="w")
        self.ent_cedula = ttk.Entry(tab1, textvariable=self.var_cedula_id, width=22)
        self.ent_cedula.grid(row=row, column=3, padx=10, pady=(10, 6), sticky="w")

        row += 1
        ttk.Label(tab1, text="Nombre").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_nombre = ttk.Entry(tab1, textvariable=self.var_nombre, width=35)
        self.ent_nombre.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab1, text="Apellidos").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_apellidos = ttk.Entry(tab1, textvariable=self.var_apellidos, width=35)
        self.ent_apellidos.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        estados = ["", "Soltero", "Casado", "Unión libre", "Divorciado", "Separado", "Viudo", "Otro"]
        ttk.Label(tab1, text="Estado civil").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.cbo_estado_civil = ttk.Combobox(tab1, textvariable=self.var_estado_civil, values=estados, state="readonly", width=32)
        self.cbo_estado_civil.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        generos = ["", "Masculino", "Femenina", "Otro"]
        ttk.Label(tab1, text="Género").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.cbo_genero = ttk.Combobox(tab1, textvariable=self.var_genero, values=generos, state="readonly", width=32)
        self.cbo_genero.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab1, text="Nacionalidad").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_nacionalidad = ttk.Entry(tab1, textvariable=self.var_nacionalidad, width=35)
        self.ent_nacionalidad.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab1, text="Usuario").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_usuario = ttk.Entry(tab1, textvariable=self.var_usuario, width=35)
        self.ent_usuario.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab1, text="Fecha nacimiento").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_fecha_nac = ttk.Entry(tab1, textvariable=self.var_fecha_nacimiento, width=35)
        self.ent_fecha_nac.grid(
            row=row,
            column=1,
            padx=10,
            pady=6,
            sticky="w"
        )
        ttk.Button(
            tab1,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.ent_fecha_nac, output_format=LONG_DATE_FORMAT, on_select=lambda *_: self._on_fecha_nacimiento_change())
        ).grid(row=row, column=1, padx=(305, 10), pady=6, sticky="w")
        self.ent_fecha_nac.bind("<FocusOut>", self._on_fecha_nacimiento_change)



        ttk.Label(tab1, text="Edad").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_edad = ttk.Entry(tab1, textvariable=self.var_edad, width=35)
        self.ent_edad.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        # -------------------------------------------------
        # TAB 2: Contacto y dirección
        # -------------------------------------------------
        tab2.columnconfigure(1, weight=1)
        tab2.columnconfigure(3, weight=1)

        row = 0
        prefijos = ["", "+506", "+52", "+57", "+506", "+1", "+504"]
        ttk.Label(tab2, text="Prefijo").grid(row=row, column=0, padx=10, pady=(10, 6), sticky="w")
        self.cbo_prefijo = ttk.Combobox(tab2, textvariable=self.var_prefijo, values=prefijos, state="readonly", width=32)
        self.cbo_prefijo.grid(row=row, column=1, padx=10, pady=(10, 6), sticky="w")

        ttk.Label(tab2, text="Teléfono").grid(row=row, column=2, padx=10, pady=(10, 6), sticky="w")
        self.ent_telefono = ttk.Entry(tab2, textvariable=self.var_telefono, width=35)
        self.ent_telefono.grid(row=row, column=3, padx=10, pady=(10, 6), sticky="w")

        row += 1
        ttk.Label(tab2, text="Provincia").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_provincia = ttk.Entry(tab2, textvariable=self.var_provincia, width=35)
        self.ent_provincia.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab2, text="Cantón").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_canton = ttk.Entry(tab2, textvariable=self.var_canton, width=35)
        self.ent_canton.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab2, text="Distrito").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_distrito = ttk.Entry(tab2, textvariable=self.var_distrito, width=35)
        self.ent_distrito.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab2, text="Dirección").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_direccion = ttk.Entry(tab2, textvariable=self.var_direccion, width=35)
        self.ent_direccion.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        # -------------------------------------------------
        # TAB 3: Laboral y pagos
        # -------------------------------------------------
        tab3.columnconfigure(1, weight=1)
        tab3.columnconfigure(3, weight=1)

        row = 0
        jornadas = ["", "Completa", "Medio tiempo", "Por horas", "Tiempo completo"]
        ttk.Label(tab3, text="Jornada").grid(row=row, column=0, padx=10, pady=(10, 6), sticky="w")
        self.cbo_jornada = ttk.Combobox(tab3, textvariable=self.var_jornada, values=jornadas, state="readonly", width=32)
        self.cbo_jornada.grid(row=row, column=1, padx=10, pady=(10, 6), sticky="w")

        estados_emp = ["", "Activo", "Inactivo"]
        ttk.Label(tab3, text="Estado").grid(row=row, column=2, padx=10, pady=(10, 6), sticky="w")
        self.cbo_estado = ttk.Combobox(tab3, textvariable=self.var_estado, values=estados_emp, state="readonly", width=32)
        self.cbo_estado.grid(row=row, column=3, padx=10, pady=(10, 6), sticky="w")

        row += 1
        ttk.Label(tab3, text="Salario").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_salario = ttk.Entry(tab3, textvariable=self.var_salario, width=35)
        self.ent_salario.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        pagos = ["", "Mensual", "Quincenal", "Semanal"]
        ttk.Label(tab3, text="Pago").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.cbo_pago = ttk.Combobox(tab3, textvariable=self.var_pago, values=pagos, state="readonly", width=32)
        self.cbo_pago.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab3, text="Banco").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_banco = ttk.Entry(tab3, textvariable=self.var_banco, width=35)
        self.ent_banco.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab3, text="Cuenta IBAN").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_iban = ttk.Entry(tab3, textvariable=self.var_cuenta_iban, width=35)
        self.ent_iban.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        monedas = ["", "CRC", "USD", "EUR"]
        ttk.Label(tab3, text="Moneda").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.cbo_moneda = ttk.Combobox(tab3, textvariable=self.var_moneda, values=monedas, state="readonly", width=32)
        self.cbo_moneda.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab3, text="Fecha ingreso").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_fecha_ingreso = ttk.Entry(tab3, textvariable=self.var_fecha_ingreso, width=35)
        self.ent_fecha_ingreso.grid(
            row=row,
            column=3,
            padx=10,
            pady=6,
            sticky="w"
        )
        ttk.Button(
            tab3,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.ent_fecha_ingreso, output_format=LONG_DATE_FORMAT)
        ).grid(row=row, column=3, padx=(305, 10), pady=6, sticky="w")

        row += 1
        ttk.Label(tab3, text="Horas contratadas").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_horas = ttk.Entry(tab3, textvariable=self.var_horas_contratadas, width=35)
        self.ent_horas.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab3, text="Vacaciones").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_vacaciones = ttk.Entry(tab3, textvariable=self.var_vacaciones, width=35)
        self.ent_vacaciones.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab3, text="Primer aviso / tope ordinario").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_horas_tope_ordinario = ttk.Entry(tab3, textvariable=self.var_horas_tope_ordinario, width=35)
        self.ent_horas_tope_ordinario.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        ttk.Label(tab3, text="Segundo aviso / tope maximo").grid(row=row, column=2, padx=10, pady=6, sticky="w")
        self.ent_horas_tope_maximo = ttk.Entry(tab3, textvariable=self.var_horas_tope_maximo, width=35)
        self.ent_horas_tope_maximo.grid(row=row, column=3, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab3, text="Tarifa hora extra").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_tarifa_hora_extra = ttk.Entry(tab3, textvariable=self.var_tarifa_hora_extra, width=35)
        self.ent_tarifa_hora_extra.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        self.chk_pago_minimo = ttk.Checkbutton(
            tab3,
            text="Pago mínimo garantizado",
            variable=self.var_pago_minimo_garantizado
        )
        self.chk_pago_minimo.grid(row=row, column=2, columnspan=2, padx=10, pady=6, sticky="w")

        # -------------------------------------------------
        # TAB 4: Emergencia y salud
        # -------------------------------------------------
        tab4.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(tab4, text="Enfermedades").grid(row=row, column=0, padx=10, pady=(10, 6), sticky="w")
        self.ent_enfermedades = ttk.Entry(tab4, textvariable=self.var_enfermedades, width=70)
        self.ent_enfermedades.grid(row=row, column=1, padx=10, pady=(10, 6), sticky="w")

        row += 1
        ttk.Label(tab4, text="Contacto emergencia").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_contacto_emerg = ttk.Entry(tab4, textvariable=self.var_contacto_emergencia, width=70)
        self.ent_contacto_emerg.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        row += 1
        ttk.Label(tab4, text="Teléfono emergencia").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        self.ent_tel_emerg = ttk.Entry(tab4, textvariable=self.var_telefono_emergencia, width=70)
        self.ent_tel_emerg.grid(row=row, column=1, padx=10, pady=6, sticky="w")

        # -------------------------------------------------
        # TAB 5: Activos
        # -------------------------------------------------
        tab5.columnconfigure(1, weight=1)
        tab5.columnconfigure(2, weight=1)
        tab5.columnconfigure(3, weight=1)

        self._row_activo(tab5, 0, "Activo 1", self.var_activo1, self.var_marca1, self.var_serial1)
        self._row_activo(tab5, 1, "Activo 2", self.var_activo2, self.var_marca2, self.var_serial2)
        self._row_activo(tab5, 2, "Activo 3", self.var_activo3, self.var_marca3, self.var_serial3)

        # -------------------------------------------------
        # FOOTER BOTONES
        # -------------------------------------------------
        footer = ttk.Frame(container)
        footer.pack(fill="x", pady=(10, 0))

        self.btn_cancelar = ttk.Button(footer, text="Cerrar", command=self.destroy)
        self.btn_cancelar.pack(side="right", padx=5)

        self.btn_guardar = ttk.Button(footer, text="Guardar", command=self._guardar)
        self.btn_guardar.pack(side="right", padx=5)

    def _row_activo(self, parent, row, label, var_activo, var_marca, var_serial):
        pady_top = (10, 6) if row == 0 else 6

        ttk.Label(parent, text=label).grid(row=row, column=0, padx=10, pady=pady_top, sticky="w")
        ent_a = ttk.Entry(parent, textvariable=var_activo, width=24)
        ent_a.grid(row=row, column=1, padx=6, pady=pady_top, sticky="w")

        ent_m = ttk.Entry(parent, textvariable=var_marca, width=22)
        ent_m.grid(row=row, column=2, padx=6, pady=pady_top, sticky="w")

        ent_s = ttk.Entry(parent, textvariable=var_serial, width=24)
        ent_s.grid(row=row, column=3, padx=6, pady=pady_top, sticky="w")

        if not hasattr(self, "_activo_entries"):
            self._activo_entries = []
        self._activo_entries.extend([ent_a, ent_m, ent_s])

    # =====================================================
    # MODE
    # =====================================================
    def _apply_mode(self):
        # Código: SIEMPRE readonly (lo genera el backend)
        self.ent_codigo.configure(state="readonly")

        # Modo ver: todo deshabilitado + sin guardar
        if self.modo == "ver":
            self._set_all_inputs_state("disabled")
            self.btn_guardar.configure(state="disabled")

        # Modo editar: editable (excepto código)
        if self.modo == "editar":
            self._set_all_inputs_state("normal")
            self.ent_codigo.configure(state="readonly")

        # Modo nuevo: editable + estado por defecto Activo
        if self.modo == "nuevo":
            self._set_all_inputs_state("normal")
            if not self.var_estado.get().strip():
                self.var_estado.set("Activo")

    def _set_all_inputs_state(self, state: str):
        widgets = [
            self.ent_cedula, self.ent_nombre, self.ent_apellidos,
            self.cbo_estado_civil, self.cbo_genero, self.ent_nacionalidad, self.ent_usuario,
            self.ent_fecha_nac, self.ent_edad,
            self.cbo_prefijo, self.ent_telefono, self.ent_provincia, self.ent_canton,
            self.ent_distrito, self.ent_direccion,
            self.cbo_jornada, self.cbo_estado, self.ent_salario, self.cbo_pago,
            self.ent_banco, self.ent_iban, self.cbo_moneda, self.ent_fecha_ingreso,
            self.ent_horas, self.ent_vacaciones, self.ent_horas_tope_ordinario,
            self.ent_horas_tope_maximo, self.ent_tarifa_hora_extra, self.chk_pago_minimo,
            self.ent_enfermedades, self.ent_contacto_emerg, self.ent_tel_emerg,
        ]

        if hasattr(self, "_activo_entries"):
            widgets.extend(self._activo_entries)

        for w in widgets:
            try:
                # Combobox readonly: si va disabled está bien, si va normal queda editable;
                # por eso fijamos state directo.
                if isinstance(w, ttk.Combobox):
                    if state == "disabled":
                        w.configure(state="disabled")
                    else:
                        w.configure(state="readonly")
                else:
                    w.configure(state=state)
            except Exception:
                pass

    # =====================================================
    # DATA BUILD
    # =====================================================
    def _build_payload(self) -> dict:
        # Nota: fecharegistro lo setea backend (NOW()) en POST.
        # En PUT solo mandamos campos editables (whitelist ya existe en backend).

        payload = {
            # El código lo genera el backend (no enviar desde UI)
            "cedula_id": self.var_cedula_id.get().strip() or None,
            "usuario": self.var_usuario.get().strip() or None,

            "nombre": self.var_nombre.get().strip(),
            "apellidos": self.var_apellidos.get().strip(),
            "estado_civil": self.var_estado_civil.get().strip() or None,
            "genero": self.var_genero.get().strip() or None,
            "nacionalidad": self.var_nacionalidad.get().strip() or None,
            "fecha_nacimiento": to_db_date(self.var_fecha_nacimiento.get().strip()) or None,
            "edad": self.var_edad.get().strip() or None,

            "prefijo": self.var_prefijo.get().strip() or None,
            "telefono": self.var_telefono.get().strip() or None,
            "provincia": self.var_provincia.get().strip() or None,
            "canton": self.var_canton.get().strip() or None,
            "distrito": self.var_distrito.get().strip() or None,
            "direccion": self.var_direccion.get().strip() or None,

            "jornada": self.var_jornada.get().strip() or None,
            "salario": self.var_salario.get().strip() or None,
            "pago": self.var_pago.get().strip() or None,
            "banco": self.var_banco.get().strip() or None,
            "cuenta_iban": self.var_cuenta_iban.get().strip() or None,
            "moneda": self.var_moneda.get().strip() or None,
            "fecha_ingreso": to_db_date(self.var_fecha_ingreso.get().strip()) or None,
            "horas_contratadas": self.var_horas_contratadas.get().strip() or None,
            "horas_tope_ordinario": self.var_horas_tope_ordinario.get().strip() or None,
            "horas_tope_maximo": self.var_horas_tope_maximo.get().strip() or None,
            "tarifa_hora_extra": self.var_tarifa_hora_extra.get().strip() or None,
            "pago_minimo_garantizado": bool(self.var_pago_minimo_garantizado.get()),
            "vacaciones": self.var_vacaciones.get().strip() or None,
            "estado": self.var_estado.get().strip() or None,

            "enfermedades": self.var_enfermedades.get().strip() or None,
            "contacto_emergencia": self.var_contacto_emergencia.get().strip() or None,
            "telefono_emergencia": self.var_telefono_emergencia.get().strip() or None,

            "activo1": self.var_activo1.get().strip() or None,
            "marca1": self.var_marca1.get().strip() or None,
            "serial1": self.var_serial1.get().strip() or None,

            "activo2": self.var_activo2.get().strip() or None,
            "marca2": self.var_marca2.get().strip() or None,
            "serial2": self.var_serial2.get().strip() or None,

            "activo3": self.var_activo3.get().strip() or None,
            "marca3": self.var_marca3.get().strip() or None,
            "serial3": self.var_serial3.get().strip() or None,
        }

        # Limpieza final: strings vacíos a None
        for k, v in list(payload.items()):
            if isinstance(v, str) and not v.strip():
                payload[k] = None

        # Campos mínimos
        if not payload.get("codigo"):
            payload["codigo"] = self.codigo_generado

        return payload

    # =====================================================
    # ACTIONS
    # =====================================================
    def _guardar(self):
        if self.modo == "ver":
            return

        if not self.var_nombre.get().strip():
            messagebox.showerror("Validación", "El nombre es requerido.")
            return

        if not self.var_apellidos.get().strip():
            messagebox.showerror("Validación", "Los apellidos son requeridos.")
            return

        payload = self._build_payload()

        # En editar, necesito id
        empleado_id = None
        if self.modo == "editar":
            try:
                empleado_id = int(str(self.empleado.get("id") or "").strip())
            except Exception:
                empleado_id = None

            if not empleado_id:
                messagebox.showerror("Error", "No se encontró el ID del empleado para modificar.")
                return

        if self.on_save:
            try:
                self.on_save(self.modo, empleado_id, payload)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
                return

        self.destroy()


    def _on_fecha_nacimiento_change(self, event=None):
        """
        Autocalcula la edad cuando se selecciona la fecha de nacimiento.
        """
        try:
            fecha_str = self.var_fecha_nacimiento.get()
            if not fecha_str:
                self.var_edad.set("")
                return

            fecha_nac = parse_hhrr_date(fecha_str)
            if not fecha_nac:
                raise ValueError("Fecha invalida")
            hoy = date.today()

            edad = hoy.year - fecha_nac.year - (
                (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day)
            )

            if edad < 0:
                self.var_edad.set("")
                return

            self.var_edad.set(str(edad))

        except Exception:
            self.var_edad.set("")
