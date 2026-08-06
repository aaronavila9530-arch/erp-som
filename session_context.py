# session_context.py

_session = {
    "usuario": None,
    "rol": None,
    "token": None,
    "company_code": "MSL-CR",
    "company_name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
}


def set_user_context(usuario, rol, token=None, company_code=None, company_name=None):
    _session["usuario"] = usuario
    _session["rol"] = rol
    _session["token"] = token
    if company_code:
        _session["company_code"] = company_code
    if company_name:
        _session["company_name"] = company_name


def get_token():
    return _session.get("token")


def get_user():
    return _session.get("usuario")


def get_rol():
    return _session.get("rol")


def get_company_code():
    return _session.get("company_code") or "MSL-CR"


def get_company_name():
    return _session.get("company_name") or "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL"
