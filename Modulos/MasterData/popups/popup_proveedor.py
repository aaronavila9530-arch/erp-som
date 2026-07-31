import tkinter as tk
from tkinter import ttk
from Modulos.MasterData.prefijos_telefonicos import PREFIJOS_TELEFONICOS

class PopupProveedor(tk.Toplevel):

    def __init__(self, parent, codigo, on_save=None):
        super().__init__(parent)
        self.title("Agregar Proveedor")
        self.geometry("720x600")
        self.config(bg="white")
        self.resizable(False, False)

        self.on_save = on_save
        self.codigo_generado = codigo

        # Variables
        self.Nombre = tk.StringVar()
        self.Apellidos = tk.StringVar()
        self.NombreComercial = tk.StringVar()
        self.Cedula = tk.StringVar()
        self.Pais = tk.StringVar()
        self.Provincia = tk.StringVar()
        self.Canton = tk.StringVar()
        self.Distrito = tk.StringVar()
        self.DireccionExacta = tk.StringVar()
        self.Prefijo = tk.StringVar()
        self.Telefono = tk.StringVar()
        self.Correo = tk.StringVar()
        self.TerminosPago = tk.StringVar()
        self.Banco = tk.StringVar()
        self.CuentaIBAN = tk.StringVar()
        self.SwiftCode = tk.StringVar()
        self.UID = tk.StringVar()
        self.DireccionBanco = tk.StringVar()
        self.TipoProveeduria = tk.StringVar()
        self.Comentarios = tk.StringVar()

        self._build()

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, bg="white")
        tab2 = tk.Frame(notebook, bg="white")
        tab3 = tk.Frame(notebook, bg="white")
        tab4 = tk.Frame(notebook, bg="white")

        notebook.add(tab1, text="Datos")
        notebook.add(tab2, text="Contacto & Ubicación")
        notebook.add(tab3, text="Bancario")
        notebook.add(tab4, text="Proveeduría")

        # ================= TAB 1 ==================
        ttk.Label(tab1, text=f"Código: {self.codigo_generado}", background="white", foreground="blue")\
            .grid(row=0, column=0, padx=10, pady=10, sticky="w", columnspan=2)

        ttk.Label(tab1, text="Nombre:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombre = ttk.Entry(tab1, textvariable=self.Nombre)
        self.entry_nombre.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Apellidos:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_apellidos = ttk.Entry(tab1, textvariable=self.Apellidos)
        self.entry_apellidos.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Nombre Comercial:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombrecom = ttk.Entry(tab1, textvariable=self.NombreComercial)
        self.entry_nombrecom.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Cédula / VAT:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_cedula = ttk.Entry(tab1, textvariable=self.Cedula)
        self.entry_cedula.grid(row=4, column=1, padx=10, pady=5)


        # ================= TAB 2 ==================
        ttk.Label(tab2, text="País:", background="white")\
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_pais = ttk.Entry(tab2, textvariable=self.Pais)
        self.entry_pais.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Provincia:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_provincia = ttk.Entry(tab2, textvariable=self.Provincia)
        self.entry_provincia.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Cantón:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_canton = ttk.Entry(tab2, textvariable=self.Canton)
        self.entry_canton.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Distrito:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_distrito = ttk.Entry(tab2, textvariable=self.Distrito)
        self.entry_distrito.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Dirección:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_direccion = ttk.Entry(tab2, textvariable=self.DireccionExacta, width=40)
        self.entry_direccion.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Prefijo:", background="white")\
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.combo_prefijo = ttk.Combobox(tab2, textvariable=self.Prefijo, values=PREFIJOS_TELEFONICOS, state="readonly")
        self.combo_prefijo.grid(row=5, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Teléfono:", background="white")\
            .grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono = ttk.Entry(tab2, textvariable=self.Telefono)
        self.entry_telefono.grid(row=6, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Correo:", background="white")\
            .grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.entry_correo = ttk.Entry(tab2, textvariable=self.Correo)
        self.entry_correo.grid(row=7, column=1, padx=10, pady=5)


        # ================= TAB 3 ==================
        ttk.Label(tab3, text="Términos de pago:", background="white")\
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_terminos = ttk.Entry(tab3, textvariable=self.TerminosPago)
        self.entry_terminos.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Banco:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_banco = ttk.Entry(tab3, textvariable=self.Banco)
        self.entry_banco.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Cuenta IBAN:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_iban = ttk.Entry(tab3, textvariable=self.CuentaIBAN)
        self.entry_iban.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Swift Code:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_swift = ttk.Entry(tab3, textvariable=self.SwiftCode)
        self.entry_swift.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="UID:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_uid = ttk.Entry(tab3, textvariable=self.UID)
        self.entry_uid.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Dirección Banco:", background="white")\
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_dirbanco = ttk.Entry(tab3, textvariable=self.DireccionBanco, width=40)
        self.entry_dirbanco.grid(row=5, column=1, padx=10, pady=5)


        # ================= TAB 4 ==================
        tipos = [
            "Limpieza", "Alimentación", "Contaduría", "Abogacía",
            "Consultoría Comercial", "Consultoría Legal",
            "Consultoría Impositiva", "Internet", "Renta Local",
            "Mantenimiento Vehicular", "Otro"
        ]

        ttk.Label(tab4, text="Tipo de Proveeduría:", background="white")\
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.combo_tipopro = ttk.Combobox(tab4, textvariable=self.TipoProveeduria, values=tipos, state="readonly")
        self.combo_tipopro.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab4, text="Comentarios:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_comentarios = ttk.Entry(tab4, textvariable=self.Comentarios, width=45)
        self.entry_comentarios.grid(row=1, column=1, padx=10, pady=5)

        # BOTÓN GUARDAR
        frame_btn = tk.Frame(self, bg="white")
        frame_btn.pack(fill="x", pady=10)

        tk.Button(
            frame_btn, text="Guardar", bg="#008C35", fg="white",
            width=18, command=self._guardar
        ).pack()

    def _guardar(self):
        data = {
            "Codigo": self.codigo_generado,
            "Nombre": self.entry_nombre.get().strip(),
            "Apellidos": self.entry_apellidos.get().strip(),
            "NombreComercial": self.entry_nombrecom.get().strip(),
            "Cedula": self.entry_cedula.get().strip(),
            "Pais": self.entry_pais.get().strip(),
            "Provincia": self.entry_provincia.get().strip(),
            "Canton": self.entry_canton.get().strip(),
            "Distrito": self.entry_distrito.get().strip(),
            "DireccionExacta": self.entry_direccion.get().strip(),
            "Prefijo": self.combo_prefijo.get().strip(),
            "Telefono": self.entry_telefono.get().strip(),
            "Correo": self.entry_correo.get().strip(),
            "TerminosPago": self.entry_terminos.get().strip(),
            "Banco": self.entry_banco.get().strip(),
            "CuentaIBAN": self.entry_iban.get().strip(),
            "SwiftCode": self.entry_swift.get().strip(),
            "UID": self.entry_uid.get().strip(),
            "DireccionBanco": self.entry_dirbanco.get().strip(),
            "TipoProveeduria": self.combo_tipopro.get().strip(),
            "Comentarios": self.entry_comentarios.get().strip(),
        }

        print("💾 Guardar Proveedor →", data)

        if self.on_save:
            self.on_save(data)

        # 👉 Cerrar popup DESPUÉS de enviar datos
        self.destroy()
