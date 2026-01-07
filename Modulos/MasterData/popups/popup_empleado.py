import tkinter as tk
from tkinter import ttk

class PopupEmpleado(tk.Toplevel):

    # ----------------------------------------------
    # Constructor
    # ----------------------------------------------
    def __init__(self, parent, codigo, on_save=None):
        super().__init__(parent)
        self.title("Agregar Empleado")
        self.geometry("650x550")
        self.config(bg="white")
        self.resizable(False, False)

        self.on_save = on_save
        self.codigo_generado = codigo  # viene desde UI principal

        # Variables
        self.nombre      = tk.StringVar()
        self.apellidos   = tk.StringVar()
        self.pais        = tk.StringVar()
        self.nacionalidad = tk.StringVar()
        self.estado_civil = tk.StringVar()
        self.genero       = tk.StringVar()
        self.prefijo      = tk.StringVar()
        self.telefono     = tk.StringVar()
        self.provincia    = tk.StringVar()
        self.canton       = tk.StringVar()
        self.distrito     = tk.StringVar()
        self.direccion    = tk.StringVar()
        self.jornada      = tk.StringVar()
        self.salario      = tk.StringVar()
        self.frecuencia_pago = tk.StringVar()
        self.banco        = tk.StringVar()
        self.cuenta_iban  = tk.StringVar()
        self.moneda       = tk.StringVar()
        self.enfermedades = tk.StringVar()
        self.contacto_emergencia  = tk.StringVar()
        self.telefono_emergencia  = tk.StringVar()

        # Activos
        self.activo1  = tk.StringVar()
        self.marca1   = tk.StringVar()
        self.serial1  = tk.StringVar()
        self.activo2  = tk.StringVar()
        self.marca2   = tk.StringVar()
        self.serial2  = tk.StringVar()
        self.activo3  = tk.StringVar()
        self.marca3   = tk.StringVar()
        self.serial3  = tk.StringVar()

        self._build()

    # ----------------------------------------------
    # UI Builder con Notebook (Tabs)
    # ----------------------------------------------
    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        tab1 = tk.Frame(notebook, bg="white")
        tab2 = tk.Frame(notebook, bg="white")
        tab3 = tk.Frame(notebook, bg="white")
        tab4 = tk.Frame(notebook, bg="white")
        tab5 = tk.Frame(notebook, bg="white")

        notebook.add(tab1, text="📌 Datos Personales")
        notebook.add(tab2, text="📞 Contacto y Dirección")
        notebook.add(tab3, text="💼 Detalles Laborales")
        notebook.add(tab4, text="🏥 Emergencia y Salud")
        notebook.add(tab5, text="🎒 Activos")

        # ===================================================
        # TAB 1: Datos personales
        # ===================================================
        tk.Label(tab1, text=f"Código: {self.codigo_generado}", bg="white", fg="blue").grid(
            row=0, column=0, padx=10, pady=10, sticky="w", columnspan=2
        )

        tk.Label(tab1, text="Nombre:", bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombre = ttk.Entry(tab1, textvariable=self.nombre)
        self.entry_nombre.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(tab1, text="Apellidos:", bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_apellidos = ttk.Entry(tab1, textvariable=self.apellidos)
        self.entry_apellidos.grid(row=2, column=1, padx=10, pady=5)

        estados = ["Soltero", "Casado", "Unión libre", "Divorciado", "Separado", "Viudo", "Otro"]
        tk.Label(tab1, text="Estado civil:", bg="white").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.combo_estado_civil = ttk.Combobox(tab1, textvariable=self.estado_civil, values=estados, state="readonly")
        self.combo_estado_civil.grid(row=3, column=1, padx=10, pady=5)

        generos = ["Masculino", "Femenino", "Otro"]
        tk.Label(tab1, text="Género:", bg="white").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.combo_genero = ttk.Combobox(tab1, textvariable=self.genero, values=generos, state="readonly")
        self.combo_genero.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(tab1, text="Nacionalidad:", bg="white").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_nacionalidad = ttk.Entry(tab1, textvariable=self.nacionalidad)
        self.entry_nacionalidad.grid(row=5, column=1, padx=10, pady=5)

        # ===================================================
        # TAB 2: Contacto
        # ===================================================
        tk.Label(tab2, text="Prefijo:", bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        prefijos_america = ["+506", "+57", "+1"]
        self.combo_prefijo = ttk.Combobox(tab2, textvariable=self.prefijo, values=prefijos_america, state="readonly")
        self.combo_prefijo.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(tab2, text="Teléfono:", bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono = ttk.Entry(tab2, textvariable=self.telefono)
        self.entry_telefono.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(tab2, text="Provincia:", bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_provincia = ttk.Entry(tab2, textvariable=self.provincia)
        self.entry_provincia.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(tab2, text="Cantón:", bg="white").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_canton = ttk.Entry(tab2, textvariable=self.canton)
        self.entry_canton.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(tab2, text="Distrito:", bg="white").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_distrito = ttk.Entry(tab2, textvariable=self.distrito)
        self.entry_distrito.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(tab2, text="Dirección:", bg="white").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_direccion = ttk.Entry(tab2, textvariable=self.direccion, width=40)
        self.entry_direccion.grid(row=5, column=1, padx=10, pady=5)

        # ===================================================
        # TAB 3: Laboral
        # ===================================================
        jornadas = ["Tiempo completo", "Medio tiempo", "Por horas"]
        tk.Label(tab3, text="Jornada:", bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.combo_jornada = ttk.Combobox(tab3, textvariable=self.jornada, values=jornadas, state="readonly")
        self.combo_jornada.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(tab3, text="Salario:", bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_salario = ttk.Entry(tab3, textvariable=self.salario)
        self.entry_salario.grid(row=1, column=1, padx=10, pady=5)

        frecuencia = ["Mensual", "Quincenal", "Semanal"]
        tk.Label(tab3, text="Pago:", bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.combo_pago = ttk.Combobox(tab3, textvariable=self.frecuencia_pago, values=frecuencia, state="readonly")
        self.combo_pago.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(tab3, text="Banco:", bg="white").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_banco = ttk.Entry(tab3, textvariable=self.banco)
        self.entry_banco.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(tab3, text="Cuenta IBAN:", bg="white").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_cuenta_iban = ttk.Entry(tab3, textvariable=self.cuenta_iban)
        self.entry_cuenta_iban.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(tab3, text="Moneda:", bg="white").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        monedas = ["CRC", "USD", "EUR"]
        self.combo_moneda = ttk.Combobox(tab3, textvariable=self.moneda, values=monedas, state="readonly")
        self.combo_moneda.grid(row=5, column=1, padx=10, pady=5)

        # ===================================================
        # TAB 4: Salud y Emergencia
        # ===================================================
        tk.Label(tab4, text="Enfermedades:", bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_enfermedades = ttk.Entry(tab4, textvariable=self.enfermedades, width=40)
        self.entry_enfermedades.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(tab4, text="Contacto emergencia:", bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_contacto_emergencia = ttk.Entry(tab4, textvariable=self.contacto_emergencia)
        self.entry_contacto_emergencia.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(tab4, text="Tel. emergencia:", bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono_emergencia = ttk.Entry(tab4, textvariable=self.telefono_emergencia)
        self.entry_telefono_emergencia.grid(row=2, column=1, padx=10, pady=5)

        # ===================================================
        # TAB 5: Activos
        # ===================================================
        tk.Label(tab5, text="Activo 1:", bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_activo1 = ttk.Entry(tab5, textvariable=self.activo1)
        self.entry_activo1.grid(row=0, column=1, padx=10, pady=5)
        self.entry_marca1 = ttk.Entry(tab5, textvariable=self.marca1, width=18)
        self.entry_marca1.grid(row=0, column=2, padx=5)
        self.entry_serial1 = ttk.Entry(tab5, textvariable=self.serial1, width=18)
        self.entry_serial1.grid(row=0, column=3, padx=5)

        tk.Label(tab5, text="Activo 2:", bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_activo2 = ttk.Entry(tab5, textvariable=self.activo2)
        self.entry_activo2.grid(row=1, column=1, padx=10, pady=5)
        self.entry_marca2 = ttk.Entry(tab5, textvariable=self.marca2, width=18)
        self.entry_marca2.grid(row=1, column=2, padx=5)
        self.entry_serial2 = ttk.Entry(tab5, textvariable=self.serial2, width=18)
        self.entry_serial2.grid(row=1, column=3, padx=5)

        tk.Label(tab5, text="Activo 3:", bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_activo3 = ttk.Entry(tab5, textvariable=self.activo3)
        self.entry_activo3.grid(row=2, column=1, padx=10, pady=5)
        self.entry_marca3 = ttk.Entry(tab5, textvariable=self.marca3, width=18)
        self.entry_marca3.grid(row=2, column=2, padx=5)
        self.entry_serial3 = ttk.Entry(tab5, textvariable=self.serial3, width=18)
        self.entry_serial3.grid(row=2, column=3, padx=5)

        # BOTÓN GUARDAR
        tk.Button(self, text="Guardar", bg="#008C35", fg="white", width=15, command=self._guardar).pack(pady=10)

    # ----------------------------------------------
    # Acción Guardar
    # ----------------------------------------------
    def _guardar(self):
        data = {
            "codigo": self.codigo_generado,
            "nombre": self.entry_nombre.get().strip(),
            "apellidos": self.entry_apellidos.get().strip(),
            "estado_civil": self.combo_estado_civil.get().strip(),
            "genero": self.combo_genero.get().strip(),
            "prefijo": self.combo_prefijo.get().strip(),
            "telefono": self.entry_telefono.get().strip(),
            "provincia": self.entry_provincia.get().strip(),
            "canton": self.entry_canton.get().strip(),
            "distrito": self.entry_distrito.get().strip(),
            "direccion": self.entry_direccion.get().strip(),
            "jornada": self.combo_jornada.get().strip(),
            "salario": self.entry_salario.get().strip(),
            "pago": self.combo_pago.get().strip(),
            "banco": self.entry_banco.get().strip(),
            "cuenta_iban": self.entry_cuenta_iban.get().strip(),
            "moneda": self.combo_moneda.get().strip(),
            "enfermedades": self.entry_enfermedades.get().strip(),
            "contacto_emergencia": self.entry_contacto_emergencia.get().strip(),
            "telefono_emergencia": self.entry_telefono_emergencia.get().strip(),
            "activo1": self.entry_activo1.get().strip(),
            "marca1": self.entry_marca1.get().strip(),
            "serial1": self.entry_serial1.get().strip(),
            "activo2": self.entry_activo2.get().strip(),
            "marca2": self.entry_marca2.get().strip(),
            "serial2": self.entry_serial2.get().strip(),
            "activo3": self.entry_activo3.get().strip(),
            "marca3": self.entry_marca3.get().strip(),
            "serial3": self.entry_serial3.get().strip(),
        }

        print("💾 Guardar Empleado →", data)

        if self.on_save:
            self.on_save(data)

        self.destroy()

        print("💾 Guardar Empleado →", data)

        if self.on_save:
            self.on_save(data)

        self.destroy()

