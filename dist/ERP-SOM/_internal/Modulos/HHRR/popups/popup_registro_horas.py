import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import crear_ot_log
from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupRegistroHoras(tk.Toplevel):

    def __init__(self, parent, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success

        self.title("Registrar horas")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(main, text="Tipo *").grid(row=0, column=0, sticky="w")

        self.cmb_tipo = ttk.Combobox(
            main,
            values=["OPERACION", "INFORME"],
            state="readonly",
            width=20
        )
        self.cmb_tipo.grid(row=0, column=1, sticky="w", pady=4)
        self.cmb_tipo.current(0)

        ttk.Label(main, text="Fecha inicio *").grid(row=1, column=0, sticky="w")

        self.cal_inicio = ttk.Entry(main, width=15)
        self.cal_inicio.insert(0, to_long_english_date(datetime.today()))
        self.cal_inicio.grid(row=1, column=1, sticky="w", pady=4)
        ttk.Button(
            main,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.cal_inicio, output_format=LONG_DATE_FORMAT)
        ).grid(row=1, column=1, padx=(120, 0), sticky="w")

        hora_inicio = ttk.Frame(main)
        hora_inicio.grid(row=1, column=2, padx=8, sticky="w")

        self.spin_hi = tk.Spinbox(hora_inicio, from_=0, to=23, width=3, format="%02.0f")
        self.spin_mi = tk.Spinbox(hora_inicio, from_=0, to=59, width=3, format="%02.0f")

        self.spin_hi.delete(0, "end")
        self.spin_hi.insert(0, "08")
        self.spin_mi.delete(0, "end")
        self.spin_mi.insert(0, "00")

        self.spin_hi.pack(side="left")
        ttk.Label(hora_inicio, text=":").pack(side="left", padx=2)
        self.spin_mi.pack(side="left")

        ttk.Label(main, text="Fecha fin *").grid(row=2, column=0, sticky="w")

        self.cal_fin = ttk.Entry(main, width=15)
        self.cal_fin.insert(0, to_long_english_date(datetime.today()))
        self.cal_fin.grid(row=2, column=1, sticky="w", pady=4)
        ttk.Button(
            main,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.cal_fin, output_format=LONG_DATE_FORMAT)
        ).grid(row=2, column=1, padx=(120, 0), sticky="w")

        hora_fin = ttk.Frame(main)
        hora_fin.grid(row=2, column=2, padx=8, sticky="w")

        self.spin_hf = tk.Spinbox(hora_fin, from_=0, to=23, width=3, format="%02.0f")
        self.spin_mf = tk.Spinbox(hora_fin, from_=0, to=59, width=3, format="%02.0f")

        self.spin_hf.delete(0, "end")
        self.spin_hf.insert(0, "17")
        self.spin_mf.delete(0, "end")
        self.spin_mf.insert(0, "00")

        self.spin_hf.pack(side="left")
        ttk.Label(hora_fin, text=":").pack(side="left", padx=2)
        self.spin_mf.pack(side="left")

        ttk.Label(main, text="Buque").grid(row=3, column=0, sticky="w")
        self.ent_buque = ttk.Entry(main, width=40)
        self.ent_buque.grid(row=3, column=1, columnspan=2, sticky="w", pady=4)

        ttk.Label(main, text="Detalle").grid(row=4, column=0, sticky="nw")
        self.txt_comentario = tk.Text(main, height=6, width=45)
        self.txt_comentario.grid(row=4, column=1, columnspan=2, sticky="w", pady=4)

        btns = ttk.Frame(main)
        btns.grid(row=5, column=0, columnspan=3, pady=20)

        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="right", padx=5)

        ttk.Button(btns, text="Registrar", command=self._guardar).pack(side="right", padx=5)

    # =========================================================
    # LOGICA
    # =========================================================
    def _guardar(self):

        try:
            tipo = (self.cmb_tipo.get() or "").strip().upper()

            if tipo not in ("OPERACION", "INFORME"):
                raise ValueError("Tipo inválido")

            fecha_inicio = parse_hhrr_date(self.cal_inicio.get())
            fecha_fin = parse_hhrr_date(self.cal_fin.get())
            if not fecha_inicio or not fecha_fin:
                raise ValueError("Debe seleccionar fechas validas")

            inicio_dt = datetime.combine(
                fecha_inicio,
                datetime.min.time()
            ).replace(
                hour=int(self.spin_hi.get()),
                minute=int(self.spin_mi.get())
            )

            fin_dt = datetime.combine(
                fecha_fin,
                datetime.min.time()
            ).replace(
                hour=int(self.spin_hf.get()),
                minute=int(self.spin_mf.get())
            )

            if fin_dt <= inicio_dt:
                raise ValueError("La fecha fin debe ser mayor a inicio")

            payload = {
                "tipo": tipo,
                "fecha_inicio": inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_fin": fin_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "buque": self.ent_buque.get().strip() or None,
                "comentario": self.txt_comentario.get("1.0", "end").strip() or None
            }

            crear_ot_log(payload)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Éxito", "Horas registradas correctamente.")

        if self.on_success:
            self.on_success()

        self.destroy()
