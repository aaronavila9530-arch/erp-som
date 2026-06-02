import base64
import json
import os
from ctypes import (
    Structure,
    byref,
    cast,
    create_string_buffer,
    create_unicode_buffer,
    c_void_p,
    c_wchar_p,
    sizeof,
    string_at,
    windll,
)
from ctypes.wintypes import BOOL, DWORD, HWND


APP_DIR_NAME = "ERP-SOM"
CREDENTIALS_FILE = "saved_credentials.dat"
ENTROPY = b"ERP-SOM.WindowsCredentials.v1"


class DATA_BLOB(Structure):
    _fields_ = [
        ("cbData", DWORD),
        ("pbData", c_void_p),
    ]


class CREDUI_INFO(Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("hwndParent", HWND),
        ("pszMessageText", c_wchar_p),
        ("pszCaptionText", c_wchar_p),
        ("hbmBanner", c_void_p),
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


def _split_windows_identity(username: str):
    username = str(username or "").strip()
    if "\\" in username:
        domain, user = username.split("\\", 1)
        return user, domain or None
    return username, None


def prompt_windows_identity(parent_hwnd: int | None = None) -> bool:
    """
    Shows the native Windows Security prompt and validates the entered
    Windows account password with LogonUser. This is separate from the
    ERP credential stored with DPAPI.
    """

    if os.name != "nt":
        raise RuntimeError("La validacion de Windows solo esta disponible en Windows")

    info = CREDUI_INFO()
    info.cbSize = sizeof(CREDUI_INFO)
    info.hwndParent = HWND(parent_hwnd or 0)
    info.pszCaptionText = "ERP-SOM"
    info.pszMessageText = "Confirme su usuario de Windows para usar credenciales guardadas"

    auth_package = DWORD(0)
    out_auth_buffer = c_void_p()
    out_auth_buffer_size = DWORD(0)
    save = BOOL(False)

    CREDUIWIN_GENERIC = 0x00000001
    CREDUIWIN_SECURE_PROMPT = 0x00001000
    ERROR_CANCELLED = 1223

    result = windll.credui.CredUIPromptForWindowsCredentialsW(
        byref(info),
        0,
        byref(auth_package),
        None,
        0,
        byref(out_auth_buffer),
        byref(out_auth_buffer_size),
        byref(save),
        CREDUIWIN_GENERIC | CREDUIWIN_SECURE_PROMPT,
    )

    if result == ERROR_CANCELLED:
        return False
    if result != 0:
        raise OSError(f"CredUIPromptForWindowsCredentials failed: {result}")

    username_buf = None
    domain_buf = None
    password_buf = None
    token = c_void_p()

    try:
        username_size = DWORD(256)
        domain_size = DWORD(256)
        password_size = DWORD(256)
        username_buf = create_unicode_buffer(username_size.value)
        domain_buf = create_unicode_buffer(domain_size.value)
        password_buf = create_unicode_buffer(password_size.value)

        ok = windll.credui.CredUnPackAuthenticationBufferW(
            0,
            out_auth_buffer,
            out_auth_buffer_size.value,
            username_buf,
            byref(username_size),
            domain_buf,
            byref(domain_size),
            password_buf,
            byref(password_size),
        )
        if not ok:
            raise OSError("CredUnPackAuthenticationBuffer failed")

        entered_username = username_buf.value
        entered_domain = domain_buf.value
        entered_password = password_buf.value

        if not entered_username or not entered_password:
            raise RuntimeError("Usuario y contrasena de Windows requeridos")

        if not entered_domain:
            entered_username, entered_domain = _split_windows_identity(entered_username)

        LOGON32_LOGON_INTERACTIVE = 2
        LOGON32_PROVIDER_DEFAULT = 0

        ok = windll.advapi32.LogonUserW(
            entered_username,
            entered_domain,
            entered_password,
            LOGON32_LOGON_INTERACTIVE,
            LOGON32_PROVIDER_DEFAULT,
            byref(token),
        )
        if not ok:
            raise RuntimeError("Windows no pudo validar esas credenciales")

        return True

    finally:
        if token:
            windll.kernel32.CloseHandle(token)
        if out_auth_buffer:
            windll.kernel32.CoTaskMemFree(out_auth_buffer)
