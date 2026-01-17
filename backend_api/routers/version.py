from fastapi import APIRouter

router = APIRouter(
    prefix="/version",
    tags=["Version"]
)

@router.get("/")
def check_version():
    return {
        "TEST": "SI VES ESTO, ESTE ARCHIVO ESTA ACTIVO"
    }
