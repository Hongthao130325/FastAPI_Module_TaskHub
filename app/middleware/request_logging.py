import logging
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers = dict(scope.get("headers", []))
        incoming_request_id = request_headers.get(b"x-request-id", b"").decode(
            "latin-1"
        )

        request_id = incoming_request_id[:128] if incoming_request_id else str(uuid4())

        scope.setdefault("state", {})["request_id"] = request_id

        method = scope["method"]
        path = scope["path"]
        start_time = time.perf_counter()
        status_code = 500

        logger.info(
            "Request started: method=%s path=%s request_id=%s",
            method,
            path,
            request_id,
        )

        async def send_with_metadata(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.perf_counter() - start_time

                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                headers.append(
                    (
                        b"x-process-time",
                        f"{process_time:.6f}".encode("ascii"),
                    )
                )

                message = {**message, "headers": headers}

            await send(message)

        try:
            await self.app(scope, receive, send_with_metadata)
        except Exception:
            process_time = time.perf_counter() - start_time

            logger.exception(
                "Request failed: method=%s path=%s status_code=%s "
                "request_id=%s process_time=%.6f",
                method,
                path,
                status_code,
                request_id,
                process_time,
            )
            raise

        process_time = time.perf_counter() - start_time

        logger.info(
            "Request completed: method=%s path=%s status_code=%s "
            "request_id=%s process_time=%.6f",
            method,
            path,
            status_code,
            request_id,
            process_time,
        )
