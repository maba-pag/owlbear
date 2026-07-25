"""Stable HTTP envelopes for native runtime conflicts and diagnostics."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel  # noqa: TC002 - runtime model serialization


def conflict(  # noqa: PLR0913 - one centralized stable conflict envelope
    *,
    code: str,
    detail: str,
    current_delivery_digest: str,
    diagnostic: BaseModel | None = None,
    lower_code: str | None = None,
    target: str | None = None,
) -> HTTPException:
    """Return one stable conflict envelope with current authority identity."""
    payload: dict[str, Any] = {
        "code": code,
        "detail": detail,
        "current_delivery_digest": current_delivery_digest,
    }
    if diagnostic is not None:
        payload.update(diagnostic.model_dump(mode="json", exclude_none=True))
        payload["code"] = str(payload["code"])
    if lower_code is not None:
        payload["lower_code"] = lower_code
    if target is not None:
        payload["target"] = target
    return HTTPException(status_code=409, detail=payload)


__all__ = ["conflict"]
