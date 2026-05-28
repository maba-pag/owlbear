"""Decision request file helpers for kanban agents.

This module manages lightweight decision request (DR) files stored under a
``decisions/`` directory with ``pending/`` and ``resolved/`` subdirectories.
"""

from __future__ import annotations

import logging
import re
from io import StringIO
from pathlib import Path
from typing import Protocol

from ruamel.yaml import YAML

from .errors import ConcurrencyError

LOGGER = logging.getLogger(__name__)


class DecisionEngine(Protocol):
    """Minimal engine protocol required by DR helpers."""

    _kanban_dir: Path

    def edit_task(self, task_id: int | str, **kwargs: object) -> object:
        """Apply an edit to a task."""


def _slugify(text: str) -> str:
    """Return a filesystem-safe slug for DR filenames."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "decision"


def parse_dr(path: Path) -> tuple[dict[str, object], str]:
    """Parse frontmatter and markdown body from a DR file."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):  # pragma: no cover - defensive input guard
        msg = f"Invalid DR file (missing opening delimiter): {path}"
        raise ValueError(msg)

    lines = content.splitlines()
    closing_idx: int | None = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_idx = idx
            break

    if closing_idx is None:  # pragma: no cover - defensive input guard
        msg = f"Invalid DR file (missing closing delimiter): {path}"
        raise ValueError(msg)

    yaml_text = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])
    data = YAML(typ="safe").load(yaml_text) or {}
    if not isinstance(data, dict):  # pragma: no cover - defensive input guard
        msg = f"Invalid DR file (frontmatter must be mapping): {path}"
        raise TypeError(msg)
    return data, body


def canonical_summary(response: str, body: str) -> str:
    """Return canonical decision summary appended to the linked task."""
    return f"## Decision Request\n- response: {response}\n- source: {body.strip() or '(no body)'}"


def _append_summary(engine: DecisionEngine, task_id: int | str, response: str, body: str) -> None:
    """Append a compact DR summary to the task body."""
    summary = canonical_summary(response, body)
    engine.edit_task(task_id, append_body=summary)


def _append_response_section(body: str, response: str, notes: str | None) -> str:
    """Append a response section to an existing DR body."""
    suffix_lines = ["## Response", f"- response: {response}"]
    if notes is not None:
        suffix_lines.append(notes)
    suffix = "\n".join(suffix_lines)
    cleaned_body = body.rstrip("\n")
    if cleaned_body:
        return f"{cleaned_body}\n\n{suffix}\n"
    return f"{suffix}\n"


def _rewrite_response(path: Path, meta: dict[str, object], body: str) -> None:
    """Persist updated frontmatter and body to a DR file."""
    yaml = YAML()
    stream = StringIO()
    yaml.dump(meta, stream)
    frontmatter = stream.getvalue().rstrip("\n")
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8", newline="\n")


def _resolve_decisions_dir(engine: DecisionEngine) -> Path:
    """Resolve decisions directory from an engine instance."""
    kanban_dir = getattr(engine, "_kanban_dir", None)
    if kanban_dir is None:  # pragma: no cover - production engines always have this
        msg = "Cannot infer decisions directory from engine"
        raise ValueError(msg)
    return Path(kanban_dir) / "decisions"


def _resolved_candidate(base_path: Path, counter: int) -> Path:
    """Return the nth collision-safe resolved path candidate."""
    if counter == 1:
        return base_path
    return base_path.with_name(f"{base_path.stem}-{counter}{base_path.suffix}")


def move_to_resolved(path: Path, resolved_dir: Path) -> Path:
    """Move *path* into resolved_dir without overwriting prior resolutions."""
    resolved_dir.mkdir(parents=True, exist_ok=True)
    base_path = resolved_dir / path.name
    counter = 1
    while True:
        candidate = _resolved_candidate(base_path, counter)
        if candidate.exists():
            counter += 1
            continue
        path.rename(candidate)
        return candidate


def resolve_decision(
    path: Path,
    response: str,
    engine: DecisionEngine,
    *,
    notes: str | None = None,
    resolved_by: str = "unknown",
) -> Path:
    """Resolve one pending DR file and return the moved path.

    Raises:
        ConcurrencyError: DR is already resolved (response is not pending).
    """
    meta, body = parse_dr(path)
    current_response = str(meta.get("response", "pending"))
    if current_response != "pending":
        msg = f"Decision {path.name!r} is already resolved"
        code = "ERR_STALE"
        raise ConcurrencyError(code, msg)

    updated = dict(meta)
    updated["response"] = response
    updated["resolved_by"] = resolved_by
    body_with_response = _append_response_section(body, response, notes)
    _rewrite_response(path, updated, body_with_response)

    task_id = updated.get("task_id")
    try:
        _append_summary(engine, task_id, response, body)
        if response in {"approved", "rejected"}:
            engine.edit_task(task_id, blocked=False)
    except FileNotFoundError:
        # Legacy callers may resolve DRs that point outside the active engine.
        pass

    resolved_dir = path.parent.parent / "resolved"
    return move_to_resolved(path, resolved_dir)


def resolve_pending_drs(
    decisions_or_engine: Path | DecisionEngine,
    engine: DecisionEngine | None = None,
) -> list[Path]:
    """Resolve pending DR files and return moved files.

    Supports both call forms:
    - ``resolve_pending_drs(decisions_dir, engine)``
    - ``resolve_pending_drs(engine)``
    """
    if engine is None:
        engine = decisions_or_engine
        decisions_dir = _resolve_decisions_dir(engine)
    else:
        decisions_dir = Path(decisions_or_engine)

    pending_dir = decisions_dir / "pending"
    resolved_dir = decisions_dir / "resolved"
    if not pending_dir.exists():
        return []
    resolved_dir.mkdir(parents=True, exist_ok=True)

    moved: list[Path] = []
    for path in sorted(pending_dir.glob("*.md")):
        try:
            meta, body = parse_dr(path)
            response = str(meta.get("response", "pending"))

            if response == "pending":
                continue

            if response in {"approved", "rejected"}:
                task_id = meta.get("task_id")
                _append_summary(engine, task_id, response, body)
                engine.edit_task(task_id, blocked=False)
                dest = move_to_resolved(path, resolved_dir)
                moved.append(dest)
                continue

            if response == "needs-info":
                task_id = meta.get("task_id")
                _append_summary(engine, task_id, response, body)
                dest = move_to_resolved(path, resolved_dir)
                moved.append(dest)
                continue

            LOGGER.warning("Unknown DR response '%s' in %s; skipping", response, path)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed processing DR file %s: %s", path, exc)
            continue

    return moved
