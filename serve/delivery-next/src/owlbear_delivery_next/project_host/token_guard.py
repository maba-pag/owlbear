"""The token guard both hosts put on their API, and the answer to an error no route caught."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from owlbear_delivery_next.git.command_failure import failure

ADMITTED = "owlbear.admitted"  # set in a request's scope once the token admitted it to a guarded route


def admit(request: Request, expected: bytes) -> None:
    """Refuse a request without the token; mark one with it, so an error it meets is answered whole."""
    if not secrets.compare_digest(request.headers.get("authorization", "").encode(), expected):
        raise HTTPException(401, "token required")
    request.scope[ADMITTED] = True


async def uncaught(request: Request, exc: Exception) -> Response:
    """An error no route caught: whole to a caller the token admitted, Starlette's own 500 to a page or asset read.

    Pages and assets are served without the token (D-01M6K23PAH492JQC3EQHD074MN). Starlette re-raises the error after
    this answer, so the server still logs its traceback.
    """
    if request.scope.get(ADMITTED):
        return JSONResponse({"detail": failure(exc)}, status_code=500)
    return PlainTextResponse("Internal Server Error", status_code=500)
