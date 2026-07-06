import os
import sys
import subprocess
import threading
import time
import requests
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from version import APP_VERSION
except Exception as e:
    raise RuntimeError(f"No se pudo cargar APP_VERSION desde version.py: {e}")


class UpdateWindow(tk.Toplevel):

    def __init__(self, parent, current_version, latest_version, message, download_url):
        super().__init__(parent)

        if not APP_VERSION:
            raise RuntimeError("APP_VERSION no está definida")

        current_version = (APP_VERSION or "").strip()
        latest_version = (str(latest_version or "").strip())

        if not latest_version or latest_version == current_version:
            self.destroy()
            return

        self.parent = parent
        self.download_url = download_url
        self.latest_version = latest_version

        self.installer_path = os.path.join(
            self._updates_dir(),
            f"ERP-SOM-Setup-{self.latest_version}.exe"
        )

        self.title("Actualización requerida")
        self.geometry("420x230")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._block_close)

        tk.Label(
            self,
            text=f"ERP-SOM {self.latest_version} disponible",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(15, 5))

        tk.Label(
            self,
            text=message or "Existe una actualización obligatoria del sistema.",
            wraplength=360,
            justify="center"
        ).pack(pady=5)

        self.progress = ttk.Progressbar(self, mode="indeterminate", length=300)
        self.progress.pack(pady=15)
        self.progress.start(10)

        self.btn = ttk.Button(self, text="Actualizar ahora", command=self._start_thread)
        self.btn.pack()

        self.after(500, self._start_thread)

    def _block_close(self):
        messagebox.showwarning(
            "Actualización requerida",
            "Debe actualizar el sistema para continuar.",
            parent=self
        )

    def _start_thread(self):
        self.btn.config(state="disabled")
        threading.Thread(target=self._download_install_relaunch, daemon=True).start()

    def _installed_exe_path(self) -> str:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return os.path.join(local_appdata, "Programs", "ERP-SOM", "ERP-SOM.exe")
        return os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "ERP-SOM", "ERP-SOM.exe")

    def _updates_dir(self) -> str:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "ERP-SOM", "updates")

    def _prepare_updates_dir(self):
        os.makedirs(self._updates_dir(), exist_ok=True)
        for name in os.listdir(self._updates_dir()):
            if name.lower().startswith("erp-som-setup-") and name.lower().endswith(".exe"):
                try:
                    os.remove(os.path.join(self._updates_dir(), name))
                except OSError:
                    pass

    def _unblock_downloaded_installer(self, installer_path: str):
        try:
            zone_identifier = installer_path + ":Zone.Identifier"
            if os.path.exists(zone_identifier):
                os.remove(zone_identifier)
        except OSError:
            pass

        try:
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "Unblock-File -LiteralPath $args[0]",
                    installer_path,
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _run_inno_and_wait(self, installer_path: str) -> int:
        """
        Inno Setup flags:
        - /VERYSILENT /SUPPRESSMSGBOXES: no UI
        - /NORESTART: no reinicios
        - /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS: cierra y reabre si aplica
        - /FORCECLOSEAPPLICATIONS: fuerza cierre si está bloqueado
        """
        args = [
            installer_path,
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/RESTARTAPPLICATIONS",
            "/FORCECLOSEAPPLICATIONS"
        ]
        completed = subprocess.run(args, check=False)
        return int(completed.returncode)

    def _download_install_relaunch(self):
        try:
            if not self.download_url:
                raise RuntimeError("URL de descarga no disponible")

            self._prepare_updates_dir()

            # -----------------------------
            # Descargar instalador (seguro)
            # -----------------------------
            with requests.get(self.download_url, stream=True, timeout=(10, 120)) as r:
                r.raise_for_status()
                with open(self.installer_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)

            if (not os.path.exists(self.installer_path)) or (os.path.getsize(self.installer_path) < 1024 * 200):
                raise RuntimeError("El instalador descargado es inválido o está corrupto.")

            self._unblock_downloaded_installer(self.installer_path)

            # --------------------------------
            # Ejecutar instalador y esperar FIN
            # --------------------------------
            code = self._run_inno_and_wait(self.installer_path)
            if code != 0:
                raise RuntimeError(f"El instalador finalizó con código {code}.")

            # -----------------------------
            # Relanzar EXE instalado
            # -----------------------------
            exe_path = self._installed_exe_path()

            # espera corta por si Windows tarda en liberar archivo
            for _ in range(20):
                if os.path.exists(exe_path):
                    break
                time.sleep(0.25)

            if not os.path.exists(exe_path):
                raise RuntimeError(
                    "La instalación terminó, pero no se encontró el ERP instalado en:\n"
                    f"{exe_path}\n\n"
                    "Verifica que el instalador esté usando Program Files."
                )

            subprocess.Popen([exe_path], close_fds=True)

            # cerrar el ERP viejo
            os._exit(0)

        except requests.exceptions.RequestException as e:
            self._handle_error(f"Error de red al descargar actualización:\n{e}")

        except Exception as e:
            self._handle_error(f"No se pudo completar la actualización:\n{e}")

    def _handle_error(self, message):
        try:
            self.progress.stop()
        except Exception:
            pass

        messagebox.showerror(
            "Error de actualización",
            message,
            parent=self
        )
        self.btn.config(state="normal")
