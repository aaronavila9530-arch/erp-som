import sys
import os


def resource_path(relative_path):
    """
    Devuelve la ruta correcta tanto en modo desarrollo
    como cuando la app está empaquetada con PyInstaller.
    """
    try:
        # PyInstaller crea una carpeta temporal y guarda su path en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
