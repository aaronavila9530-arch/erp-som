import base64
import json
import os
import subprocess
import tempfile
import time
from ctypes import (
    Structure,
    WINFUNCTYPE,
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
from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM


APP_DIR_NAME = "ERP-SOM"
CREDENTIALS_FILE = "saved_credentials.dat"
ENTROPY = b"ERP-SOM.WindowsCredentials.v1"
_RAISED_WINDOWS_SECURITY_HWND = set()


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


def _force_window_foreground(hwnd) -> None:
    if os.name != "nt" or not hwnd:
        return

    try:
        SW_RESTORE = 9
        HWND_TOPMOST = HWND(-1)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        VK_MENU = 0x12
        KEYEVENTF_KEYUP = 0x0002

        windll.user32.ShowWindow(hwnd, SW_RESTORE)
        windll.user32.keybd_event(VK_MENU, 0, 0, 0)
        windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
        )
        windll.user32.BringWindowToTop(hwnd)
        windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _bring_windows_security_prompt_to_front(parent_hwnd: int | None = None) -> bool:
    if os.name != "nt":
        return False

    patterns = (
        "seguridad de windows",
        "windows security",
        "windows hello",
        "pin",
        "credential",
        "credencial",
        "credenciales",
    )
    class_patterns = (
        "credential",
        "credui",
        "windows.ui.core",
    )
    found = []

    @WINFUNCTYPE(BOOL, HWND, LPARAM)
    def enum_proc(hwnd, _lparam):
        try:
            if not windll.user32.IsWindowVisible(hwnd):
                return True

            title_buf = create_unicode_buffer(512)
            class_buf = create_unicode_buffer(256)
            windll.user32.GetWindowTextW(hwnd, title_buf, 512)
            windll.user32.GetClassNameW(hwnd, class_buf, 256)
            title = (title_buf.value or "").strip().lower()
            class_name = (class_buf.value or "").strip().lower()

            title_match = any(pattern in title for pattern in patterns)
            class_match = any(pattern in class_name for pattern in class_patterns)

            if title_match or class_match:
                found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        windll.user32.EnumWindows(enum_proc, 0)
    except Exception:
        return False

    for hwnd in found:
        hwnd_value = int(hwnd)
        if hwnd_value in _RAISED_WINDOWS_SECURITY_HWND:
            continue

        _RAISED_WINDOWS_SECURITY_HWND.add(hwnd_value)
        _force_window_foreground(hwnd)
        return True

    return False

def _split_windows_identity(username: str):
    username = str(username or "").strip()
    if "\\" in username:
        domain, user = username.split("\\", 1)
        return user, domain or None
    return username, None


def _make_credui_info(parent_hwnd: int | None):
    info = CREDUI_INFO()
    info.cbSize = sizeof(CREDUI_INFO)
    info.hwndParent = HWND(parent_hwnd or 0)
    info.pszCaptionText = "ERP-SOM"
    info.pszMessageText = "Confirme su usuario de Windows para usar credenciales guardadas"
    return info


def _prompt_current_windows_user(parent_hwnd: int | None = None):
    info = _make_credui_info(parent_hwnd)

    auth_package = DWORD(0)
    out_auth_buffer = c_void_p()
    out_auth_buffer_size = DWORD(0)
    save = BOOL(False)

    CREDUIWIN_ENUMERATE_CURRENT_USER = 0x00000200
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
        CREDUIWIN_ENUMERATE_CURRENT_USER | CREDUIWIN_SECURE_PROMPT,
    )

    try:
        if result == ERROR_CANCELLED:
            return False
        if result == 0:
            return True
        return None
    finally:
        if out_auth_buffer:
            windll.ole32.CoTaskMemFree(out_auth_buffer)


def _prompt_windows_password(parent_hwnd: int | None = None) -> bool:
    info = _make_credui_info(parent_hwnd)

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
            windll.ole32.CoTaskMemFree(out_auth_buffer)


def _prompt_windows_hello(parent_hwnd: int | None = None) -> bool | None:
    powershell = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    if not os.path.exists(powershell):
        return None

    script = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Security.Credentials.UI.UserConsentVerifier, Windows.Security.Credentials.UI, ContentType=WindowsRuntime]

function Await-WinRtOperation($Operation, $ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethodDefinition -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1

    if (-not $method) {
        throw 'AsTask generic method not found'
    }

    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$availability = Await-WinRtOperation `
    ([Windows.Security.Credentials.UI.UserConsentVerifier]::CheckAvailabilityAsync()) `
    ([Windows.Security.Credentials.UI.UserConsentVerifierAvailability])

if ($availability.ToString() -ne 'Available') {
    Write-Output ('UNAVAILABLE:' + $availability.ToString())
    exit 2
}

$verification = Await-WinRtOperation `
    ([Windows.Security.Credentials.UI.UserConsentVerifier]::RequestVerificationAsync('ERP-SOM necesita validar Windows para usar credenciales guardadas')) `
    ([Windows.Security.Credentials.UI.UserConsentVerificationResult])

Write-Output $verification.ToString()
if ($verification.ToString() -eq 'Verified') {
    exit 0
}
if ($verification.ToString() -eq 'Canceled') {
    exit 3
}
exit 4
"""

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".ps1",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(script)
            script_path = f.name

        process = subprocess.Popen(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 120
        prompt_raised = False
        while process.poll() is None:
            if not prompt_raised:
                prompt_raised = _bring_windows_security_prompt_to_front(parent_hwnd)
            if time.monotonic() > deadline:
                process.kill()
                raise TimeoutError("Windows Hello validation timed out")
            time.sleep(0.5)

        stdout, stderr = process.communicate()
        output = (stdout or stderr or "").strip()
        if process.returncode == 0 and "Verified" in output:
            return True
        if process.returncode == 3:
            return False
        return None
    except Exception:
        return None
    finally:
        if script_path:
            try:
                os.remove(script_path)
            except OSError:
                pass


def prompt_windows_identity(parent_hwnd: int | None = None) -> bool:
    """
    Uses the current Windows credential provider first. That is the path that
    can show PIN/Windows Hello. If Windows cannot expose that prompt, falls
    back to the username/password credential dialog.
    """

    if os.name != "nt":
        raise RuntimeError("La validacion de Windows solo esta disponible en Windows")

    _RAISED_WINDOWS_SECURITY_HWND.clear()
    _bring_windows_security_prompt_to_front(parent_hwnd)

    hello_result = _prompt_windows_hello(parent_hwnd)
    if hello_result is not None:
        return hello_result

    current_user_result = _prompt_current_windows_user(parent_hwnd)
    if current_user_result is not None:
        return current_user_result

    return _prompt_windows_password(parent_hwnd)
