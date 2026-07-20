from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns each request a request_id so log lines across the pipeline can be correlated."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        logger = logging.getLogger("app.request")

        try:
            logger.info("request started", extra={"method": request.method, "path": request.url.path})
            response = await call_next(request)
            logger.info("request finished", extra={"status_code": response.status_code})
        finally:
            _request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
