import os
import tempfile
import subprocess
import requests
import tkinter as tk
from tkinter import ttk, messagebox

class UpdateWindow(tk.Toplevel):

    def __init__(self, parent, current_version, latest_version, message, download_url):
        super().__init__(parent)

        self.download_url = download_url

        self.title("Actualización obligatoria")
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self,
            text=f"ERP-SOM {latest_version} disponible",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=15)

        tk.Label(
            self,
            text=message,
            wraplength=360,
            justify="center"
        ).pack()

        self.progress = ttk.Progressbar(self, length=300)
        self.progress.pack(pady=15)

        ttk.Button(
            self,
            text="Actualizar ahora",
            command=self._download
        ).pack()

        self.after(300, self._download)

    def _download(self):
        try:
            path = os.path.join(tempfile.gettempdir(), "ERP-SOM-Setup.exe")
            r = requests.get(self.download_url, stream=True, timeout=60)
            r.raise_for_status()

            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

            subprocess.Popen([path], shell=True)
            os._exit(0)

        except Exception as e:
            messagebox.showerror(
                "Error de actualización",
                str(e),
                parent=self
            )
