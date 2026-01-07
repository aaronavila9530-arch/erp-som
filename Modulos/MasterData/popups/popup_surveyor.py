import tkinter as tk
from tkinter import ttk

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

        # Variables
        self.nombre = tk.StringVar()
        self.apellidos = tk.StringVar()
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
        self.cuenta_iban = tk.StringVar()
        self.moneda = tk.StringVar()
        self.swift = tk.StringVar()
        self.uid = tk.StringVar()
        self.enfermedades = tk.StringVar()
        self.contacto_emergencia = tk.StringVar()
        self.telefono_emergencia = tk.StringVar()
        self.puerto = tk.StringVar()

        self._build()

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, bg="white")  # Datos personales
        tab2 = tk.Frame(notebook, bg="white")  # Contacto
        tab3 = tk.Frame(notebook, bg="white")  # Laboral
        tab4 = tk.Frame(notebook, bg="white")  # Salud
        tab5 = tk.Frame(notebook, bg="white")  # Operación & Puertos

        notebook.add(tab1, text="📌 Datos Personales")
        notebook.add(tab2, text="📞 Contacto")
        notebook.add(tab3, text="💼 Laboral")
        notebook.add(tab4, text="🏥 Salud")
        notebook.add(tab5, text="⚓ Operaciones")

        # ==========================
        # TAB 1 — Datos personales
        # ==========================
        ttk.Label(tab1, text=f"Código: {self.codigo_generado}",
                  background="white", foreground="blue") \
            .grid(row=0, column=0, padx=10, pady=10, columnspan=2, sticky="w")

        ttk.Label(tab1, text="Nombre:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombre = ttk.Entry(tab1, textvariable=self.nombre)
        self.entry_nombre.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Apellidos:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_apellidos = ttk.Entry(tab1, textvariable=self.apellidos)
        self.entry_apellidos.grid(row=2, column=1, padx=10, pady=5)

        estados = ["Soltero", "Casado", "Unión libre", "Divorciado", "Separado", "Viudo", "Otro"]
        ttk.Label(tab1, text="Estado civil:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.combo_estado_civil = ttk.Combobox(tab1, textvariable=self.estado_civil,
                                               values=estados, state="readonly")
        self.combo_estado_civil.grid(row=3, column=1, padx=10, pady=5)

        generos = ["Masculino", "Femenino", "Otro"]
        ttk.Label(tab1, text="Género:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.combo_genero = ttk.Combobox(tab1, textvariable=self.genero,
                                         values=generos, state="readonly")
        self.combo_genero.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Nacionalidad:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_nacionalidad = ttk.Entry(tab1, textvariable=self.nacionalidad)
        self.entry_nacionalidad.grid(row=5, column=1, padx=10, pady=5)

        # ==========================
        # TAB 2 — Contacto
        # ==========================
        ttk.Label(tab2, text="Prefijo:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        prefijos_america = ["+506", "+57", "+1"]
        self.combo_prefijo = ttk.Combobox(tab2, textvariable=self.prefijo,
                                          values=prefijos_america, state="readonly")
        self.combo_prefijo.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Teléfono:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono = ttk.Entry(tab2, textvariable=self.telefono)
        self.entry_telefono.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Provincia:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_provincia = ttk.Entry(tab2, textvariable=self.provincia)
        self.entry_provincia.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Cantón:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_canton = ttk.Entry(tab2, textvariable=self.canton)
        self.entry_canton.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Distrito:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_distrito = ttk.Entry(tab2, textvariable=self.distrito)
        self.entry_distrito.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Dirección exacta:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_direccion = ttk.Entry(tab2, textvariable=self.direccion, width=40)
        self.entry_direccion.grid(row=5, column=1, padx=10, pady=5)

        # ==========================
        # TAB 3 — Laboral
        # ==========================
        ttk.Label(tab3, text="Jornada:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        jornadas = ["Tiempo completo", "Medio tiempo", "Por horas"]
        self.combo_jornada = ttk.Combobox(tab3, textvariable=self.jornada,
                                          values=jornadas, state="readonly")
        self.combo_jornada.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Pago:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        frecuencia = ["Mensual", "Quincenal", "Semanal"]
        self.combo_pago = ttk.Combobox(tab3, textvariable=self.frecuencia_pago,
                                       values=frecuencia, state="readonly")
        self.combo_pago.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Banco:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_banco = ttk.Entry(tab3, textvariable=self.banco)
        self.entry_banco.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Cuenta IBAN:", background="white") \
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_cuenta_iban = ttk.Entry(tab3, textvariable=self.cuenta_iban)
        self.entry_cuenta_iban.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Swift Code:", background="white") \
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_swift = ttk.Entry(tab3, textvariable=self.swift)
        self.entry_swift.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="UID:", background="white") \
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_uid = ttk.Entry(tab3, textvariable=self.uid)
        self.entry_uid.grid(row=5, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Moneda:", background="white") \
            .grid(row=6, column=0, padx=10, pady=5, sticky="w")
        monedas = ["CRC", "USD", "EUR"]
        self.combo_moneda = ttk.Combobox(tab3, textvariable=self.moneda,
                                         values=monedas, state="readonly")
        self.combo_moneda.grid(row=6, column=1, padx=10, pady=5)


        # ==========================
        # TAB 4 — Salud
        # ==========================
        ttk.Label(tab4, text="Enfermedades:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_enfermedades = ttk.Entry(tab4, textvariable=self.enfermedades, width=40)
        self.entry_enfermedades.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab4, text="Contacto emergencia:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_contacto_emergencia = ttk.Entry(tab4, textvariable=self.contacto_emergencia)
        self.entry_contacto_emergencia.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab4, text="Tel. emergencia:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono_emergencia = ttk.Entry(tab4, textvariable=self.telefono_emergencia)
        self.entry_telefono_emergencia.grid(row=2, column=1, padx=10, pady=5)

        # ==========================
        # TAB 5 — Operación & Puertos
        # ==========================
        ttk.Label(tab5, text="Operación:", background="white") \
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.combo_operacion = ttk.Combobox(tab5, textvariable=self.operacion,
                                           values=self.lista_operaciones, state="readonly")
        self.combo_operacion.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab5, text="Honorario:", background="white") \
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_honorario = ttk.Entry(tab5, textvariable=self.honorario)
        self.entry_honorario.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab5, text="Puertos que atiende:", background="white") \
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.combo_puerto = ttk.Combobox(tab5, textvariable=self.puerto,
                                        values=self.lista_puertos, state="readonly")
        self.combo_puerto.grid(row=2, column=1, padx=10, pady=5)

        # ==========================
        # BOTÓN GUARDAR
        # ==========================
        tk.Button(self, text="Guardar", bg="#008C35", fg="white",
                  width=15, command=self._guardar).pack(pady=10)

    def _guardar(self):
        data = {
            "codigo": self.codigo_generado,
            "nombre": self.entry_nombre.get().strip(),
            "apellidos": self.entry_apellidos.get().strip(),
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
            "cuenta_iban": self.entry_cuenta_iban.get().strip(),
            "moneda": self.combo_moneda.get().strip(),
            "swift": self.entry_swift.get().strip(),
            "uid": self.entry_uid.get().strip(),
            "enfermedades": self.entry_enfermedades.get().strip(),
            "contacto_emergencia": self.entry_contacto_emergencia.get().strip(),
            "telefono_emergencia": self.entry_telefono_emergencia.get().strip(),
            "puerto": self.combo_puerto.get().strip(),
        }

        print("💾 Guardar Surveyor →", data)

        if self.on_save:
            self.on_save(data)

        self.destroy()
