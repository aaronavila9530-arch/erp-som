import tkinter as tk
from tkinter import ttk
import requests
from api_client import BASE_URL
from Modulos.MasterData.prefijos_telefonicos import PREFIJOS_TELEFONICOS


class PopupSurveyor(tk.Toplevel):

    def __init__(self, parent, codigo, lista_operaciones=None, lista_puertos=None, on_save=None):
        super().__init__(parent)
        self.title("Agregar Surveyor")
        self.geometry("700x600")
        self.config(bg="white")
        self.resizable(False, False)

        self.on_save = on_save
        self.codigo_generado = codigo

        # Si no vienen datos aún, usamos listas vacías
        self.lista_operaciones = lista_operaciones or []
        self.lista_puertos = lista_puertos or []
        self._ensure_catalogs()

        # Variables
        self.nombre = tk.StringVar()
        self.apellidos = tk.StringVar()
        self.email = tk.StringVar()
        self.nacionalidad = tk.StringVar()
        self.estado_civil = tk.StringVar()
        self.genero = tk.StringVar()
        self.prefijo = tk.StringVar()
        self.telefono = tk.StringVar()
        self.provincia = tk.StringVar()
        self.canton = tk.StringVar()
        self.distrito = tk.StringVar()
        self.direccion = tk.StringVar()
        self.jornada = tk.StringVar()
        self.operacion = tk.StringVar()
        self.honorario = tk.StringVar()
        self.frecuencia_pago = tk.StringVar()
        self.banco = tk.StringVar()
        self.direccion_banco = tk.StringVar()
        self.cuenta_iban = tk.StringVar()
        self.moneda = tk.StringVar()
        self.swift = tk.StringVar()
        self.uid = tk.StringVar()
        self.enfermedades = tk.StringVar()
        self.contacto_emergencia = tk.StringVar()
        self.telefono_emergencia = tk.StringVar()
        self.puerto = tk.StringVar()
        self.tarifa_rows = []

        self._build()

    def _ensure_catalogs(self):
        if not self.lista_operaciones:
            try:
                url = f"{BASE_URL}/servicios_md?page=1&page_size=500"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                payload = response.json()
                self.lista_operaciones = [
                    item.get("nombre", "")
                    for item in payload.get("data", [])
                    if item.get("nombre")
                ]
            except Exception as e:
                print("Error cargando operaciones iniciales:", e)

        if not self.lista_puertos:
            try:
                from api_client import get_puertos_all_api
                self.lista_puertos = get_puertos_all_api() or []
            except Exception as e:
                print("Error cargando puertos iniciales:", e)

    def _build(self):

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, bg="white")
        tab2 = tk.Frame(notebook, bg="white")
        tab3 = tk.Frame(notebook, bg="white")
        tab4 = tk.Frame(notebook, bg="white")
        tab5 = tk.Frame(notebook, bg="white")

        notebook.add(tab1, text="📌 Datos Personales")
        notebook.add(tab2, text="📞 Contacto")
        notebook.add(tab3, text="💼 Laboral")
        notebook.add(tab4, text="🏥 Salud")
        notebook.add(tab5, text="⚓ Operaciones")

        # Permitir expansión horizontal
        for tab in (tab1, tab2, tab3, tab4, tab5):
            tab.columnconfigure(1, weight=1)

        # ==========================
        # TAB 1 — Datos Personales
        # ==========================

        ttk.Label(
            tab1,
            text=f"Código: {self.codigo_generado}",
            background="white",
            foreground="blue"
        ).grid(row=0, column=0, padx=10, pady=10, columnspan=2, sticky="w")

        ttk.Label(tab1, text="Nombre:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.entry_nombre = ttk.Entry(tab1, textvariable=self.nombre)
        self.entry_nombre.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab1, text="Apellidos:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.entry_apellidos = ttk.Entry(tab1, textvariable=self.apellidos)
        self.entry_apellidos.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        estados = ["Soltero", "Casado", "Unión libre", "Divorciado", "Separado", "Viudo", "Otro"]

        ttk.Label(tab1, text="Estado civil:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.combo_estado_civil = ttk.Combobox(
            tab1,
            textvariable=self.estado_civil,
            values=estados,
            state="readonly"
        )
        self.combo_estado_civil.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        generos = ["Masculino", "Femenino", "Otro"]

        ttk.Label(tab1, text="Género:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.combo_genero = ttk.Combobox(
            tab1,
            textvariable=self.genero,
            values=generos,
            state="readonly"
        )
        self.combo_genero.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab1, text="Nacionalidad:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")

        self.entry_nacionalidad = ttk.Entry(tab1, textvariable=self.nacionalidad)
        self.entry_nacionalidad.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # ==========================
        # TAB 2 — Contacto
        # ==========================

        ttk.Label(tab2, text="Prefijo:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.combo_prefijo = ttk.Combobox(
            tab2,
            textvariable=self.prefijo,
            values=PREFIJOS_TELEFONICOS,
            state="readonly"
        )
        self.combo_prefijo.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Teléfono:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.entry_telefono = ttk.Entry(tab2, textvariable=self.telefono)
        self.entry_telefono.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Email:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.entry_email = ttk.Entry(tab2, textvariable=self.email)
        self.entry_email.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Provincia:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.entry_provincia = ttk.Entry(tab2, textvariable=self.provincia)
        self.entry_provincia.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Cantón:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.entry_canton = ttk.Entry(tab2, textvariable=self.canton)
        self.entry_canton.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Distrito:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")

        self.entry_distrito = ttk.Entry(tab2, textvariable=self.distrito)
        self.entry_distrito.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab2, text="Dirección exacta:", background="white") \
            .grid(row=6, column=0, padx=10, pady=5, sticky="w")

        self.entry_direccion = ttk.Entry(tab2, textvariable=self.direccion)
        self.entry_direccion.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # ==========================
        # TAB 3 — Laboral
        # ==========================

        ttk.Label(tab3, text="Jornada:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")

        jornadas = ["Tiempo completo", "Medio tiempo", "Por horas"]

        self.combo_jornada = ttk.Combobox(
            tab3,
            textvariable=self.jornada,
            values=jornadas,
            state="readonly"
        )
        self.combo_jornada.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Pago:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")

        frecuencia = ["Mensual", "Quincenal", "Semanal"]

        self.combo_pago = ttk.Combobox(
            tab3,
            textvariable=self.frecuencia_pago,
            values=frecuencia,
            state="readonly"
        )
        self.combo_pago.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Banco:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.entry_banco = ttk.Entry(tab3, textvariable=self.banco)
        self.entry_banco.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Dirección banco:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.entry_direccion_banco = ttk.Entry(tab3, textvariable=self.direccion_banco)
        self.entry_direccion_banco.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Cuenta IBAN:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.entry_cuenta_iban = ttk.Entry(tab3, textvariable=self.cuenta_iban)
        self.entry_cuenta_iban.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Swift Code:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")

        self.entry_swift = ttk.Entry(tab3, textvariable=self.swift)
        self.entry_swift.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="UID:", background="white") \
            .grid(row=6, column=0, padx=10, pady=5, sticky="w")

        self.entry_uid = ttk.Entry(tab3, textvariable=self.uid)
        self.entry_uid.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab3, text="Moneda:", background="white") \
            .grid(row=7, column=0, padx=10, pady=5, sticky="w")

        monedas = ["CRC", "USD", "EUR"]

        self.combo_moneda = ttk.Combobox(
            tab3,
            textvariable=self.moneda,
            values=monedas,
            state="readonly"
        )
        self.combo_moneda.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        # ==========================
        # TAB 4 — Salud
        # ==========================

        ttk.Label(tab4, text="Enfermedades:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.entry_enfermedades = ttk.Entry(tab4, textvariable=self.enfermedades)
        self.entry_enfermedades.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab4, text="Contacto emergencia:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.entry_contacto_emergencia = ttk.Entry(tab4, textvariable=self.contacto_emergencia)
        self.entry_contacto_emergencia.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab4, text="Tel. emergencia:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.entry_telefono_emergencia = ttk.Entry(tab4, textvariable=self.telefono_emergencia)
        self.entry_telefono_emergencia.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # ==========================
        # TAB 5 — Operaciones
        # ==========================

        ttk.Label(tab5, text="Operación:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.combo_operacion = ttk.Combobox(
            tab5,
            textvariable=self.operacion,
            values=self.lista_operaciones,
            state="readonly"
        )
        self.combo_operacion.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab5, text="Honorario:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.entry_honorario = ttk.Entry(tab5, textvariable=self.honorario)
        self.entry_honorario.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(tab5, text="Puertos que atiende:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.combo_puerto = ttk.Combobox(
            tab5,
            textvariable=self.puerto,
            values=self.lista_puertos,
            state="readonly"
        )
        self.combo_puerto.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Cargar operaciones dinámicamente
        self.combo_operacion.configure(postcommand=self._cargar_operaciones)

        ttk.Separator(tab5, orient="horizontal").grid(
            row=3, column=0, columnspan=2, padx=10, pady=12, sticky="ew"
        )

        ttk.Label(
            tab5,
            text="Cobertura adicional por puerto / servicio",
            background="white",
            font=("Arial", 10, "bold")
        ).grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")

        header = tk.Frame(tab5, bg="white")
        header.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 2), sticky="ew")
        for idx, text in enumerate(("Puerto", "Servicio", "Honorario", "Accion")):
            ttk.Label(header, text=text, background="white", font=("Arial", 9, "bold")).grid(
                row=0, column=idx, padx=4, sticky="w"
            )

        self.tarifas_frame = tk.Frame(tab5, bg="white")
        self.tarifas_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=2, sticky="ew")

        frame_tarifa_btns = tk.Frame(tab5, bg="white")
        frame_tarifa_btns.grid(row=7, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        tk.Button(frame_tarifa_btns, text="+ Agregar puerto / servicio", command=self._add_tarifa_row) \
            .pack(side="left", padx=(0, 6))
        tk.Button(frame_tarifa_btns, text="- Quitar ultimo", command=self._remove_last_tarifa_row) \
            .pack(side="left")

        for child in tab5.grid_slaves():
            child.destroy()

        ttk.Label(
            tab5,
            text="Cobertura por puerto / servicio",
            background="white",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        header = tk.Frame(tab5, bg="white")
        header.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 2), sticky="ew")
        for idx, text in enumerate(("Puerto", "Servicio", "Honorario", "Accion")):
            ttk.Label(header, text=text, background="white", font=("Arial", 9, "bold")).grid(
                row=0, column=idx, padx=4, sticky="w"
            )

        base_frame = tk.Frame(tab5, bg="white")
        base_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=2, sticky="ew")

        self.combo_puerto = ttk.Combobox(
            base_frame,
            textvariable=self.puerto,
            values=self.lista_puertos,
            state="readonly",
            width=24
        )
        self.combo_puerto.grid(row=0, column=0, padx=4, sticky="ew")

        self.combo_operacion = ttk.Combobox(
            base_frame,
            textvariable=self.operacion,
            values=self.lista_operaciones,
            state="readonly",
            width=24
        )
        self.combo_operacion.configure(postcommand=self._cargar_operaciones)
        self.combo_operacion.grid(row=0, column=1, padx=4, sticky="ew")

        self.entry_honorario = ttk.Entry(base_frame, textvariable=self.honorario, width=14)
        self.entry_honorario.grid(row=0, column=2, padx=4, sticky="ew")
        ttk.Label(base_frame, text="Base", background="white").grid(row=0, column=3, padx=4, sticky="w")

        self.tarifas_frame = tk.Frame(tab5, bg="white")
        self.tarifas_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="ew")

        frame_tarifa_btns = tk.Frame(tab5, bg="white")
        frame_tarifa_btns.grid(row=4, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        tk.Button(frame_tarifa_btns, text="+ Agregar puerto / servicio", command=self._add_tarifa_row) \
            .pack(side="left", padx=(0, 6))
        tk.Button(frame_tarifa_btns, text="- Quitar ultimo", command=self._remove_last_tarifa_row) \
            .pack(side="left")

        # ==========================
        # BOTÓN GUARDAR
        # ==========================

        tk.Button(
            self,
            text="Guardar",
            bg="#008C35",
            fg="white",
            width=15,
            command=self._guardar
        ).pack(pady=10)

    def _add_tarifa_row(self, item=None):
        item = item or {}
        row_frame = tk.Frame(self.tarifas_frame, bg="white")
        row_frame.pack(fill="x", pady=2)

        puerto_var = tk.StringVar(value=item.get("puerto", ""))
        servicio_var = tk.StringVar(value=item.get("servicio") or item.get("operacion", ""))
        honorario_var = tk.StringVar(value="" if item.get("honorario") is None else str(item.get("honorario", "")))

        combo_puerto = ttk.Combobox(
            row_frame,
            textvariable=puerto_var,
            values=self.lista_puertos,
            state="readonly",
            width=24
        )
        combo_puerto.grid(row=0, column=0, padx=4, sticky="ew")

        combo_servicio = ttk.Combobox(
            row_frame,
            textvariable=servicio_var,
            values=self.lista_operaciones,
            state="readonly",
            width=24
        )
        combo_servicio.configure(postcommand=self._cargar_operaciones)
        combo_servicio.grid(row=0, column=1, padx=4, sticky="ew")

        entry_honorario = ttk.Entry(row_frame, textvariable=honorario_var, width=14)
        entry_honorario.grid(row=0, column=2, padx=4, sticky="ew")

        row = {
            "frame": row_frame,
            "puerto": puerto_var,
            "servicio": servicio_var,
            "honorario": honorario_var,
            "servicio_combo": combo_servicio,
        }
        tk.Button(row_frame, text="Quitar", command=lambda r=row: self._remove_tarifa_row(r)) \
            .grid(row=0, column=3, padx=4)

        self.tarifa_rows.append(row)

    def _remove_tarifa_row(self, row):
        if row in self.tarifa_rows:
            self.tarifa_rows.remove(row)
        row["frame"].destroy()

    def _remove_last_tarifa_row(self):
        if self.tarifa_rows:
            self._remove_tarifa_row(self.tarifa_rows[-1])

    def _collect_tarifas(self):
        tarifas = []
        base = {
            "puerto": self.combo_puerto.get().strip(),
            "servicio": self.combo_operacion.get().strip(),
            "honorario": self.entry_honorario.get().strip(),
            "moneda": self.combo_moneda.get().strip() or "USD",
        }
        if any(base.values()):
            tarifas.append(base)

        for row in self.tarifa_rows:
            item = {
                "puerto": row["puerto"].get().strip(),
                "servicio": row["servicio"].get().strip(),
                "honorario": row["honorario"].get().strip(),
                "moneda": self.combo_moneda.get().strip() or "USD",
            }
            if any(item.values()):
                tarifas.append(item)
        return tarifas

    def set_tarifas(self, tarifas):
        for row in list(self.tarifa_rows):
            self._remove_tarifa_row(row)

        tarifas = tarifas or []
        if not tarifas:
            return

        first = tarifas[0]
        self.puerto.set(first.get("puerto", ""))
        self.operacion.set(first.get("servicio") or first.get("operacion", ""))
        self.honorario.set("" if first.get("honorario") is None else str(first.get("honorario", "")))
        for item in tarifas[1:]:
            self._add_tarifa_row(item)

    def _guardar(self):
        tarifas = self._collect_tarifas()
        data = {
            "codigo": self.codigo_generado,
            "nombre": self.entry_nombre.get().strip(),
            "apellidos": self.entry_apellidos.get().strip(),
            "email": self.entry_email.get().strip(),
            "estado_civil": self.combo_estado_civil.get().strip(),
            "genero": self.combo_genero.get().strip(),
            "nacionalidad": self.entry_nacionalidad.get().strip(),
            "prefijo": self.combo_prefijo.get().strip(),
            "telefono": self.entry_telefono.get().strip(),
            "provincia": self.entry_provincia.get().strip(),
            "canton": self.entry_canton.get().strip(),
            "distrito": self.entry_distrito.get().strip(),
            "direccion": self.entry_direccion.get().strip(),
            "jornada": self.combo_jornada.get().strip(),
            "operacion": self.combo_operacion.get().strip(),
            "honorario": self.entry_honorario.get().strip(),
            "pago": self.combo_pago.get().strip(),
            "banco": self.entry_banco.get().strip(),
            "direccion_banco": self.entry_direccion_banco.get().strip(),
            "cuenta_iban": self.entry_cuenta_iban.get().strip(),
            "moneda": self.combo_moneda.get().strip(),
            "swift": self.entry_swift.get().strip(),
            "uid": self.entry_uid.get().strip(),
            "enfermedades": self.entry_enfermedades.get().strip(),
            "contacto_emergencia": self.entry_contacto_emergencia.get().strip(),
            "telefono_emergencia": self.entry_telefono_emergencia.get().strip(),
            "puerto": self.combo_puerto.get().strip(),
            "tarifas": tarifas,
        }

        print("💾 Guardar Surveyor →", data)

        if self.on_save:
            self.on_save(data)

        self.destroy()

    def _cargar_operaciones(self, event=None):

        try:
            url = f"{BASE_URL}/servicios_md/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            payload = response.json()
            data = payload.get("data", [])

            operaciones = [item["nombre"] for item in data if item.get("nombre")]
            self.lista_operaciones = operaciones

            self.combo_operacion["values"] = operaciones
            for row in self.tarifa_rows:
                row["servicio_combo"]["values"] = operaciones

        except Exception as e:
            print("Error cargando operaciones:", e)
