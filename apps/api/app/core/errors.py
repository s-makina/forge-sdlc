"""Structured JSON error handling for the API."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException


def _error_payload(code: str, message: str, details: object | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    detail = exc.detail if isinstance(exc, StarletteHTTPException) else str(exc)
    status_code = (
        exc.status_code
        if isinstance(exc, StarletteHTTPException)
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    return JSONResponse(
        status_code=status_code,
        content=_error_payload(code="http_error", message=str(detail)),
    )


def _json_safe(value: object) -> object:
    """Recursively replace non-JSON-serializable values with their ``str()`` form.

    Validator exceptions can leak into a ``RequestValidationError``'s ``ctx``,
    which ``JSONResponse`` (via ``json.dumps``) cannot serialize. Normalize those
    up front so validation failures always return a clean 422 instead of a 500.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    details = _json_safe(exc.errors()) if isinstance(exc, RequestValidationError) else None
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload(
            code="validation_error",
            message="Request validation failed",
            details=details,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register JSON error handlers on the app."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
