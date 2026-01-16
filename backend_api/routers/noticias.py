from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from dependencies import get_db, get_current_user
from security import _check_admin_role

router = APIRouter(
    prefix="/noticias",
    tags=["Noticias HHRR"]
)

# ============================================================
# POST — PUBLICAR NOTICIAS
# SOLO admin / master
# ============================================================
@router.post("")
def publicar_noticias(
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    noticia_1 = payload.get("noticia_1")
    noticia_2 = payload.get("noticia_2")
    noticia_3 = payload.get("noticia_3")
    noticia_4 = payload.get("noticia_4")
    noticia_5 = payload.get("noticia_5")

    if not any([noticia_1, noticia_2, noticia_3, noticia_4, noticia_5]):
        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos una noticia"
        )

    try:
        cur.execute(
            """
            INSERT INTO noticias (
                created_by,
                noticia_1,
                noticia_2,
                noticia_3,
                noticia_4,
                noticia_5
            )
            VALUES (
                %(created_by)s,
                %(noticia_1)s,
                %(noticia_2)s,
                %(noticia_3)s,
                %(noticia_4)s,
                %(noticia_5)s
            )
            RETURNING *
            """,
            {
                "created_by": current_user["usuario"],
                "noticia_1": noticia_1,
                "noticia_2": noticia_2,
                "noticia_3": noticia_3,
                "noticia_4": noticia_4,
                "noticia_5": noticia_5,
            }
        )

        noticia = cur.fetchone()
        conn.commit()
        return noticia

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# GET — OBTENER ÚLTIMA PUBLICACIÓN
# TODOS LOS USUARIOS AUTENTICADOS
# ============================================================
@router.get("/latest")
def obtener_ultima_noticia(
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            id,
            created_at,
            created_by,
            noticia_1,
            noticia_2,
            noticia_3,
            noticia_4,
            noticia_5
        FROM noticias
        ORDER BY created_at DESC
        LIMIT 1
        """
    )

    noticia = cur.fetchone()

    return noticia or {}
