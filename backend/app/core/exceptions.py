"""Domain exceptions and the handlers that translate them into the API envelope.

Keeping exceptions framework-agnostic (plain Python classes) lets services
raise them without importing FastAPI; only the handlers know about HTTP.
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for all domain exceptions."""

    status_code: int = 500
    default_message: str = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class NotFoundError(AppError):
    """Resource not found."""

    status_code = 404
    default_message = "Resource not found"


class AuthError(AppError):
    """Invalid credentials, missing/expired token, etc."""

    status_code = 401
    default_message = "Authentication failed"


class ValidationError(AppError):
    """Request semantically invalid (beyond Pydantic schema validation)."""

    status_code = 422
    default_message = "Validation error"


class ConflictError(AppError):
    """Resource conflict (e.g. email already registered)."""

    status_code = 409
    default_message = "Conflict"


def _envelope(error: str) -> dict:
    return {"success": False, "data": None, "error": error}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that wrap exceptions in the {success, data, error} envelope."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.get("loc", []) if part != "body")
            message = first.get("msg", "Validation error")
            payload = f"{location}: {message}" if location else message
        else:
            payload = "Validation error"
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "error": payload,
                "details": jsonable_encoder(errors),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return JSONResponse(status_code=exc.status_code, content=_envelope(detail))

    @app.exception_handler(Exception)
    async def _handle_generic(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=_envelope("Internal server error"))
