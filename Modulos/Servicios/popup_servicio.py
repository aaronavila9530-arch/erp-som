import tkinter as tk
from tkinter import ttk, messagebox
from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker
from api_client import (
    post_servicio,
    get_clientes_api,
    get_continentes_cpp_api,
    get_paises_cpp_api,
    get_puertos_cpp_api,   # ← AÑADIR ESTA
    get_surveyores_api,
    get_serviciosmd_api
)


class PopupServicio(tk.Toplevel):

    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.title("Agregar Servicio")
        self.geometry("580x560")
        self.configure(bg="white")
        self.resizable(False, False)
        self.on_success = on_success

        self._build_ui()
        self.load_initial_data()
      

    def _build_ui(self):
        pad = 8

        # ===================================================
        # Formulario: Grid ordenado
        # ===================================================
        ttk.Label(self, text="Tipo:", background="white").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        self.tipo = ttk.Combobox(self, values=["Buque", "Contenedor"], state="readonly")
        self.tipo.grid(row=0, column=1, padx=pad, pady=pad)

        ttk.Label(self, text="Buque / Contenedor:", background="white").grid(row=1, column=0, padx=pad, pady=pad, sticky="w")
        self.bc = ttk.Entry(self)
        self.bc.grid(row=1, column=1, padx=pad, pady=pad)

        ttk.Label(self, text="Cliente:", background="white").grid(row=2, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_cliente = ttk.Combobox(self, state="readonly")
        self.cmb_cliente.grid(row=2, column=1, padx=pad, pady=pad)

        ttk.Label(self, text="Contacto:", background="white").grid(row=3, column=0, padx=pad, pady=pad, sticky="w")
        self.contacto = ttk.Entry(self)
        self.contacto.grid(row=3, column=1, padx=pad, pady=pad)

        ttk.Label(self, text="Detalle:", background="white").grid(row=4, column=0, padx=pad, pady=pad, sticky="w")
        self.detalle = ttk.Entry(self)
        self.detalle.grid(row=4, column=1, padx=pad, pady=pad)

        # Continente / País / Puerto
        ttk.Label(self, text="Continente:", background="white").grid(row=5, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_continente = ttk.Combobox(self, state="readonly")
        self.cmb_continente.grid(row=5, column=1, padx=pad, pady=pad)
        self.cmb_continente.bind("<<ComboboxSelected>>", self.load_paises)

        ttk.Label(self, text="País:", background="white").grid(row=6, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_pais = ttk.Combobox(self, state="readonly")
        self.cmb_pais.grid(row=6, column=1, padx=pad, pady=pad)
        self.cmb_pais.bind("<<ComboboxSelected>>", self.load_puertos)

        ttk.Label(self, text="Puerto:", background="white").grid(row=7, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_puerto = ttk.Combobox(self, state="readonly")
        self.cmb_puerto.grid(row=7, column=1, padx=pad, pady=pad)

        # Operación y Surveyor
        ttk.Label(self, text="Operación:", background="white").grid(row=8, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_operacion = ttk.Combobox(self, state="readonly")
        self.cmb_operacion.grid(row=8, column=1, padx=pad, pady=pad)
        self.cmb_operacion.bind("<<ComboboxSelected>>", self.autofill_honorarios)

        ttk.Label(self, text="Surveyor:", background="white").grid(row=9, column=0, padx=pad, pady=pad, sticky="w")
        self.cmb_surveyor = ttk.Combobox(self, state="readonly")
        self.cmb_surveyor.grid(row=9, column=1, padx=pad, pady=pad)
        self.cmb_surveyor.bind("<<ComboboxSelected>>", self.autofill_honorarios)

        # HONORARIOS (autofill)
        ttk.Label(self, text="Honorarios:", background="white").grid(
            row=10, column=0, padx=pad, pady=pad, sticky="w"
        )
        self.honorarios = ttk.Entry(self)
        self.honorarios.grid(row=10, column=1, padx=pad, pady=pad)

        # COSTO OPERATIVO (manual)
        ttk.Label(self, text="Costo operativo:", background="white").grid(
            row=11, column=0, padx=pad, pady=pad, sticky="w"
        )
        self.costo_operativo = ttk.Entry(self)
        self.costo_operativo.grid(row=11, column=1, padx=pad, pady=pad)

        # FECHA INICIO
        ttk.Label(self, text="Fecha inicio:", background="white").grid(
            row=11, column=0, padx=pad, pady=pad, sticky="w"
        )
        self.fecha_inicio = ttk.Entry(self, width=18)
        self.fecha_inicio.grid(row=11, column=1, padx=pad, pady=pad)

        ttk.Button(
            self,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.fecha_inicio)
        ).grid(row=11, column=2, padx=pad)

        # HORA INICIO
        ttk.Label(self, text="Hora inicio:", background="white").grid(
            row=12, column=0, padx=pad, pady=pad, sticky="w"
        )
        self.hora_inicio = ttk.Entry(self, width=18)
        self.hora_inicio.grid(row=12, column=1, padx=pad, pady=pad)

        ttk.Button(
            self,
            text="⏱",
            width=3,
            command=lambda: TimePicker(self, self.hora_inicio)
        ).grid(row=12, column=2, padx=pad)

        # Botones
        ttk.Button(self, text="Guardar", command=self.save).grid(
            row=14, column=0, padx=pad, pady=pad
        )
        ttk.Button(self, text="Cancelar", command=self.destroy).grid(
            row=14, column=1, padx=pad, pady=pad
        )


    # ============================================================
    # CARGAR DATOS INICIALES (CLIENTES + CONTINENTES)
    # ============================================================
    def load_initial_data(self):
        """Carga datos iniciales desde la API al abrir el popup."""

        # -----------------------------
        # CLIENTES
        # -----------------------------
        try:
            raw = get_clientes_api()

            # Normalizar posibles formatos:
            # 1) ["Cliente A", "Cliente B"]
            # 2) [{"codigo":..,"nombrecomercial":..}, ...]
            # 3) {"total": X, "data": [ {...}, {...} ]}
            if isinstance(raw, dict) and "data" in raw:
                clientes = raw.get("data", [])
            else:
                clientes = raw or []

            # Guardar data completa
            self.clientes_data = clientes

            # Si viene como lista de strings → usar tal cual
            if isinstance(clientes, list) and (len(clientes) == 0 or isinstance(clientes[0], str)):
                self.cmb_cliente.config(values=clientes)

            # Si viene como lista de dicts → mostrar "nombre" (nombrecomercial / nombrejuridico)
            elif isinstance(clientes, list) and isinstance(clientes[0], dict):
                nombres = []
                for c in clientes:
                    nombre = (
                        c.get("nombrecomercial")
                        or c.get("nombrejuridico")
                        or c.get("NombreComercial")
                        or c.get("NombreJuridico")
                        or c.get("codigo")
                        or c.get("Codigo")
                        or ""
                    )
                    if nombre:
                        nombres.append(nombre)

                self.cmb_cliente.config(values=nombres)

            else:
                # Caso inesperado: forzar vacío (pero no romper)
                self.cmb_cliente.config(values=[])

        except Exception as e:
            print("❌ Error cargando clientes:", e)

        # -----------------------------
        # CONTINENTES
        # -----------------------------
        try:
            continentes = get_continentes_cpp_api()
            self.cmb_continente.config(values=continentes)
        except Exception as e:
            print("❌ Error cargando continentes:", e)

        # -----------------------------
        # OPERACIONES (ServiciosMD)
        # -----------------------------
        try:
            operaciones = get_serviciosmd_api()
            self.cmb_operacion.config(values=operaciones)
        except Exception as e:
            print("❌ Error cargando operaciones:", e)

        # -----------------------------
        # SURVEYORS
        # -----------------------------
        try:
            surveyores = get_surveyores_api()
            self.surveyores_data = surveyores  # Guardar para autofill
            self.cmb_surveyor.config(values=[s["nombre"] for s in surveyores])
        except Exception as e:
            print("❌ Error cargando surveyores:", e)



    # ============================================================
    # CARGAR PAÍSES SEGÚN CONTINENTE
    # ============================================================
    def load_paises(self, *_):
        continente = self.cmb_continente.get().strip()
        if not continente:
            return

        try:
            raw = get_paises_cpp_api(continente)

            # Normalizar formatos posibles
            if isinstance(raw, dict) and "data" in raw:
                paises = raw.get("data", [])
            else:
                paises = raw or []

            # Si vienen como strings
            if isinstance(paises, list) and (len(paises) == 0 or isinstance(paises[0], str)):
                values = paises

            # Si vienen como dicts
            elif isinstance(paises, list) and isinstance(paises[0], dict):
                values = [
                    p.get("nombre")
                    or p.get("pais")
                    or p.get("name")
                    or ""
                    for p in paises
                    if isinstance(p, dict)
                ]

            else:
                values = []

            self.cmb_pais.config(values=values)
            self.cmb_pais.set("")
            self.cmb_puerto.set("")

        except Exception as e:
            print("❌ Error cargando países:", e)

    # ============================================================
    # CARGAR PUERTOS SEGÚN PAÍS
    # ============================================================
    def load_puertos(self, *_):
        pais = self.cmb_pais.get().strip()
        if not pais:
            return

        try:
            raw = get_puertos_cpp_api(pais)

            # Normalizar formatos posibles
            if isinstance(raw, dict) and "data" in raw:
                puertos = raw.get("data", [])
            else:
                puertos = raw or []

            # Si vienen como strings
            if isinstance(puertos, list) and (len(puertos) == 0 or isinstance(puertos[0], str)):
                values = puertos

            # Si vienen como dicts
            elif isinstance(puertos, list) and isinstance(puertos[0], dict):
                values = [
                    p.get("nombre")
                    or p.get("puerto")
                    or p.get("name")
                    or ""
                    for p in puertos
                    if isinstance(p, dict)
                ]

            else:
                values = []

            self.cmb_puerto.config(values=values)
            self.cmb_puerto.set("")

        except Exception as e:
            print("❌ Error cargando puertos:", e)

    # ============================================================
    # AUTOLLENAR HONORARIOS (operación + surveyor)
    # ============================================================
    def autofill_honorarios(self, *_):
        if not hasattr(self, "surveyores_data"):
            return

        oper = self.cmb_operacion.get().strip()
        surv = self.cmb_surveyor.get().strip()

        if not oper or not surv:
            return

        for s in self.surveyores_data:

            if not isinstance(s, dict):
                continue

            nombre = (
                s.get("nombre")
                or s.get("Nombre")
                or s.get("surveyor")
                or ""
            )

            operacion = (
                s.get("operacion")
                or s.get("Operacion")
                or ""
            )

            if nombre == surv and operacion == oper:
                honorario = (
                    s.get("honorario")
                    or s.get("Honorario")
                    or 0
                )
                self.honorarios.delete(0, tk.END)
                self.honorarios.insert(0, str(honorario))
                return

        # Si no encontró coincidencia → limpiar SOLO honorarios
        self.honorarios.delete(0, tk.END)


    # ============================================================
    # UTILIDAD: convertir texto a float seguro
    # ============================================================
    def _to_float(self, value):
        """
        Convierte entradas tipo '1,200.50', '1200', '' a float.
        Si viene vacío, retorna 0.0.
        """
        if value is None:
            return 0.0

        s = str(value).strip()
        if s == "":
            return 0.0

        # quitar separadores comunes
        s = s.replace(",", "").replace(" ", "")

        return float(s)


    # =======================================================
    # Guardar → API
    # =======================================================
    def save(self):
        if not self.tipo.get() or not self.bc.get():
            messagebox.showerror(
                "Error",
                "Complete los campos obligatorios"
            )
            return

        # Validar y convertir montos
        try:
            honorarios_val = self._to_float(self.honorarios.get())
            costo_op_val = self._to_float(self.costo_operativo.get())
        except Exception:
            messagebox.showerror(
                "Error",
                "Honorarios y Costo operativo deben ser numéricos.\n"
                "Ejemplos válidos: 1200, 1200.50"
            )
            return

        data = {
            "tipo": self.tipo.get(),
            "buque_contenedor": self.bc.get(),
            "cliente": self.cmb_cliente.get(),
            "contacto": self.contacto.get(),
            "detalle": self.detalle.get(),
            "continente": self.cmb_continente.get(),
            "pais": self.cmb_pais.get(),
            "puerto": self.cmb_puerto.get(),
            "operacion": self.cmb_operacion.get(),
            "surveyor": self.cmb_surveyor.get(),
            "honorarios": honorarios_val,
            "costo_operativo": costo_op_val,
            "fecha_inicio": self.fecha_inicio.get(),
            "hora_inicio": self.hora_inicio.get(),
        }

        resp = post_servicio(data)
        if resp.get("status") == "OK":
            messagebox.showinfo(
                "Éxito",
                "Servicio registrado correctamente"
            )
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error API", resp)
