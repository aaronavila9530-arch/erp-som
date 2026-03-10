# session_context.py

_session = {
    "usuario": None,
    "rol": None,
    "token": None
}


def set_user_context(usuario, rol, token=None):
    _session["usuario"] = usuario
    _session["rol"] = rol
    _session["token"] = token


def get_token():
    return _session.get("token")


def get_user():
    return _session.get("usuario")


def get_rol():
    return _session.get("rol")
