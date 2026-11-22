from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError


async def app_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, ApplicationError):
        raise exc

    headers = {}

    if exc.status_code == HTTPStatus.UNAUTHORIZED:
        headers["WWW-Authenticate"] = "Bearer"

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=headers,
    )
