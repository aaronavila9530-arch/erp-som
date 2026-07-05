import tkinter as tk
from tkinter import ttk, messagebox

# =========================================================
# IMPORTS API (SEGUROS - NO ROMPEN SI NO EXISTEN)
# =========================================================
try:
    from api_client import (
        get_servicio_surveyors_api,
        save_servicio_surveyors_api,
        get_surveyors_catalog_api
    )
    API_AVAILABLE = True
except Exception:
    API_AVAILABLE = False

    def get_servicio_surveyors_api(*args, **kwargs):
        return []

    def save_servicio_surveyors_api(*args, **kwargs):
        return {"status": "ok"}

    def get_surveyors_catalog_api(*args, **kwargs):
        return []


class PopupSurveyorsServicio(tk.Toplevel):

    MAX_SURVEYORS = 10

    def __init__(self, parent, consec, modo="view", on_saved=None):
        super().__init__(parent)

        self.parent = parent
        self.consec = consec
        self.modo = (modo or "view").strip().lower()
        self.on_saved = on_saved

        self.title(f"Surveyors del Servicio {consec}")
        self.geometry("760x560")
        self.config(bg="white")
        self.resizable(False, False)

        self.rows = []
        self.catalogo_surveyors = []

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_catalogo()
        self._load_existing_rows()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        main = tk.Frame(self, bg="white")
        main.pack(fill="both", expand=True, padx=15, pady=15)

        header = tk.Frame(main, bg="white")
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text="Gestión de Surveyors",
            bg="white",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Puede agregar hasta 10 surveyors por servicio. "
                 "El resumen se reflejará en Editar Servicio.",
            bg="white",
            fg="#555555",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(4, 0))

        # -----------------------------------------------------
        # RESUMEN
        # -----------------------------------------------------
        resumen = tk.Frame(main, bg="#F7F9FC", bd=1, relief="solid")
        resumen.pack(fill="x", pady=(0, 10))

        self.lbl_total_surveyors = tk.Label(
            resumen,
            text="Total surveyors: 0",
            bg="#F7F9FC",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_total_surveyors.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.lbl_total_honorarios = tk.Label(
            resumen,
            text="Honorarios totales: 0.00",
            bg="#F7F9FC",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_total_honorarios.grid(row=0, column=1, padx=12, pady=10, sticky="w")

        # -----------------------------------------------------
        # TABLA DETALLE
        # -----------------------------------------------------
        table_wrap = tk.Frame(main, bg="white")
        table_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            table_wrap,
            bg="white",
            highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            table_wrap,
            orient="vertical",
            command=canvas.yview
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.rows_frame = tk.Frame(canvas, bg="white")
        self.rows_window = canvas.create_window(
            (0, 0),
            window=self.rows_frame,
            anchor="nw"
        )

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(self.rows_window, width=event.width)

        self.rows_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Header grilla
        hdr = tk.Frame(self.rows_frame, bg="white")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        hdr.grid_columnconfigure(1, weight=1)

        tk.Label(
            hdr,
            text="#",
            bg="white",
            font=("Segoe UI", 9, "bold"),
            width=4
        ).grid(row=0, column=0, padx=4, sticky="w")

        tk.Label(
            hdr,
            text="Surveyor",
            bg="white",
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=1, padx=4, sticky="w")

        tk.Label(
            hdr,
            text="Honorario",
            bg="white",
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=2, padx=4, sticky="w")

        tk.Label(
            hdr,
            text="Acción",
            bg="white",
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=3, padx=4, sticky="w")

        self.rows_container = tk.Frame(self.rows_frame, bg="white")
        self.rows_container.grid(row=1, column=0, sticky="nsew")

        # -----------------------------------------------------
        # BOTONES SUPERIORES
        # -----------------------------------------------------
        top_actions = tk.Frame(main, bg="white")
        top_actions.pack(fill="x", pady=(10, 0))

        self.btn_add_row = tk.Button(
            top_actions,
            text="+ Agregar surveyor",
            bg="#DCEBFA",
            font=("Segoe UI", 9, "bold"),
            command=self._add_row
        )
        self.btn_add_row.pack(side="left")

        self.btn_clear_rows = tk.Button(
            top_actions,
            text="Limpiar todo",
            command=self._clear_all_rows
        )
        self.btn_clear_rows.pack(side="left", padx=8)

        if self.modo == "view":
            self.btn_add_row.config(state="disabled")
            self.btn_clear_rows.config(state="disabled")

        # -----------------------------------------------------
        # BOTONES INFERIORES
        # -----------------------------------------------------
        btns = tk.Frame(main, bg="white")
        btns.pack(fill="x", pady=(15, 0))

        self.btn_guardar = tk.Button(
            btns,
            text="Guardar",
            bg="#86A9D9",
            font=("Segoe UI", 10, "bold"),
            command=self._save
        )
        self.btn_guardar.pack(side="left", padx=(0, 10))

        tk.Button(
            btns,
            text="Cerrar" if self.modo == "view" else "Cancelar",
            command=self.destroy
        ).pack(side="left")

        if self.modo == "view":
            self.btn_guardar.config(state="disabled")

    # =========================================================
    # CARGAS INICIALES
    # =========================================================
    def _load_catalogo(self):
        try:
            resp = get_surveyors_catalog_api()
            if isinstance(resp, dict):
                self.catalogo_surveyors = resp.get("data", []) or []
            elif isinstance(resp, list):
                self.catalogo_surveyors = resp
            else:
                self.catalogo_surveyors = []
        except Exception:
            self.catalogo_surveyors = []

    def _load_existing_rows(self):

        data = []

        if API_AVAILABLE:
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

        # MODO LOCAL (sin API)
        if not data:
            self._add_row()
            self._refresh_summary()
            return

        for row in data[:self.MAX_SURVEYORS]:
            self._add_row(
                surveyor=row.get("surveyor_nombre", ""),
                honorario=row.get("honorario", "")
            )

        self._refresh_summary()

    # =========================================================
    # ROWS
    # =========================================================
    def _add_row(self, surveyor="", honorario=""):

        if len(self.rows) >= self.MAX_SURVEYORS:
            messagebox.showwarning(
                "Límite alcanzado",
                f"Solo se permiten {self.MAX_SURVEYORS} surveyors por servicio."
            )
            return

        row_index = len(self.rows)

        row_wrap = tk.Frame(
            self.rows_container,
            bg="white",
            bd=1,
            relief="solid"
        )
        row_wrap.grid(
            row=row_index,
            column=0,
            sticky="ew",
            pady=3
        )
        row_wrap.grid_columnconfigure(1, weight=1)

        lbl_idx = tk.Label(
            row_wrap,
            text=str(row_index + 1),
            bg="white",
            width=4
        )
        lbl_idx.grid(row=0, column=0, padx=6, pady=6, sticky="w")

        cmb_surveyor = ttk.Combobox(
            row_wrap,
            state="readonly",
            width=42
        )
        cmb_surveyor["values"] = self._catalogo_display_values()
        cmb_surveyor.grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        if surveyor:
            cmb_surveyor.set(str(surveyor))

        ent_honorario = ttk.Entry(row_wrap, width=18)
        ent_honorario.grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ent_honorario.insert(0, str(honorario) if honorario is not None else "")

        btn_delete = tk.Button(
            row_wrap,
            text="Quitar",
            command=lambda: self._delete_row(row_data)
        )
        btn_delete.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        row_data = {
            "frame": row_wrap,
            "lbl_idx": lbl_idx,
            "cmb_surveyor": cmb_surveyor,
            "ent_honorario": ent_honorario
        }

        if self.modo == "view":
            cmb_surveyor.config(state="disabled")
            ent_honorario.config(state="disabled")
            btn_delete.config(state="disabled")

        cmb_surveyor.bind("<<ComboboxSelected>>", lambda e: self._refresh_summary())
        ent_honorario.bind("<KeyRelease>", lambda e: self._refresh_summary())
        ent_honorario.bind("<FocusOut>", lambda e: self._refresh_summary())

        self.rows.append(row_data)
        self._reindex_rows()
        self._refresh_summary()

    def _delete_row(self, row_data):
        if row_data not in self.rows:
            return

        row_data["frame"].destroy()
        self.rows.remove(row_data)

        if not self.rows:
            self._add_row()
        else:
            self._reindex_rows()
            self._refresh_summary()

    def _clear_all_rows(self):
        for row in self.rows[:]:
            row["frame"].destroy()

        self.rows.clear()
        self._add_row()
        self._refresh_summary()

    def _reindex_rows(self):
        for idx, row in enumerate(self.rows):
            row["frame"].grid_configure(row=idx)
            row["lbl_idx"].config(text=str(idx + 1))

    # =========================================================
    # UTILIDADES
    # =========================================================
    def _catalogo_display_values(self):
        values = []

        for item in self.catalogo_surveyors:
            if isinstance(item, dict):
                nombre = str(item.get("nombre") or "").strip()
                apellidos = str(item.get("apellidos") or "").strip()
                codigo = str(item.get("codigo") or item.get("id") or "").strip()
                nombre_completo = str(item.get("nombre_completo") or "").strip()
                surveyor = str(item.get("surveyor") or item.get("name") or "").strip()
                nombre = (
                    nombre_completo
                    or " ".join([nombre, apellidos]).strip()
                    or surveyor
                    or codigo
                )
            else:
                nombre = str(item).strip()

            if nombre:
                values.append(nombre)

        # quitar duplicados conservando orden
        seen = set()
        clean = []

        for v in values:
            key = v.lower()
            if key not in seen:
                seen.add(key)
                clean.append(v)

        return clean

    def _to_float_or_none(self, value):
        s = str(value or "").strip()

        if s == "":
            return None

        s = s.replace(",", "").replace(" ", "")

        try:
            return float(s)
        except Exception:
            return None

    def _collect_rows(self, validate=False):
        payload_rows = []
        errores = []

        for idx, row in enumerate(self.rows, start=1):
            surveyor = (row["cmb_surveyor"].get() or "").strip()
            honorario_raw = row["ent_honorario"].get()
            honorario = self._to_float_or_none(honorario_raw)

            fila_vacia = surveyor == "" and str(honorario_raw).strip() == ""
            if fila_vacia:
                continue

            if validate:
                if surveyor == "":
                    errores.append(f"Fila {idx}: debe seleccionar un surveyor.")
                if honorario is None:
                    errores.append(f"Fila {idx}: el honorario es obligatorio y numérico.")
                elif honorario < 0:
                    errores.append(f"Fila {idx}: el honorario no puede ser negativo.")

            payload_rows.append(
                {
                    "surveyor_nombre": surveyor,
                    "honorario": 0.0 if honorario is None else honorario,
                    "orden": idx
                }
            )

        return payload_rows, errores

    def _build_resumen(self, rows):
        cantidad = len(rows)
        total = round(sum(float(r.get("honorario") or 0) for r in rows), 2)

        if cantidad == 0:
            surveyor_resumen = ""
        elif cantidad == 1:
            surveyor_resumen = rows[0].get("surveyor_nombre", "")
        else:
            surveyor_resumen = f"Varios ({cantidad})"

        return {
            "surveyor": surveyor_resumen,
            "honorarios": total,
            "cantidad": cantidad
        }

    def _refresh_summary(self):
        rows, _ = self._collect_rows(validate=False)
        resumen = self._build_resumen(rows)

        self.lbl_total_surveyors.config(
            text=f"Total surveyors: {resumen['cantidad']}"
        )
        self.lbl_total_honorarios.config(
            text=f"Honorarios totales: {resumen['honorarios']:.2f}"
        )

    def _save(self):

        # =========================
        # SOLO CERRAR SI ES VIEW
        # =========================
        if self.modo == "view":
            self.destroy()
            return

        # =========================
        # VALIDAR Y RECOLECTAR
        # =========================
        rows, errores = self._collect_rows(validate=True)

        if errores:
            messagebox.showerror(
                "Validación",
                "\n".join(errores)
            )
            return

        if len(rows) > self.MAX_SURVEYORS:
            messagebox.showerror(
                "Validación",
                f"No se permiten más de {self.MAX_SURVEYORS} surveyors."
            )
            return

        payload = {
            "surveyors": rows
        }

        # =========================
        # LLAMAR API (PUT/POST)
        # =========================
        if API_AVAILABLE:
            try:
                resp = save_servicio_surveyors_api(
                    self.consec,
                    payload
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"No se pudieron guardar los surveyors:\n{e}"
                )
                return

            ok = False
            if isinstance(resp, dict):
                ok = resp.get("status") == "ok" or resp.get("success") is True

            if not ok:
                messagebox.showerror(
                    "Error",
                    "Error al guardar surveyors"
                )
                return

        # =========================
        # ACTUALIZAR UI PADRE
        # =========================
        resumen = self._build_resumen(rows)

        if self.on_saved:
            self.on_saved(resumen)

        # =========================
        # OK
        # =========================
        messagebox.showinfo(
            "OK",
            "Surveyors guardados correctamente."
        )

        self.destroy()
