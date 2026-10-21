# ============================================================
# COMERCIAL — COTIZACIONES UI
# Archivo: Modulos/Comercial/comercial_cotizaciones_ui.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu, simpledialog
import math
import pandas as pd
from Modulos.Servicios.popup_servicio import PopupServicio


from Modulos.Comercial.popup.popup_nueva_cotizacion import PopupNuevaCotizacion
from Modulos.Comercial.date_utils import to_long_english_date
from api_client import (
    get_comercial_cotizaciones_api,
    get_comercial_cotizacion_api,
    download_comercial_cotizacion_export_api,
    delete_comercial_cotizacion_api,
    put_comercial_cotizacion_api
)


class ComercialCotizacionesUI(ttk.Frame):
    """
    COMERCIAL — COTIZACIONES
    Gestión de cotizaciones comerciales
    """

    PAGE_SIZE = 50
    STATUS_COL_INDEX = 10

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        self.data_all = []
        self.page = 1
        self.servicios_values = []

        self.pack(fill="both", expand=True)
        self._setup_style()
        self._build_ui()

    # =========================================================
    # STYLE
    # =========================================================
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=24
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold")
        )

        # -------- TAG COLORS (PASTEL STATUS) --------
        self.tree_tags = {
            "PENDIENTE": {"background": "#FFF4CC"},   # Amarillo pastel
            "APROBADO": {"background": "#E6F4EA"},    # Verde pastel
            "CANCELADO": {"background": "#FDECEA"}    # Rojo pastel
        }

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ---------------- HEADER ----------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=6)

        ttk.Label(
            header,
            text="Cotizaciones Comerciales",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="Volver",
            command=self._go_back
        ).pack(side="right")

        # ---------------- FILTER BAR ----------------
        filter_bar = ttk.LabelFrame(self, text="Filtros")
        filter_bar.pack(fill="x", padx=12, pady=6)

        self.f_cliente = tk.StringVar()
        self.f_servicio = tk.StringVar()
        self.f_continente = tk.StringVar()
        self.f_pais = tk.StringVar()
        self.f_puerto = tk.StringVar()
        self.f_status = tk.StringVar()

        self.cb_filtros = {}

        col = 0

        # Cliente
        ttk.Label(filter_bar, text="Cliente").grid(row=0, column=col, padx=4)
        cb_cliente = ttk.Combobox(
            filter_bar,
            textvariable=self.f_cliente,
            width=28,
            state="readonly"
        )
        cb_cliente.grid(row=1, column=col, padx=4, sticky="w")
        self.cb_filtros["Cliente"] = cb_cliente
        col += 1

        # Servicio (selector avanzado)
        ttk.Label(filter_bar, text="Servicio").grid(row=0, column=col, padx=4)

        self.entry_servicio = ttk.Entry(
            filter_bar,
            textvariable=self.f_servicio,
            width=40,
            state="readonly"
        )
        self.entry_servicio.grid(row=1, column=col, padx=4, sticky="w")

        ttk.Button(
            filter_bar,
            text="...",
            width=3,
            command=lambda: self._open_selector_popup(
                "Seleccionar Servicio",
                self.servicios_values,
                self.f_servicio
            )
        ).grid(row=1, column=col + 1, padx=2)

        col += 2  # avanzamos 2 columnas

        # Continente
        ttk.Label(filter_bar, text="Continente").grid(row=0, column=col, padx=4)
        cb_cont = ttk.Combobox(
            filter_bar,
            textvariable=self.f_continente,
            width=20,
            state="readonly"
        )
        cb_cont.grid(row=1, column=col, padx=4, sticky="w")
        self.cb_filtros["Continente"] = cb_cont
        col += 1

        # País
        ttk.Label(filter_bar, text="País").grid(row=0, column=col, padx=4)
        cb_pais = ttk.Combobox(
            filter_bar,
            textvariable=self.f_pais,
            width=20,
            state="readonly"
        )
        cb_pais.grid(row=1, column=col, padx=4, sticky="w")
        self.cb_filtros["País"] = cb_pais
        col += 1

        # Puerto
        ttk.Label(filter_bar, text="Puerto").grid(row=0, column=col, padx=4)
        cb_puerto = ttk.Combobox(
            filter_bar,
            textvariable=self.f_puerto,
            width=20,
            state="readonly"
        )
        cb_puerto.grid(row=1, column=col, padx=4, sticky="w")
        self.cb_filtros["Puerto"] = cb_puerto
        col += 1

        # Status
        ttk.Label(filter_bar, text="Status").grid(row=0, column=col, padx=4)
        cb_status = ttk.Combobox(
            filter_bar,
            textvariable=self.f_status,
            width=12,
            state="readonly"
        )
        cb_status.grid(row=1, column=col, padx=4, sticky="w")
        self.cb_filtros["Status"] = cb_status
        col += 1

        ttk.Button(
            filter_bar,
            text="Buscar",
            command=self._buscar
        ).grid(row=1, column=col, padx=10)

        ttk.Button(
            filter_bar,
            text="Limpiar",
            command=self._limpiar
        ).grid(row=1, column=col + 1)

        # ---------------- KPI CARDS ----------------
        kpi_frame = ttk.Frame(self)
        kpi_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.kpi_cards = {}

        def _kpi_card(parent, title, bg):
            card = tk.Frame(
                parent,
                bg=bg,
                height=60,
                padx=12,
                pady=6
            )
            card.pack(side="left", expand=True, fill="x", padx=4)

            lbl_title = tk.Label(
                card,
                text=title,
                bg=bg,
                fg="white",
                font=("Segoe UI", 9, "bold")
            )
            lbl_title.pack(anchor="w")

            lbl_value = tk.Label(
                card,
                text="0",
                bg=bg,
                fg="white",
                font=("Segoe UI", 16, "bold")
            )
            lbl_value.pack(anchor="w")

            self.kpi_cards[title] = lbl_value

        # --- COLORES EXACTOS COMO LA IMAGEN ---
        _kpi_card(kpi_frame, "Clientes",   "#1F6FFF")  # Azul
        _kpi_card(kpi_frame, "Servicios",  "#6F2DBD")  # Morado
        _kpi_card(kpi_frame, "Países",     "#3A86FF")  # Azul claro
        _kpi_card(kpi_frame, "Puertos",    "#6C757D")  # Gris
        _kpi_card(kpi_frame, "Pendientes", "#FFC107")  # Amarillo
        _kpi_card(kpi_frame, "Aprobadas",  "#2ECC71")  # Verde
        _kpi_card(kpi_frame, "Canceladas", "#E74C3C")  # Rojo


        # ---------------- ACTION BAR ----------------
        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", padx=12, pady=4)

        ttk.Button(
            action_bar,
            text="Nueva Cotización",
            command=self._nueva
        ).pack(side="left", padx=4)

        acciones_btn = ttk.Menubutton(action_bar, text="Acciones")
        acciones_btn.pack(side="left", padx=4)

        acciones_menu = Menu(acciones_btn, tearoff=0)
        acciones_menu.add_command(label="Aprobar", command=self._aprobar)
        acciones_menu.add_command(label="Cancelar", command=self._cancelar)
        acciones_menu.add_separator()
        acciones_menu.add_command(label="Editar texto", command=self._editar_texto)
        acciones_menu.add_command(label="Exportar Word", command=lambda: self._exportar_cotizacion("word"))
        acciones_menu.add_command(label="Exportar PDF", command=lambda: self._exportar_cotizacion("pdf"))
        acciones_menu.add_separator()
        acciones_menu.add_command(label="Eliminar", command=self._eliminar)

        acciones_btn["menu"] = acciones_menu

        ttk.Button(
            action_bar,
            text="Exportar",
            command=self._exportar
        ).pack(side="right")

        # ---------------- TABLE ----------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=12, pady=6)

        cols = (
            "id", "quotation_number", "cliente", "servicio",
            "continente", "pais", "puerto",
            "precio", "idioma", "validez", "status",
            "created_at"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings"
        )

        headers = {
            "id": "ID",
            "quotation_number": "Quotation",
            "cliente": "Cliente",
            "servicio": "Servicio",
            "continente": "Continente",
            "pais": "País",
            "puerto": "Puerto",
            "precio": "Precio",
            "idioma": "Idioma",
            "validez": "Validez",
            "status": "Status",
            "created_at": "Creada"
        }

        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ---------------- PAGINATION ----------------
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=12, pady=(0, 6))

        self.lbl_page = ttk.Label(footer, text="0 resultados")
        self.lbl_page.pack(side="left")

        ttk.Button(footer, text="◀ Anterior", command=self._prev_page).pack(side="right", padx=4)
        ttk.Button(footer, text="Siguiente ▶", command=self._next_page).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _buscar(self):
        try:
            resp = get_comercial_cotizaciones_api()
            self.data_all = resp.get("data", [])
            self.page = 1
            self._alimentar_filtros()
            self._render_page()
            self._load_kpis()   # 👈 ESTA LÍNEA
        except Exception as e:
            messagebox.showerror("Cotizaciones", str(e))

    def _alimentar_filtros(self):

        def uniq(key):
            return sorted({str(r.get(key)) for r in self.data_all if r.get(key)})

        clientes = uniq("cliente")
        self.servicios_values = uniq("servicio")
        continentes = uniq("continente")
        paises = uniq("pais")
        puertos = uniq("puerto")
        status_list = uniq("status")

        self.cb_filtros["Cliente"]["values"] = clientes
        self.cb_filtros["Continente"]["values"] = continentes
        self.cb_filtros["País"]["values"] = paises
        self.cb_filtros["Puerto"]["values"] = puertos
        self.cb_filtros["Status"]["values"] = status_list


    # =========================================================
    # POPUP SELECTOR PARA COMBOS GRANDES (PRO ERP VERSION)
    # =========================================================
    def _open_selector_popup(self, title, values, variable):

        popup = tk.Toplevel(self)
        popup.title(title)
        popup.geometry("600x350")
        popup.transient(self)
        popup.grab_set()

        frame = tk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar_y = tk.Scrollbar(frame, orient="vertical")
        scrollbar_x = tk.Scrollbar(frame, orient="horizontal")

        listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            font=("Segoe UI", 10)
        )

        scrollbar_y.config(command=listbox.yview)
        scrollbar_x.config(command=listbox.xview)

        listbox.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        for v in values:
            listbox.insert("end", v)

        def select_item(event=None):
            selection = listbox.curselection()
            if selection:
                value = listbox.get(selection[0])
                variable.set(value)
                popup.destroy()

        listbox.bind("<Double-Button-1>", select_item)

        ttk.Button(
            popup,
            text="Seleccionar",
            command=select_item
        ).pack(pady=5)


    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        filtered = [
            r for r in self.data_all
            if (not self.f_cliente.get() or r.get("cliente") == self.f_cliente.get())
            and (not self.f_servicio.get() or r.get("servicio") == self.f_servicio.get())
            and (not self.f_continente.get() or r.get("continente") == self.f_continente.get())
            and (not self.f_pais.get() or r.get("pais") == self.f_pais.get())
            and (not self.f_puerto.get() or r.get("puerto") == self.f_puerto.get())
            and (not self.f_status.get() or r.get("status") == self.f_status.get())
        ]

        total = len(filtered)
        if total == 0:
            self.lbl_page.config(text="0 resultados")
            return

        total_pages = math.ceil(total / self.PAGE_SIZE)
        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        def fmt_precio(value):
            if value in (None, ""):
                return ""
            try:
                return f"{float(value):,.2f}"
            except (TypeError, ValueError):
                return ""

        for r in filtered[start:end]:
            status = r.get("status")

            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    r.get("id"),
                    r.get("quotation_number"),
                    r.get("cliente"),
                    r.get("servicio"),
                    r.get("continente"),
                    r.get("pais"),
                    r.get("puerto"),
                    fmt_precio(r.get("precio")),
                    r.get("idioma"),
                    r.get("validez"),
                    status,
                    to_long_english_date(r.get("created_at"))
                )
            )

            # -------- APPLY PASTEL COLOR BY STATUS --------
            if status in self.tree_tags:
                self.tree.tag_configure(
                    status,
                    **self.tree_tags[status]
                )
                self.tree.item(item_id, tags=(status,))

        self.lbl_page.config(text=f"Página {self.page} de {total_pages}")

    # =========================================================
    # ACTIONS
    # =========================================================
    def _selected_cotizacion_id(self, title="Cotizaciones"):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(title, "Seleccione una cotización")
            return None

        values = self.tree.item(sel[0])["values"]
        if not values:
            messagebox.showwarning(title, "Seleccione una cotización válida")
            return None

        return values[0]

    def _nueva(self):
        PopupNuevaCotizacion(self)

    def _eliminar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Eliminar", "Seleccione una cotización")
            return

        cotizacion_id = self.tree.item(sel[0])["values"][0]

        if not messagebox.askyesno("Confirmar", "¿Eliminar esta cotización?"):
            return

        delete_comercial_cotizacion_api(cotizacion_id)
        self._buscar()

    def _aprobar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aprobar", "Seleccione una cotización")
            return

        values = self.tree.item(sel[0])["values"]
        cotizacion_id = values[0]
        status_actual = values[self.STATUS_COL_INDEX]

        if status_actual != "PENDIENTE":
            messagebox.showwarning(
                "Aprobar",
                "Solo se pueden aprobar cotizaciones en estado PENDIENTE"
            )
            return

        if not messagebox.askyesno(
            "Confirmar aprobación",
            "¿Está seguro que esta cotización ha sido aprobada?"
        ):
            return

        try:
            put_comercial_cotizacion_api(
                cotizacion_id,
                {"status": "APROBADO"}
            )

            PopupServicio(
                self,
                on_success=self._buscar
            )

            self._buscar()

        except Exception as e:
            messagebox.showerror("Aprobar", str(e))


    def _cancelar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cancelar", "Seleccione una cotización")
            return

        values = self.tree.item(sel[0])["values"]
        cotizacion_id = values[0]
        status_actual = values[self.STATUS_COL_INDEX]

        if status_actual != "PENDIENTE":
            messagebox.showwarning(
                "Cancelar",
                "Solo se pueden cancelar cotizaciones en estado PENDIENTE"
            )
            return

        if not messagebox.askyesno(
            "Confirmar cancelación",
            "¿Está seguro que esta cotización ha sido cancelada / rechazada por el cliente?"
        ):
            return

        reason = simpledialog.askstring(
            "Razón de cancelación",
            "Indique la razón de cancelación:"
        )

        if not reason:
            messagebox.showwarning(
                "Cancelar",
                "Debe indicar una razón de cancelación"
            )
            return

        try:
            put_comercial_cotizacion_api(
                cotizacion_id,
                {
                    "status": "CANCELADO",
                    "razon_cancelacion": reason
                }
            )

            self._buscar()

        except Exception as e:
            messagebox.showerror("Cancelar", str(e))

    def _editar_texto(self):
        cotizacion_id = self._selected_cotizacion_id("Editar texto")
        if not cotizacion_id:
            return

        try:
            data = get_comercial_cotizacion_api(cotizacion_id)
        except Exception as e:
            messagebox.showerror("Editar texto", str(e))
            return

        popup = tk.Toplevel(self)
        popup.title(f"Editar texto cotización {data.get('quotation_number') or cotizacion_id}")
        popup.geometry("900x620")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(True, True)

        header = ttk.Frame(popup)
        header.pack(fill="x", padx=12, pady=(10, 4))

        ttk.Label(
            header,
            text=f"{data.get('quotation_number') or ''} | {data.get('cliente') or ''}",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Este texto queda guardado y se usa cada vez que exportes la cotización.",
            foreground="#555555"
        ).pack(anchor="w", pady=(2, 0))

        frame = ttk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        text = tk.Text(frame, wrap="word", font=("Segoe UI", 10), undo=True)
        ysb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=ysb.set)
        text.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        text.insert("1.0", data.get("texto_cotizacion") or data.get("texto_exportable") or "")

        footer = ttk.Frame(popup)
        footer.pack(fill="x", padx=12, pady=(0, 12))

        def save_text():
            nuevo_texto = text.get("1.0", "end").strip()
            if not nuevo_texto:
                messagebox.showwarning("Editar texto", "El texto no puede quedar vacío")
                return

            try:
                put_comercial_cotizacion_api(
                    cotizacion_id,
                    {"texto_cotizacion": nuevo_texto}
                )
                popup.destroy()
                self._buscar()
                messagebox.showinfo("Editar texto", "Texto guardado correctamente")
            except Exception as exc:
                messagebox.showerror("Editar texto", str(exc))

        ttk.Button(footer, text="Cancelar", command=popup.destroy).pack(side="right", padx=4)
        ttk.Button(footer, text="Guardar texto", command=save_text).pack(side="right", padx=4)

    def _exportar_cotizacion(self, formato: str):
        cotizacion_id = self._selected_cotizacion_id("Exportar cotización")
        if not cotizacion_id:
            return

        ext = ".docx" if formato == "word" else ".pdf"
        label = "Word" if formato == "word" else "PDF"

        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(label, f"*{ext}")]
        )
        if not path:
            return

        try:
            download_comercial_cotizacion_export_api(cotizacion_id, formato, path)
            messagebox.showinfo("Exportar cotización", f"{label} generado correctamente")
        except Exception as e:
            messagebox.showerror("Exportar cotización", str(e))


    def _exportar(self):
        if not self.data_all:
            messagebox.showwarning("Exportar", "No hay datos")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        if not path:
            return

        export_rows = []
        for row in self.data_all:
            item = dict(row or {})
            item["created_at"] = to_long_english_date(item.get("created_at"))
            export_rows.append(item)

        df = pd.DataFrame(export_rows)
        if path.endswith(".csv"):
            df.to_csv(path, index=False)
        else:
            df.to_excel(path, index=False)

        messagebox.showinfo("Exportar", "Archivo generado")

    def _limpiar(self):
        for v in (
            self.f_cliente,
            self.f_servicio,
            self.f_continente,
            self.f_pais,
            self.f_puerto,
            self.f_status
        ):
            v.set("")

        self.data_all = []
        self.page = 1
        self.servicios_values = []
        self.tree.delete(*self.tree.get_children())
        self.lbl_page.config(text="0 resultados")

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._render_page()

    def _next_page(self):
        if self.page * self.PAGE_SIZE < len(self.data_all):
            self.page += 1
            self._render_page()

    def _go_back(self):
        if callable(self.on_back):
            self.on_back()

    # =========================================================
    # KPIs
    # =========================================================
    def _load_kpis(self):
        try:
            from api_client import get_comercial_cotizaciones_kpis_api

            resp = get_comercial_cotizaciones_kpis_api(
                cliente=self.f_cliente.get() or None,
                servicio=self.f_servicio.get() or None,
                pais=self.f_pais.get() or None,
                puerto=self.f_puerto.get() or None,
                status=self.f_status.get() or None
            )

            k = resp.get("kpis", {})

            self.kpi_cards["Clientes"].config(text=str(k.get("clientes", 0)))
            self.kpi_cards["Servicios"].config(text=str(k.get("servicios", 0)))
            self.kpi_cards["Países"].config(text=str(k.get("paises", 0)))
            self.kpi_cards["Puertos"].config(text=str(k.get("puertos", 0)))
            self.kpi_cards["Pendientes"].config(text=str(k.get("pendientes", 0)))
            self.kpi_cards["Aprobadas"].config(text=str(k.get("aprobadas", 0)))
            self.kpi_cards["Canceladas"].config(text=str(k.get("canceladas", 0)))

        except Exception as e:
            print("KPI ERROR:", e)


    # =========================================================
    # AUTO RESIZE COMBO BASED ON VALUES
    # =========================================================
    def _auto_resize_combo(self, combo, values):
        """
        Ajusta el width del Combobox basado en el texto más largo.
        """
        if not values:
            return

        max_len = max(len(str(v)) for v in values)

        # margen extra para que no quede pegado
        combo.configure(width=min(max_len + 3, 80))


    # =========================================================
    # FORCE DROPDOWN WIDTH (REAL POPDOWN FIX)
    # =========================================================
    def _force_dropdown_width(self, combo):
        """
        Expande el ancho REAL del dropdown del Combobox.
        """
        try:
            combo.update_idletasks()

            popdown = combo.tk.call("ttk::combobox::PopdownWindow", combo)

            values = combo["values"]
            if not values:
                return

            max_len = max(len(str(v)) for v in values)

            combo.tk.call(
                f"{popdown}.f.l",
                "configure",
                "-width",
                max_len + 5
            )

        except Exception:
            pass
