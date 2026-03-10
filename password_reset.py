import requests
from api_client import BASE_URL


# =====================================================
# PASO 1 — VERIFICAR IDENTIDAD
# (usuario + nombre + apellido + email)
# =====================================================
def verify_identity(usuario: str, nombre: str, apellido: str, email: str):
    """
    Llama al backend para verificar identidad
    """

    payload = {
        "usuario": usuario.strip(),
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "email": email.strip()
    }

    try:
        r = requests.post(
            f"{BASE_URL}/auth/reset/verify-identity",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        return True, r.json()

    except requests.HTTPError as e:
        try:
            return False, r.json()
        except Exception:
            return False, {"error": str(e)}

    except Exception as e:
        return False, {"error": str(e)}


# =====================================================
# PASO 2 — VERIFICAR TOTP
# =====================================================
def verify_reset_totp(usuario: str, codigo: str):
    """
    Llama al backend para validar TOTP
    """

    payload = {
        "usuario": usuario.strip(),
        "codigo": codigo.strip()
    }

    try:
        r = requests.post(
            f"{BASE_URL}/auth/reset/verify-totp",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        return True, r.json()

    except requests.HTTPError as e:
        try:
            return False, r.json()
        except Exception:
            return False, {"error": str(e)}

    except Exception as e:
        return False, {"error": str(e)}


# =====================================================
# PASO 3 — CAMBIAR CONTRASEÑA
# =====================================================
def reset_password_final(usuario: str, new_password: str):
    """
    Envía la nueva contraseña al backend (bcrypt se hace en API)
    """

    payload = {
        "usuario": usuario.strip(),
        "password": new_password
    }

    try:
        r = requests.post(
            f"{BASE_URL}/auth/reset/set-password",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        return True, r.json()

    except requests.HTTPError as e:
        try:
            return False, r.json()
        except Exception:
            return False, {"error": str(e)}

    except Exception as e:
        return False, {"error": str(e)}
