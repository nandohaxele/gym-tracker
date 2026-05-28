"""Standard API response envelope.

All endpoints return this shape (per api_contract.md):
    { "success": true,  "data": <payload>, "error": null }
    { "success": false, "data": null,      "error": "message" }
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Generic response wrapper. Useful as an OpenAPI response_model hint."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None


def ok(data: Any = None) -> dict[str, Any]:
    """Build a success envelope. `data` may be a dict, list, or Pydantic BaseModel."""
    return {"success": True, "data": data, "error": None}


def fail(error: str) -> dict[str, Any]:
    """Build an error envelope."""
    return {"success": False, "data": None, "error": error}
