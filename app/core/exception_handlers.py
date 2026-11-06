from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.constants import TASK_NOT_FOUND_MESSAGE
from app.core.exceptions import NotFoundException


async def not_found_exception_handler(
    request: Request, exc: NotFoundException
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": TASK_NOT_FOUND_MESSAGE})
