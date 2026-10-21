"""Fail closed on a standby until the operator completes the failover checklist."""
import os
from starlette.responses import JSONResponse


def role():
    value = os.getenv('SOM_DEPLOYMENT_ROLE', 'primary').strip().lower()
    if value not in {'primary', 'standby'}:
        raise RuntimeError('SOM_DEPLOYMENT_ROLE must be primary or standby')
    return value


def enabled(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes'}


def accepts_traffic():
    return role() == 'primary' or enabled('SOM_STANDBY_VALIDATED')


def runs_jobs():
    return role() == 'primary' and enabled('SOM_BACKGROUND_JOBS', default=True)


class StandbyGate:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope.get('path') not in {'/health/live', '/health/ready'}:
            if not accepts_traffic():
                response = JSONResponse({'detail': 'Standby not enabled for traffic'}, status_code=503,
                                        headers={'Retry-After': '30', 'Cache-Control': 'no-store'})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
