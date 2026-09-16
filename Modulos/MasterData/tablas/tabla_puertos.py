import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    delete_masterdata_port_api,
    get_continentes_cpp_api,
    get_masterdata_ports_api,
    get_paises_cpp_api,
    get_puertos_cpp_api,
    post_masterdata_port_api,
    put_masterdata_port_api,
)
from Modulos.MasterData.tablas.base_table import BasePaginatedTable


class TablaPuertosUI(BasePaginatedTable):
    def __init__(self, parent, on_back):
        super().__init__(parent, title="Continentes / Paises / Puertos", on_back=on_back)
        self.columns = [
            ("id", "ID"),
            ("continente", "Continente"),
            ("pais", "Pais"),
            ("puerto", "Puerto"),
        ]
        self._configurar_columnas()
        self._build_filters()
        self.btn_ver.config(command=self.ver_registro)
        self.btn_editar.config(command=self.editar_registro)
        self.btn_eliminar.config(command=self.eliminar_registro)
        self.btn_nuevo = tk.Button(self.toolbar, text="Agregar puerto", width=14, bg="#005A9C", fg="white", command=self.agregar_registro)
        self.btn_nuevo.pack(side="left", padx=4)
        self._load_continentes()
        self._set_empty_state()

    def _build_filters(self):
        self.filter_frame = tk.Frame(self, bg="white")
        self.filter_frame.pack(fill="x", padx=6, pady=4, before=self.table_frame)
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()

        tk.Label(self.filter_frame, text="Continente", bg="white").grid(row=0, column=0, padx=4, sticky="e")
        self.cbo_continente = ttk.Combobox(self.filter_frame, textvariable=self.continente_var, state="readonly", width=24)
        self.cbo_continente.grid(row=0, column=1, padx=4, sticky="w")
        self.cbo_continente.bind("<<ComboboxSelected>>", lambda *_: self._on_continente_change())

        tk.Label(self.filter_frame, text="Pais", bg="white").grid(row=0, column=2, padx=4, sticky="e")
        self.cbo_pais = ttk.Combobox(self.filter_frame, textvariable=self.pais_var, state="readonly", width=24)
        self.cbo_pais.grid(row=0, column=3, padx=4, sticky="w")
        self.cbo_pais.bind("<<ComboboxSelected>>", lambda *_: self._on_pais_change())

        tk.Label(self.filter_frame, text="Puerto", bg="white").grid(row=0, column=4, padx=4, sticky="e")
        self.cbo_puerto = ttk.Combobox(self.filter_frame, textvariable=self.puerto_var, state="normal", width=24)
        self.cbo_puerto.grid(row=0, column=5, padx=4, sticky="w")

        tk.Button(self.filter_frame, text="Buscar", bg="#003A75", fg="white", width=12, command=self._buscar).grid(row=0, column=6, padx=8)
        tk.Button(self.filter_frame, text="Limpiar", width=12, command=self._limpiar).grid(row=0, column=7, padx=4)

    def _load_continentes(self):
        try:
            values = get_continentes_cpp_api()
            self.cbo_continente["values"] = values
        except Exception as e:
            messagebox.showerror("Puertos", f"No se pudieron cargar continentes:\n{e}")

    def _on_continente_change(self):
        self.pais_var.set("")
        self.puerto_var.set("")
        self.cbo_pais["values"] = []
        self.cbo_puerto["values"] = []
        continente = self.continente_var.get().strip()
        if not continente:
            return
        try:
            self.cbo_pais["values"] = get_paises_cpp_api(continente)
        except Exception as e:
            messagebox.showerror("Puertos", f"No se pudieron cargar paises:\n{e}")

    def _on_pais_change(self):
        self.puerto_var.set("")
        self.cbo_puerto["values"] = []
        pais = self.pais_var.get().strip()
        if not pais:
            return
        try:
            self.cbo_puerto["values"] = get_puertos_cpp_api(pais, self.continente_var.get().strip() or None)
        except Exception as e:
            messagebox.showerror("Puertos", f"No se pudieron cargar puertos:\n{e}")

    def _configurar_columnas(self):
        self.table["columns"] = [c[0] for c in self.columns]
        for col, texto in self.columns:
            self.table.heading(col, text=texto)
            width = 70 if col == "id" else 210
            self.table.column(col, width=width, stretch=True, anchor="center")

    def _set_empty_state(self):
        self.total_items = 0
        self.lbl_page.config(text="Presione Buscar")
        self.table.delete(*self.table.get_children())

    def _buscar(self):
        self.page = 1
        self.refresh()

    def _limpiar(self):
        self.continente_var.set("")
        self.pais_var.set("")
        self.puerto_var.set("")
        self.cbo_pais["values"] = []
        self.cbo_puerto["values"] = []
        self._set_empty_state()

    def load_data(self):
        try:
            data = get_masterdata_ports_api(
                page=self.page,
                page_size=self.page_size,
                continente=self.continente_var.get().strip() or None,
                pais=self.pais_var.get().strip() or None,
                puerto=self.puerto_var.get().strip() or None,
            )
            self.total_items = data.get("total", 0)
            rows = data.get("data", [])
            total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
            self.lbl_page.config(text=f"Pagina {self.page} / {total_pages} - {self.total_items} registros")
            self.table.delete(*self.table.get_children())
            for row in rows:
                self.table.insert("", "end", values=[row.get(col, "") for col, _ in self.columns])
        except Exception as e:
            messagebox.showerror("Puertos", str(e))

    def _selected_values(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Puertos", "Seleccione un puerto primero")
            return None
        values = self.table.item(sel[0])["values"]
        return dict(zip([c[0] for c in self.columns], values))

    def _open_form(self, row=None, readonly=False):
        win = tk.Toplevel(self)
        win.title("Puerto")
        win.geometry("520x280")
        win.configure(bg="white")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        vars_by_key = {
            "id": tk.StringVar(value=str((row or {}).get("id", "Automatico"))),
            "continente": tk.StringVar(value=(row or {}).get("continente", "")),
            "pais": tk.StringVar(value=(row or {}).get("pais", "")),
            "puerto": tk.StringVar(value=(row or {}).get("puerto", "")),
        }
        body = tk.Frame(win, bg="white", padx=16, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="ID", bg="white").grid(row=0, column=0, sticky="e", pady=6, padx=6)
        id_entry = tk.Entry(body, textvariable=vars_by_key["id"], width=34, state="readonly")
        id_entry.grid(row=0, column=1, sticky="w", pady=6, padx=6)

        tk.Label(body, text="Continente", bg="white").grid(row=1, column=0, sticky="e", pady=6, padx=6)
        cbo_cont = ttk.Combobox(body, textvariable=vars_by_key["continente"], width=32, state="readonly" if not readonly else "disabled")
        cbo_cont.grid(row=1, column=1, sticky="w", pady=6, padx=6)

        tk.Label(body, text="Pais", bg="white").grid(row=2, column=0, sticky="e", pady=6, padx=6)
        cbo_pais = ttk.Combobox(body, textvariable=vars_by_key["pais"], width=32, state="readonly" if not readonly else "disabled")
        cbo_pais.grid(row=2, column=1, sticky="w", pady=6, padx=6)

        tk.Label(body, text="Puerto", bg="white").grid(row=3, column=0, sticky="e", pady=6, padx=6)
        cbo_puerto = ttk.Combobox(body, textvariable=vars_by_key["puerto"], width=32, state="normal" if not readonly else "disabled")
        cbo_puerto.grid(row=3, column=1, sticky="w", pady=6, padx=6)

        def load_form_continentes():
            try:
                cbo_cont["values"] = get_continentes_cpp_api()
            except Exception:
                cbo_cont["values"] = []

        initial_load = {"active": True}

        def load_form_paises(*_):
            if not initial_load["active"]:
                vars_by_key["pais"].set("")
                vars_by_key["puerto"].set("")
            continente = vars_by_key["continente"].get().strip()
            if not continente:
                cbo_pais["values"] = []
                cbo_puerto["values"] = []
                return
            try:
                cbo_pais["values"] = get_paises_cpp_api(continente)
            except Exception:
                cbo_pais["values"] = []

        def load_form_puertos(*_):
            if not initial_load["active"]:
                vars_by_key["puerto"].set("")
            pais = vars_by_key["pais"].get().strip()
            if not pais:
                cbo_puerto["values"] = []
                return
            try:
                cbo_puerto["values"] = get_puertos_cpp_api(pais, vars_by_key["continente"].get().strip() or None)
            except Exception:
                cbo_puerto["values"] = []

        cbo_cont.bind("<<ComboboxSelected>>", load_form_paises)
        cbo_pais.bind("<<ComboboxSelected>>", load_form_puertos)
        load_form_continentes()
        if row:
            load_form_paises()
            load_form_puertos()
        initial_load["active"] = False

        actions = tk.Frame(body, bg="white")
        actions.grid(row=4, column=0, columnspan=2, pady=(14, 0), sticky="e")

        def save():
            payload = {key: var.get().strip() for key, var in vars_by_key.items()}
            if not all(payload.values()):
                messagebox.showwarning("Puertos", "Continente, pais y puerto son requeridos")
                return
            try:
                if row:
                    put_masterdata_port_api(int(row["id"]), payload)
                else:
                    post_masterdata_port_api(payload)
                win.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Puertos", str(e))

        tk.Button(actions, text="Cerrar" if readonly else "Cancelar", width=10, command=win.destroy).pack(side="right", padx=4)
        if not readonly:
            tk.Button(actions, text="Guardar", width=10, bg="#00703C", fg="white", command=save).pack(side="right", padx=4)

    def agregar_registro(self):
        self._open_form()

    def ver_registro(self):
        row = self._selected_values()
        if row:
            self._open_form(row, readonly=True)

    def editar_registro(self):
        row = self._selected_values()
        if row:
            self._open_form(row)

    def eliminar_registro(self):
        row = self._selected_values()
        if not row:
            return
        if not messagebox.askyesno("Puertos", f"Eliminar puerto {row.get('puerto')}?"):
            return
        try:
            delete_masterdata_port_api(int(row["id"]))
            self.refresh()
        except Exception as e:
            messagebox.showerror("Puertos", str(e))
