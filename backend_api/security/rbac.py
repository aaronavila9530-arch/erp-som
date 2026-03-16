from fastapi import Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user


def require_permission(module: str, action: str):

    """
    RBAC ERP-SOM

    Prioridad:

    1️⃣ MASTER → acceso total
    2️⃣ Overrides por usuario
    3️⃣ Permisos por rol (tabla rbac_permissions)
    """

    def checker(
        user=Depends(get_current_user),
        conn=Depends(get_db)
    ):

        if not user:
            raise HTTPException(401, "Usuario no autenticado")

        username = (user.get("usuario") or "").strip().lower()
        role = (user.get("rol") or "").strip().lower()

        module_code = module.strip().lower()
        action_code = action.strip().lower()

        # =========================================
        # MASTER → ACCESO TOTAL
        # =========================================

        if role == "master":
            return True

        # =========================================
        # OVERRIDES POR USUARIO
        # =========================================

        USER_OVERRIDES = {

            # SURVEYOR
            "surveyor": {

                "comercial": ["view"],
                "hhrre": ["view"],
                "informes": ["view", "create", "edit", "submit"],

            },

            # CONTABILIDAD
            "accountant": {

                "finanzas": ["view", "create", "edit"],
                "dashboard": ["view"]

            }

        }

        if username in USER_OVERRIDES:

            user_modules = USER_OVERRIDES[username]

            if module_code in user_modules:

                if action_code in user_modules[module_code]:
                    return True

                raise HTTPException(
                    403,
                    f"Acceso denegado para usuario {username}"
                )

        # =========================================
        # PERMISOS POR ROL
        # =========================================

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND (module = %s OR module='*')
              AND (action = %s OR action='*')
            ORDER BY
              CASE
                WHEN action = %s THEN 1
                WHEN action = '*' THEN 2
                ELSE 3
              END
            LIMIT 1
        """, (
            role,
            module_code,
            action_code,
            action_code
        ))

        perm = cur.fetchone()

        if not perm or not perm["allowed"]:
            raise HTTPException(
                403,
                "Acceso denegado por RBAC"
            )

        return True

    return checker