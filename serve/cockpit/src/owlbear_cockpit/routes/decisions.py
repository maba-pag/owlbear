"""Cockpit decisions API routes."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_cockpit.deps import get_decisions_dir, get_engine
from owlbear_kanban.decisions import canonical_summary, move_to_resolved, parse_dr
from owlbear_kanban.errors import ConcurrencyError

router = APIRouter()

_DECISION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

_DecisionsDir = Annotated[Path, Depends(get_decisions_dir)]
_Engine = Annotated[object, Depends(get_engine)]


class ResolveRequest(BaseModel):
    """Request body for POST /decisions/{id}/resolve."""

    model_config = ConfigDict(extra="forbid")

    response: Literal["approved", "needs-info", "rejected"]
    notes: str | None = Field(default=None, max_length=10_000)


class PendingDRItem(BaseModel):
    """One pending decision request returned by cockpit API."""

    id: str
    task_id: int
    agent: str
    request_type: str
    created: str
    title: str
    body: str
    body_preview: str


class PendingDRResponse(BaseModel):
    """Response payload for GET /decisions/pending."""

    count: int
    items: list[PendingDRItem]


def _extract_title(body: str, fallback: str) -> str:
    """Extract a title from the first markdown heading, else fallback."""
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
        return stripped  # pragma: no cover - title without markdown heading
    return fallback  # pragma: no cover - empty body fallback


def _append_response_section(body: str, response: str, notes: str | None) -> str:
    """Append the markdown response section while preserving existing body text."""
    suffix_lines = ["## Response", f"- response: {response}"]
    if notes is not None:
        suffix_lines.append(notes)
    suffix = "\n".join(suffix_lines)
    cleaned_body = body.rstrip("\n")
    if cleaned_body:
        return f"{cleaned_body}\n\n{suffix}\n"
    return f"{suffix}\n"  # pragma: no cover - empty-body defensive path


def _rewrite_response(path: Path, meta: dict[str, object], body: str) -> None:
    """Persist updated frontmatter + markdown body."""
    yaml = YAML()
    stream = StringIO()
    yaml.dump(meta, stream)
    frontmatter = stream.getvalue().rstrip("\n")
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8", newline="\n")


def _validate_decision_id(decision_id: str) -> None:
    """Validate decision id against the allowlist pattern."""
    if not _DECISION_ID_PATTERN.fullmatch(decision_id):
        raise HTTPException(status_code=422, detail="Invalid decision id")


@router.get("/decisions/pending", response_model=PendingDRResponse)
def list_pending_decisions(decisions_dir: _DecisionsDir) -> PendingDRResponse:
    """List pending decision requests as cockpit-ready JSON."""
    pending_dir = decisions_dir / "pending"
    if not pending_dir.is_dir():
        return {"count": 0, "items": []}

    items: list[PendingDRItem] = []
    for path in sorted(pending_dir.glob("*.md")):
        try:
            meta, body = parse_dr(path)
        except (TypeError, ValueError, YAMLError):
            continue

        if str(meta.get("response", "")) != "pending":
            continue

        preview = body.strip()[:200]
        try:
            item = PendingDRItem.model_validate(
                {
                    "id": path.stem,
                    "task_id": meta.get("task_id"),
                    "agent": meta.get("agent", ""),
                    "request_type": meta.get("request_type", ""),
                    "created": meta.get("created", ""),
                    "title": _extract_title(body, path.stem),
                    "body": body.strip(),
                    "body_preview": preview,
                }
            )
        except ValidationError:
            continue

        items.append(item)

    return PendingDRResponse(count=len(items), items=items)


@router.post("/decisions/{decision_id}/resolve")
def resolve_decision(
    decision_id: str,
    req: ResolveRequest,
    decisions_dir: _DecisionsDir,
    engine: _Engine,
) -> dict[str, object]:
    """Resolve one DR with immediate lifecycle side effects."""
    _validate_decision_id(decision_id)

    pending_path = decisions_dir / "pending" / f"{decision_id}.md"
    resolved_path = decisions_dir / "resolved" / f"{decision_id}.md"

    if not pending_path.exists():
        if resolved_path.exists():
            try:
                resolved_meta, _ = parse_dr(resolved_path)
            except (TypeError, ValueError, YAMLError) as exc:
                detail = "Invalid decision file format"
                raise HTTPException(status_code=422, detail=detail) from exc

            # Requests previously resolved through this endpoint are treated as
            # duplicate submissions and keep FastAPI's {detail} 404 envelope.
            if str(resolved_meta.get("resolved_by", "")) == "cockpit-api":
                detail = f"Decision {decision_id!r} not found"
                raise HTTPException(status_code=404, detail=detail)

            msg = f"Decision {decision_id!r} is already resolved"
            code = "ERR_STALE"
            raise ConcurrencyError(code, msg)

        detail = f"Decision {decision_id!r} not found"
        raise HTTPException(status_code=404, detail=detail)

    try:
        meta, body = parse_dr(pending_path)
    except (
        TypeError,
        ValueError,
        YAMLError,
    ) as exc:  # pragma: no cover - defensive malformed file guard
        detail = "Invalid decision file format"
        raise HTTPException(status_code=422, detail=detail) from exc

    current_response = str(meta.get("response", "pending"))
    if current_response != "pending":
        msg = f"Decision {decision_id!r} is already resolved"
        code = "ERR_STALE"
        raise ConcurrencyError(code, msg)

    updated = dict(meta)
    updated["response"] = req.response
    updated["resolved_by"] = "cockpit-api"
    body_with_response = _append_response_section(body, req.response, req.notes)
    _rewrite_response(pending_path, updated, body_with_response)

    task_id = updated.get("task_id")
    try:
        engine.edit_task(task_id, append_body=canonical_summary(req.response, body))
        if req.response in {"approved", "rejected"}:
            engine.edit_task(task_id, blocked=False)
    except FileNotFoundError:
        # Legacy callers may resolve DRs that point to tasks outside this engine.
        pass

    move_to_resolved(pending_path, resolved_path.parent)

    return {"id": decision_id, "response": req.response}
