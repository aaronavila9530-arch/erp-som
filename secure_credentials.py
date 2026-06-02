import base64
import json
import os
from ctypes import (
    Structure,
    byref,
    cast,
    create_string_buffer,
    c_void_p,
    string_at,
    windll,
)
from ctypes.wintypes import DWORD


APP_DIR_NAME = "ERP-SOM"
CREDENTIALS_FILE = "saved_credentials.dat"
ENTROPY = b"ERP-SOM.WindowsCredentials.v1"


class DATA_BLOB(Structure):
    _fields_ = [
        ("cbData", DWORD),
        ("pbData", c_void_p),
    ]


def _app_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, APP_DIR_NAME)
    os.makedirs(folder, exist_ok=True)
    return folder


def _credentials_path() -> str:
    return os.path.join(_app_data_dir(), CREDENTIALS_FILE)


def _make_blob(data: bytes):
    buffer = create_string_buffer(data, len(data))
    blob = DATA_BLOB(len(data), c_void_p())
    blob.pbData = cast(buffer, c_void_p)
    return blob, buffer


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    return string_at(blob.pbData, blob.cbData)


def _crypt_protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows credential protection is only available on Windows")

    data_blob, data_buf = _make_blob(data)
    entropy_blob, entropy_buf = _make_blob(ENTROPY)
    out_blob = DATA_BLOB()

    ok = windll.crypt32.CryptProtectData(
        byref(data_blob),
        None,
        byref(entropy_blob),
        None,
        None,
        0,
        byref(out_blob),
    )
    _ = (data_buf, entropy_buf)
    if not ok:
        raise OSError("CryptProtectData failed")

    try:
        return _bytes_from_blob(out_blob)
    finally:
        windll.kernel32.LocalFree(c_void_p(out_blob.pbData))


def _crypt_unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows credential protection is only available on Windows")

    data_blob, data_buf = _make_blob(data)
    entropy_blob, entropy_buf = _make_blob(ENTROPY)
    out_blob = DATA_BLOB()

    ok = windll.crypt32.CryptUnprotectData(
        byref(data_blob),
        None,
        byref(entropy_blob),
        None,
        None,
        0,
        byref(out_blob),
    )
    _ = (data_buf, entropy_buf)
    if not ok:
        raise OSError("CryptUnprotectData failed")

    try:
        return _bytes_from_blob(out_blob)
    finally:
        windll.kernel32.LocalFree(c_void_p(out_blob.pbData))


def save_credentials(usuario: str, password: str) -> None:
    usuario = str(usuario or "").strip()
    password = str(password or "")
    if not usuario or not password:
        raise ValueError("Usuario y contraseña son requeridos")

    payload = json.dumps(
        {"usuario": usuario, "password": password},
        ensure_ascii=False,
    ).encode("utf-8")
    encrypted = _crypt_protect(payload)
    with open(_credentials_path(), "w", encoding="ascii") as f:
        f.write(base64.b64encode(encrypted).decode("ascii"))


def load_credentials() -> dict | None:
    path = _credentials_path()
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="ascii") as f:
        raw = f.read().strip()

    if not raw:
        return None

    decrypted = _crypt_unprotect(base64.b64decode(raw))
    data = json.loads(decrypted.decode("utf-8"))
    if not isinstance(data, dict):
        return None
    if not data.get("usuario") or not data.get("password"):
        return None
    return data


def has_saved_credentials() -> bool:
    return os.path.exists(_credentials_path())


def delete_credentials() -> None:
    try:
        os.remove(_credentials_path())
    except FileNotFoundError:
        pass


def is_windows_protection_available() -> bool:
    return os.name == "nt"
