"""Cockpit decisions API routes."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_cockpit.deps import get_decisions_dir

router = APIRouter()

_DECISION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

_DecisionsDir = Annotated[Path, Depends(get_decisions_dir)]


class ResolveRequest(BaseModel):
    """Request body for POST /decisions/{id}/resolve."""

    model_config = ConfigDict(extra="forbid")

    response: Literal["approved", "needs-info", "rejected", "completed"]
    notes: str | None = None


def _parse_dr(path: Path) -> tuple[dict[str, object], str]:
    """Parse frontmatter and markdown body from a decision file."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if not lines or lines[0].strip() != "---":  # pragma: no cover - malformed file guard
        msg = f"Invalid decision file (missing opening delimiter): {path}"
        raise ValueError(msg)

    closing_idx: int | None = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_idx = idx
            break

    if closing_idx is None:  # pragma: no cover - malformed file guard
        msg = f"Invalid decision file (missing closing delimiter): {path}"
        raise ValueError(msg)

    yaml_text = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])
    data = YAML(typ="safe").load(yaml_text) or {}
    if not isinstance(data, dict):  # pragma: no cover - malformed file guard
        msg = f"Invalid decision file (frontmatter must be mapping): {path}"
        raise TypeError(msg)
    return data, body


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


def _find_decision_path(decisions_dir: Path, decision_id: str) -> Path:
    """Resolve a decision path from pending first, then resolved.

    Raises HTTPException(422) if decision_id does not match the allowlist
    pattern ``^[a-zA-Z0-9][a-zA-Z0-9_-]*$`` (path traversal protection).
    Raises FileNotFoundError if the id is valid but no file exists.
    """
    if not _DECISION_ID_PATTERN.fullmatch(decision_id):
        raise HTTPException(status_code=422, detail="Invalid decision id")

    pending = decisions_dir / "pending" / f"{decision_id}.md"
    if pending.exists():
        return pending
    resolved = decisions_dir / "resolved" / f"{decision_id}.md"
    if resolved.exists():  # pragma: no cover - compatibility with already-moved files
        return resolved
    raise FileNotFoundError(decision_id)


@router.get("/decisions/pending")
def list_pending_decisions(decisions_dir: _DecisionsDir) -> dict[str, object]:
    """List pending decision requests as cockpit-ready JSON."""
    pending_dir = decisions_dir / "pending"
    if not pending_dir.is_dir():
        return {"count": 0, "items": []}

    items: list[dict[str, object]] = []
    for path in sorted(pending_dir.glob("*.md")):
        try:
            meta, body = _parse_dr(path)
        except (TypeError, ValueError, YAMLError):
            continue

        if str(meta.get("response", "")) != "pending":
            continue

        preview = body.strip()[:200]
        items.append(
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

    return {"count": len(items), "items": items}


@router.post("/decisions/{decision_id}/resolve")
def resolve_decision(
    decision_id: str,
    req: ResolveRequest,
    decisions_dir: _DecisionsDir,
) -> dict[str, object]:
    """Update DR response and append a response section in-place."""
    try:
        path = _find_decision_path(decisions_dir, decision_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id!r} not found") from None

    try:
        meta, body = _parse_dr(path)
    except (TypeError, ValueError, YAMLError) as exc:  # pragma: no cover - defensive malformed file guard
        raise HTTPException(status_code=422, detail="Invalid decision file format") from exc

    updated = dict(meta)
    updated["response"] = req.response
    body_with_response = _append_response_section(body, req.response, req.notes)
    _rewrite_response(path, updated, body_with_response)

    return {"id": decision_id, "response": req.response}
