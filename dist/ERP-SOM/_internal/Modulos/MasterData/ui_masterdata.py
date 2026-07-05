import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
from Modulos.MasterData.popups.popup_empleado import PopupEmpleado



COLOR_MENU = "#003A75"
COLOR_BG = "white"

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


class MasterDataUI(tk.Frame):

    def __init__(self, parent, go_back_callback=None):
        super().__init__(parent, bg=COLOR_BG)
        self.go_back_callback = go_back_callback

        # Variables de filtro
        self.tipo_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()

        # Construcción de UI
        self._build_filtros()
        self._build_acciones()

        # Cargar continentes al inicio
        self.after(100, self.load_continentes)

        # Frame donde se cargan tablas (vacío al inicio)
        self.table_frame = tk.Frame(self, bg=COLOR_BG)
        self.table_frame.pack(fill="both", expand=True)


    # ======================================================
    # FILTROS DE BÚSQUEDA
    # ======================================================
    def _build_filtros(self):
        frame = tk.LabelFrame(self, text="Buscar", bg=COLOR_BG, fg=COLOR_MENU)
        frame.pack(fill="x", pady=10)

        # Tipo
        ttk.Label(frame, text="Tipo:", background=COLOR_BG).grid(row=0, column=0, padx=5)
        self.cbo_tipo = ttk.Combobox(
            frame,
            textvariable=self.tipo_var,
            state="readonly",
            values=["Todos", "Empleado", "Surveyor", "Cliente", "Proveedor", "Servicio"],
            width=14
        )
        self.cbo_tipo.grid(row=0, column=1, padx=5)
        self.cbo_tipo.set("Todos")

        # Continente
        ttk.Label(frame, text="Continente:", background=COLOR_BG).grid(row=0, column=2, padx=5)
        self.cbo_cont = ttk.Combobox(
            frame,
            textvariable=self.continente_var,
            state="readonly",
            width=18
        )
        self.cbo_cont.grid(row=0, column=3, padx=5)
        self.cbo_cont.bind("<<ComboboxSelected>>", self._on_continente_selected)

        # País
        ttk.Label(frame, text="País:", background=COLOR_BG).grid(row=0, column=4, padx=5)
        self.cbo_pais = ttk.Combobox(
            frame,
            textvariable=self.pais_var,
            state="readonly",
            width=18
        )
        self.cbo_pais.grid(row=0, column=5, padx=5)
        self.cbo_pais.bind("<<ComboboxSelected>>", self._on_pais_selected)

        # Puerto
        ttk.Label(frame, text="Puerto:", background=COLOR_BG).grid(row=0, column=6, padx=5)
        self.cbo_puerto = ttk.Combobox(
            frame,
            textvariable=self.puerto_var,
            state="readonly",
            width=18
        )
        self.cbo_puerto.grid(row=0, column=7, padx=5)

        # Botón Buscar
        btn_buscar = tk.Button(
            frame,
            text="Buscar",
            bg=COLOR_MENU,
            fg="white",
            width=12,
            command=self.buscar
        )
        btn_buscar.grid(row=0, column=8, padx=10)

    # ======================================================
    # ACCIONES (BOTONES DE AGREGAR)
    # ======================================================
    def _build_acciones(self):
        frame = tk.Frame(self, bg=COLOR_BG)
        frame.pack(fill="x", pady=20)

        btn_emp = tk.Button(frame, text="➕ Empleado", bg="#005A9C", fg="white",
                            width=15, command=self._add_empleado)
        btn_emp.grid(row=0, column=0, padx=5)

        btn_surv = tk.Button(frame, text="➕ Surveyor", bg="#005A9C", fg="white",
                             width=15, command=self._add_surveyor)
        btn_surv.grid(row=0, column=1, padx=5)

        btn_cli = tk.Button(frame, text="➕ Cliente", bg="#005A9C", fg="white",
                            width=15, command=self._add_cliente)
        btn_cli.grid(row=0, column=2, padx=5)

        btn_prov = tk.Button(frame, text="➕ Proveedor", bg="#005A9C", fg="white",
                             width=15, command=self._add_proveedor)
        btn_prov.grid(row=0, column=3, padx=5)  # 👈 misma fila

        btn_serv = tk.Button(frame, text="➕ Servicio", bg="#005A9C", fg="white",
                             width=15, command=self._add_servicio)
        btn_serv.grid(row=0, column=4, padx=5)


    # ======================================================
    # TABLA RESULTADOS
    # ======================================================
    def _build_table(self):
        self.table_frame = tk.Frame(self, bg=COLOR_BG)
        self.table_frame.pack(fill="both", expand=True)

        self.table = ttk.Treeview(
            self.table_frame,
            columns=("C1", "C2"),
            show="headings"
        )
        self.table.pack(fill="both", expand=True)

    # ======================================================
    # CARGA DE COMBOS DESDE API
    # ======================================================
    def load_continentes(self):
        try:
            url = f"{BASE_URL}/cpp/continentes"
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            res = response.json()
            self.cbo_cont["values"] = res
            self.cbo_cont.set("Seleccione")
            self.continente_var.set("Seleccione")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar continentes\n{e}"
            )

    def load_paises(self, *_):
        cont = self.cbo_cont.get()

        if not cont or cont == "Seleccione":
            self.cbo_pais["values"] = []
            self.cbo_pais.set("")
            self.cbo_puerto["values"] = []
            self.cbo_puerto.set("")
            return

        try:
            url = f"{BASE_URL}/cpp/paises?continente={cont}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            res = response.json()
            self.cbo_pais["values"] = res
            self.cbo_pais.set("Seleccione")
            self.pais_var.set("Seleccione")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar países\n{e}"
            )

    def load_puertos(self, *_):
        pais = self.cbo_pais.get()

        if not pais or pais == "Seleccione":
            self.cbo_puerto["values"] = []
            self.cbo_puerto.set("")
            return

        try:
            url = f"{BASE_URL}/cpp/puertos?pais={pais}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            res = response.json()
            self.cbo_puerto["values"] = res
            self.cbo_puerto.set("Seleccione")
            self.puerto_var.set("Seleccione")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar puertos\n{e}"
            )

    # ======================================================
    # HANDLERS DE EVENTO
    # ======================================================
    def _on_continente_selected(self, event=None):
        print("🌎 Cambio continente (handler):", self.continente_var.get())
        self.load_paises()

    def _on_pais_selected(self, event=None):
        print("🚢 Cambio país (handler):", self.pais_var.get())
        self.load_puertos()


    # ======================================================
    # BUSCAR (cambiar vista según categoría seleccionada)
    # ======================================================
    def buscar(self):
        tipo = self.tipo_var.get().strip()

        print(f"[DEBUG] Tipo seleccionado: {repr(tipo)}")  # <-- para ver qué llega

        if tipo == "Servicio":
            print("📌 Cargando tabla servicios...")
            self.mostrar_tabla_servicios()
            return

    # ======================================================
    # Acción del botón Buscar
    # ======================================================
    def buscar(self):
        tipo = self.tipo_var.get().strip()

        if tipo == "Servicio":
            self.mostrar_tabla_servicios()
            return

        if tipo == "Proveedor":
            self.mostrar_tabla_proveedores()
            return

        if tipo == "Cliente":
            self.mostrar_tabla_clientes()
            return

        if tipo == "Surveyor":
            self.mostrar_tabla_surveyores()
            return

        if tipo == "Empleado":
            self.mostrar_tabla_empleados()
            return


    # ======================================================
    # Mostrar tabla Clientes
    # ======================================================
    def mostrar_tabla_clientes(self):
        from Modulos.MasterData.tablas.tabla_clientes import TablaClientesUI

        # Ocultar vista anterior
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Crear nueva vista SAP
        tabla = TablaClientesUI(
            parent=self.table_frame,
            on_back=self._volver_inicio
        )
        tabla.pack(fill="both", expand=True)


        messagebox.showinfo("Próximamente", "Faltan otras tablas por implementar")

    # ======================================================
    # POPUP EMPLEADO
    # ======================================================
    def _add_empleado(self):
        from Modulos.MasterData.popups.popup_empleado import PopupEmpleado
        nuevo_codigo = "MSL-0001-E"
        PopupEmpleado(self, codigo=nuevo_codigo, on_save=self._empleado_guardado)

    def _empleado_guardado(self, data):
        print("🏁 Enviando empleado al API…")
        try:
            url = f"{BASE_URL}/empleados/add"
            response = requests.post(url, json=data, timeout=10)
            print("📥 Status:", response.status_code)
            if response.status_code == 200:
                messagebox.showinfo("✔", "Empleado guardado correctamente")
            else:
                messagebox.showerror("Error API", response.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))


    def _add_surveyor(self):
        from Modulos.MasterData.popups.popup_surveyor import PopupSurveyor
        from api_client import get_serviciosmd_api, get_puertos_all_api

        # 1. Obtener lista de operaciones desde ServiciosMD
        try:
            lista_operaciones = get_serviciosmd_api()
        except Exception as e:
            print("❌ Error cargando operaciones:", e)
            lista_operaciones = []

        # 2. Obtener lista de todos los puertos desde CPP
        try:
            lista_puertos = get_puertos_all_api()
        except Exception as e:
            print("❌ Error cargando puertos:", e)
            lista_puertos = []

        # 3. Generar código incremental
        try:
            url = f"{BASE_URL}/surveyores/ultimo"
            response = requests.get(url, timeout=10)
            data = response.json()

            ultimo = data.get("ultimo", 0)
            nuevo_num = f"{ultimo + 1:04d}"
            nuevo_codigo = f"MSL-{nuevo_num}-S"

        except Exception as e:
            messagebox.showerror("Error API", f"No se pudo generar el código: {e}")
            nuevo_codigo = "MSL-0001-S"

        # 4. Abrir popup con operaciones y puertos cargados
        popup = PopupSurveyor(
            self,
            codigo=nuevo_codigo,
            lista_operaciones=lista_operaciones,
            lista_puertos=lista_puertos,
            on_save=self._surveyor_guardado
        )

        popup.grab_set()
        popup.wait_window()


    def _surveyor_guardado(self, data):
        print("🏁 Enviando surveyor al API…")
        try:
            url = f"{BASE_URL}/surveyores/add"
            response = requests.post(url, json=data, timeout=10)
            print("📥 Status:", response.status_code)
            if response.status_code == 200:
                messagebox.showinfo("✔", "Surveyor guardado correctamente")
            else:
                messagebox.showerror("Error API", response.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))


    # ======================================================
    # POPUP CLIENTE
    # ======================================================
    def _add_cliente(self):
        from Modulos.MasterData.popups.popup_cliente import PopupCliente

        try:
            # Obtener consecutivo desde el API
            url = f"{BASE_URL}/clientes/ultimo"
            response = requests.get(url, timeout=10)
            data = response.json()

            # Leer llave correcta
            ultimo = data.get("ultimo", 0)

            # Generar consecutivo
            nuevo_num = f"{ultimo + 1:04d}"
            nuevo_codigo = f"MSL-{nuevo_num}-C"

        except Exception as e:
            messagebox.showerror("Error API", f"No se pudo generar el código: {e}")
            return

        popup = PopupCliente(self, codigo=nuevo_codigo, on_save=self._cliente_guardado)
        popup.grab_set()
        popup.wait_window()


    def _cliente_guardado(self, data):
        print("🏁 Enviando cliente al API…")
        try:
            url = f"{BASE_URL}/clientes/add"
            response = requests.post(url, json=data, timeout=10)
            print("📥 Status:", response.status_code)
            if response.status_code == 200:
                messagebox.showinfo("✔", "Cliente guardado correctamente")
            else:
                messagebox.showerror("Error API", response.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))



    # ======================================================
    # POPUP PROVEEDOR (CÓDIGO ÚNICO DESDE API)
    # ======================================================
    def _add_proveedor(self):
        from Modulos.MasterData.popups.popup_proveedor import PopupProveedor

        try:
            # ENDPOINT CORRECTO DEL BACKEND
            url = f"{BASE_URL}/proveedores/ultimo"
            response = requests.get(url, timeout=10)
            data = response.json()

            # LLAVE CORRECTA DEL JSON
            ultimo = data.get("ultimo", 0)

            # GENERAR SIGUIENTE CONSECUTIVO
            nuevo_num = f"{ultimo + 1:04d}"
            nuevo_codigo = f"MSL-{nuevo_num}-P"

        except Exception as e:
            messagebox.showerror("Error API", f"No se pudo generar el código: {e}")
            return

        popup = PopupProveedor(self, codigo=nuevo_codigo, on_save=self._proveedor_guardado)
        popup.grab_set()
        popup.wait_window()

    # ======================================================
    # Guardar proveedor en API
    # ======================================================
    def _proveedor_guardado(self, data):
        try:
            url = f"{BASE_URL}/proveedores/add"
            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                messagebox.showinfo("✔", "Proveedor guardado correctamente")
            else:
                messagebox.showerror("Error API", response.text)

        except Exception as e:
            messagebox.showerror("Error API", str(e))


    # ======================================================
    # POPUP SERVICIO
    # ======================================================
    def _add_servicio(self):
        from Modulos.MasterData.popups.popup_servicio import PopupServicio
        import requests

        try:
            # 🔹 Usar el router correcto de ServiciosMD
            url = f"{BASE_URL}/servicios_md/ultimo"
            response = requests.get(url, timeout=25)
            data = response.json()

            # "ultimo" viene del backend (MAX del código en ServiciosMD)
            ultimo = data.get("ultimo", 0)

            # Generar siguiente consecutivo
            nuevo_num = str(ultimo + 1).zfill(4)   # 0001, 0002, 0003...
            nuevo_codigo = f"MSL-{nuevo_num}-S"
        except Exception as e:
            print("❌ Error generando código servicio:", e)
            # Fallback si algo falla
            nuevo_codigo = "MSL-0001-S"

        popup = PopupServicio(self, codigo=nuevo_codigo, on_save=self._servicio_guardado)
        popup.grab_set()
        popup.wait_window()


    # ======================================================
    # POPUP Guardar servicio
    # ======================================================

    def _servicio_guardado(self, data):
        print("🏁 Enviando servicio al API…")
        try:
            url = f"{BASE_URL}/servicios_md/add"
            response = requests.post(url, json=data, timeout=10)
            print("📥 Status:", response.status_code)
            print("📥 Respuesta:", response.text)
            if response.status_code == 200:
                messagebox.showinfo("✔", "Servicio guardado correctamente")
            else:
                messagebox.showerror("Error API", response.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))



    # ======================================================
    # Mostrar tabla Servicios
    # ======================================================
    def mostrar_tabla_servicios(self):
        from Modulos.MasterData.tablas.tabla_servicios import TablaServiciosUI
        
        # Ocultar vista anterior de tabla (placeholder)
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Crear nueva vista SAP
        tabla = TablaServiciosUI(
            parent=self.table_frame,
            on_back=self._volver_inicio
        )
        tabla.pack(fill="both", expand=True)

    # ======================================================
    # Mostrar tabla Proveedores
    # ======================================================
    def mostrar_tabla_proveedores(self):
        from Modulos.MasterData.tablas.tabla_proveedores import TablaProveedoresUI

        # Ocultar vista anterior
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Crear nueva vista SAP
        tabla = TablaProveedoresUI(
            parent=self.table_frame,
            on_back=self._volver_inicio
        )
        tabla.pack(fill="both", expand=True)


    # ======================================================
    # Mostrar tabla Surveyores
    # ======================================================
    def mostrar_tabla_surveyores(self):
        from Modulos.MasterData.tablas.tabla_surveyores import TablaSurveyoresUI

        # Ocultar vista anterior
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Crear nueva vista SAP
        tabla = TablaSurveyoresUI(
            parent=self.table_frame,
            on_back=self._volver_inicio
        )
        tabla.pack(fill="both", expand=True)


    # ======================================================
    # Mostrar tabla Empleados
    # ======================================================
    def mostrar_tabla_empleados(self):
        from Modulos.MasterData.tablas.tabla_empleados import TablaEmpleadosUI

        # Ocultar vista anterior
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Crear nueva vista
        tabla = TablaEmpleadosUI(
            parent=self.table_frame,
            on_back=self._volver_inicio
        )
        tabla.pack(fill="both", expand=True)



    # ======================================================
    # Volver al inicio (vista original sin tabla)
    # ======================================================
    def _volver_inicio(self):
        for w in self.table_frame.winfo_children():
            w.destroy()

