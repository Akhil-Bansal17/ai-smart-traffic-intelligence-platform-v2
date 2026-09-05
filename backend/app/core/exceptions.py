"""
Centralized exception handling.

Rule: no internal stack trace, file path, or raw exception message
ever reaches the client. Every error response has the same shape:

    {"error": {"code": "...", "message": "..."}}

Application code should raise AppException (or a subclass) for
expected/handled error conditions. Anything else (a genuine bug)
is caught by the catch-all handler below, logged in full server-side,
and returned to the client as a generic 500 with no details.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    """Base class for expected application errors with a safe, user-facing message."""

    def __init__(self, message: str, code: str = "app_error", status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning("Handled AppException: %s (%s)", exc.message, exc.code)
        return _error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("Validation error on %s: %s", request.url.path, exc.errors())
        return _error_response("validation_error", "The request was invalid.", status.HTTP_422_UNPROCESSABLE_ENTITY)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response("http_error", str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Full detail goes to the server log only - never to the client.
        logger.exception("Unhandled exception on %s", request.url.path)
        return _error_response(
            "internal_error", "An unexpected error occurred.", status.HTTP_500_INTERNAL_SERVER_ERROR
        )
