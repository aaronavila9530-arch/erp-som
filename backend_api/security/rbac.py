from fastapi import Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user


def require_permission(module: str, action: str):

    """
    🔐 RBAC ERP-SOM — ULTRA BLINDADO

    Prioridad:

    1️⃣ MASTER → acceso total
    2️⃣ Overrides por usuario
    3️⃣ Permiso exacto (module + action)
    4️⃣ Fallback → permiso por módulo (CRÍTICO FIX)
    5️⃣ Wildcard (*)
    """

    def checker(
        user=Depends(get_current_user),
        conn=Depends(get_db)
    ):

        # =====================================================
        # VALIDACIÓN BASE
        # =====================================================
        if not user:
            raise HTTPException(401, "Usuario no autenticado")

        username = (user.get("usuario") or "").strip().lower()
        role = (user.get("rol") or "").strip().lower()

        module_code = (module or "").strip().lower()
        action_code = (action or "").strip().lower()

        # DEBUG CLAVE
        print(f"🔐 RBAC CHECK → user={username} role={role} module={module_code} action={action_code}")

        # =====================================================
        # MASTER → ACCESO TOTAL
        # =====================================================
        if role == "master":
            return True

        # =====================================================
        # NORMALIZACIÓN DE ACTIONS (🔥 FIX CRÍTICO)
        # =====================================================
        # Evita falsos 403 en endpoints tipo /me/summary
        if action_code in ("me", "summary", "me/summary"):
            action_code = "ot_log"

        # =====================================================
        # OVERRIDES POR USUARIO
        # =====================================================
        USER_OVERRIDES = {

            "surveyor": {
                "comercial": ["view"],
                "hhrre": ["view"],
                "informes": ["view", "create", "edit", "submit"],
            },

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

        # =====================================================
        # CONSULTA RBAC
        # =====================================================
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # -----------------------------------------------------
        # 1️⃣ PERMISO EXACTO
        # -----------------------------------------------------
        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND module = %s
              AND action = %s
            LIMIT 1
        """, (role, module_code, action_code))

        perm = cur.fetchone()

        if perm:
            if perm["allowed"]:
                return True
            raise HTTPException(403, "Acceso denegado (regla exacta)")

        # -----------------------------------------------------
        # 2️⃣ FALLBACK → SOLO MÓDULO (🔥 FIX REAL)
        # -----------------------------------------------------
        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND module = %s
              AND action IN ('view', '*')
            ORDER BY
              CASE WHEN action = 'view' THEN 1 ELSE 2 END
            LIMIT 1
        """, (role, module_code))

        perm = cur.fetchone()

        if perm and perm["allowed"]:
            return True

        # -----------------------------------------------------
        # 3️⃣ WILDCARD GLOBAL
        # -----------------------------------------------------
        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND module = '*'
              AND action = '*'
            LIMIT 1
        """, (role,))

        perm = cur.fetchone()

        if perm and perm["allowed"]:
            return True

        # =====================================================
        # DENEGADO FINAL
        # =====================================================
        raise HTTPException(
            403,
            f"Acceso denegado por RBAC → role={role} module={module_code} action={action_code}"
        )

    return checker