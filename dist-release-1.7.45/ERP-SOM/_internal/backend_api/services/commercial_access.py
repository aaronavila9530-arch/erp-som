from fastapi import Header, HTTPException


BOARD_ONLY_USERS = frozenset({"surveyor01", "surveyor02", "surveyor03"})


def require_commercial_detail(x_user: str = Header("", alias="X-User")):
    # Match the desktop navigation restriction at the API boundary as well.
    if x_user.strip().lower() in BOARD_ONLY_USERS:
        raise HTTPException(403, "Este usuario solo tiene acceso a la pizarra comercial")
