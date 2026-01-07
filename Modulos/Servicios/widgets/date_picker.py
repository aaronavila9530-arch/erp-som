import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime


class DatePicker(tk.Toplevel):
    def __init__(self, parent, entry_widget):
        super().__init__(parent)
        self.entry_widget = entry_widget
        self.title("Seleccionar fecha")
        self.geometry("300x260")
        self.resizable(False, False)

        today = datetime.today()
        self.year = today.year
        self.month = today.month

        self.header = tk.Frame(self)
        self.header.pack(fill="x")

        ttk.Button(self.header, text="<", width=3, command=self.prev_month).pack(side="left")
        self.label = tk.Label(self.header, text="", font=("Segoe UI", 10, "bold"))
        self.label.pack(side="left", expand=True)
        ttk.Button(self.header, text=">", width=3, command=self.next_month).pack(side="right")

        self.calendar_frame = tk.Frame(self)
        self.calendar_frame.pack(expand=True, fill="both")

        self.draw_calendar()

    def draw_calendar(self):
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        self.label.config(text=f"{calendar.month_name[self.month]} {self.year}")

        days = ["L", "M", "X", "J", "V", "S", "D"]
        for i, d in enumerate(days):
            tk.Label(self.calendar_frame, text=d, fg="blue").grid(row=0, column=i)

        month_days = calendar.monthcalendar(self.year, self.month)

        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue

                btn = ttk.Button(
                    self.calendar_frame,
                    text=str(day),
                    width=3,
                    command=lambda d=day: self.select_date(d)
                )
                btn.grid(row=r, column=c, padx=3, pady=3)

    def prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.draw_calendar()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.draw_calendar()

    def select_date(self, day):
        selected = f"{self.year}-{self.month:02d}-{day:02d}"
        self.entry_widget.delete(0, tk.END)
        self.entry_widget.insert(0, selected)
        self.destroy()
