import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.availability import accepts_traffic, role
from database import probe_database

router = APIRouter(prefix='/health', tags=['Availability'])


def result(payload, status=200):
    return JSONResponse(payload, status_code=status, headers={'Cache-Control':'no-store'})


@router.get('/live')
def live():
    return result({'status':'alive'})


@router.get('/ready')
def ready():
    if not accepts_traffic():
        return result({'status':'not_ready', 'reason':'standby_not_validated'}, 503)
    if not probe_database():
        return result({'status':'not_ready', 'reason':'database_unavailable'}, 503)
    revision = os.getenv('SOM_RELEASE_SHA') or os.getenv('RAILWAY_GIT_COMMIT_SHA', '')
    return result({'status':'ready', 'role':role(), 'revision':revision[:40]})
