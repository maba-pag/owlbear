"""Effective Retro grades and their append-only evidence corrections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

CONTRACT = "persisted-event-1"
PENDING = "awaiting-correction"


def corrected_id(original: str) -> str:
    """The once-only storage identity of a grade corrected under this evidence contract."""
    return f"{original}-{CONTRACT}"


def effective(
    grades: Iterable[Mapping[str, Any]],
    requests: Iterable[Mapping[str, Any]],
    *,
    include_pending: bool = False,
) -> list[dict[str, Any]]:
    """Current judgements with stable logical IDs; originals stay in the ledger as history.

    A request registers its exact historical cohort before it can be taken or paid. While awaiting its correction,
    a grade is available only as an explicit pending display row, never as trusted judging/proposal evidence.
    """
    first: dict[str, dict[str, Any]] = {}
    for grade in grades:
        first.setdefault(grade["id"], dict(grade))
    pending = {rid: gid for request in requests for rid, gid in (request.get("corrections") or {}).items()}
    out = []
    for gid, grade in first.items():
        if grade.get("supersedes"):
            continue
        corrected = first.get(corrected_id(gid))
        if corrected is not None and corrected.get("supersedes") == gid:
            out.append(corrected | {"id": gid, "history_id": corrected["id"]})
        elif pending.get(grade["record"]) == gid:
            if include_pending:
                out.append(
                    grade
                    | {
                        "grade": PENDING,
                        "reason": "Awaiting corrected evidence; the original judgement remains in history.",
                        "should": "",
                        "preliminary": False,
                    }
                )
        else:
            out.append(grade)
    return out
