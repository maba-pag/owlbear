"""The token guard both hosts put on their API, and the answer to an error no route caught."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from owlbear_delivery_next.git.command_failure import failure, streams

ADMITTED = "owlbear.admitted"  # set in a request's scope once the token admitted it to a guarded route


def admit(request: Request, expected: bytes) -> None:
    """Refuse a request without the token; mark one with it, so an error it meets is answered whole."""
    if not secrets.compare_digest(request.headers.get("authorization", "").encode(), expected):
        raise HTTPException(401, "token required")
    request.scope[ADMITTED] = True


async def uncaught(request: Request, exc: Exception) -> Response:
    """An error no route caught: whole to a caller the token admitted, Starlette's own 500 to a page or asset read.

    Pages and assets are served without the token (D-01M6K23PAH492JQC3EQHD074MN). Starlette re-raises the error after
    this answer and the server logs its traceback, which leaves out what a failed command printed: that is added to
    the error as a note, once, for every request, so the host log has it whole too.
    """
    if request.scope.get(ADMITTED):
        answer: Response = JSONResponse({"detail": failure(exc)}, status_code=500)
    else:
        answer = PlainTextResponse("Internal Server Error", status_code=500)
    if (said := streams(exc)) and said not in getattr(exc, "__notes__", ()):
        exc.add_note(said)
    return answer
