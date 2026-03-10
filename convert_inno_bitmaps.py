from PIL import Image
import os
import sys


# ============================================================
# RESOLVER PATH BASE (DEV / EXE / CUALQUIER PC)
# ============================================================

def get_base_dir():
    """
    Devuelve la ruta base del proyecto de forma portable.
    - En desarrollo: carpeta donde está este script
    - En EXE (PyInstaller): carpeta temporal (_MEIPASS)
    """
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, "assets")


BASE_DIR = get_base_dir()


# ==========================
# CONFIGURACIÓN INNO SETUP
# ==========================

IMAGES = [
    {
        "input": "logo_menu_tareas.jpeg",
        "output": "wizard_left.bmp",
        "size": (164, 314)
    },
    {
        "input": "logo_menu_tareas.jpeg",
        "output": "wizard_small.bmp",
        "size": (55, 58)
    }
]


# ============================================================
# CONVERSIÓN DE IMÁGENES
# ============================================================

def convert_image(cfg):
    src = os.path.join(BASE_DIR, cfg["input"])
    dst = os.path.join(BASE_DIR, cfg["output"])
    size = cfg["size"]

    if not os.path.exists(src):
        raise FileNotFoundError(f"No existe el archivo: {src}")

    img = Image.open(src).convert("RGB")
    img = img.resize(size, Image.LANCZOS)
    img.save(dst, format="BMP")

    print(f"✔ Generado: {dst}  ({size[0]}x{size[1]} BMP)")


def main():
    print("=== Generando imágenes BMP compatibles con Inno Setup ===\n")
    print(f"📁 Assets directory: {BASE_DIR}\n")

    for cfg in IMAGES:
        convert_image(cfg)

    print("\n✔ Conversión finalizada correctamente.")


if __name__ == "__main__":
    main()
