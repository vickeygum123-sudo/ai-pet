"""Stable API error helpers for the backend foundation."""

from __future__ import annotations

from fastapi import HTTPException, status


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """Create a stable HTTPException detail payload."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


AUTH_HEADER_REQUIRED = api_error(
    status.HTTP_401_UNAUTHORIZED,
    "AUTH_HEADER_REQUIRED",
    "Missing X-Account-Id header for MVP auth placeholder.",
)

ACCOUNT_CONFLICT = api_error(
    status.HTTP_409_CONFLICT,
    "ACCOUNT_CONFLICT",
    "Account creation conflict.",
)

DEVICE_CONFLICT = api_error(
    status.HTTP_409_CONFLICT,
    "DEVICE_CONFLICT",
    "Device registration conflict.",
)
