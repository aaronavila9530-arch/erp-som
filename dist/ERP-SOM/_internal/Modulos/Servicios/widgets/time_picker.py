import tkinter as tk
from tkinter import ttk


class TimePicker(tk.Toplevel):
    def __init__(self, parent, entry_widget):
        super().__init__(parent)
        self.entry_widget = entry_widget
        self.title("Seleccionar hora")
        self.geometry("200x120")
        self.resizable(False, False)

        tk.Label(self, text="Hora:").pack(pady=5)

        frame = tk.Frame(self)
        frame.pack()

        hours = [f"{h:02d}" for h in range(0, 24)]
        minutes = [f"{m:02d}" for m in range(0, 60)]

        self.cmb_hour = ttk.Combobox(frame, values=hours, width=5, state="readonly")
        self.cmb_hour.current(0)
        self.cmb_hour.grid(row=0, column=0, padx=5)

        self.cmb_minute = ttk.Combobox(frame, values=minutes, width=5, state="readonly")
        self.cmb_minute.current(0)
        self.cmb_minute.grid(row=0, column=1, padx=5)

        ttk.Button(self, text="Aceptar", command=self.apply_time).pack(pady=10)

    def apply_time(self):
        time = f"{self.cmb_hour.get()}:{self.cmb_minute.get()}"
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, time)
        self.destroy()
