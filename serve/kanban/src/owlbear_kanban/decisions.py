"""Decision request file helpers for kanban agents.

This module manages lightweight decision request (DR) files stored under a
``decisions/`` directory with ``pending/`` and ``resolved/`` subdirectories.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ruamel.yaml import YAML

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


def _append_summary(
    engine: DecisionEngine, task_id: int | str, response: str, body: str
) -> None:
    """Append a compact DR summary to the task body."""
    summary = canonical_summary(response, body)
    engine.edit_task(task_id, append_body=summary)


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
        try:
            os.link(path, candidate)
        except FileExistsError:
            counter += 1
            continue
        try:
            path.unlink()
        except OSError:
            if candidate.exists():
                candidate.unlink()
            raise
        return candidate


def create_dr(  # noqa: PLR0913
    decisions_dir: Path,
    engine: DecisionEngine,
    *,
    task_id: int,
    agent: str,
    request_type: str,
    body: str,
) -> Path:
    """Create a pending DR file atomically, then block the task.

    Uses ``O_EXCL`` for creation and retries collisions with ``-2``, ``-3``,
    etc. suffixes.
    """
    pending_dir = decisions_dir / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    created = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    frontmatter = (
        "---\n"
        f"task_id: {task_id}\n"
        f"agent: {agent}\n"
        f"request_type: {request_type}\n"
        f"created: '{created}'\n"
        "response: pending\n"
        "---\n\n"
    )
    content = frontmatter + body

    slug = _slugify(request_type)
    counter = 1
    while True:
        filename = (
            f"{task_id}-{slug}.md" if counter == 1 else f"{task_id}-{slug}-{counter}.md"
        )
        candidate = pending_dir / filename
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            break
        except FileExistsError:
            counter += 1

    try:
        engine.edit_task(task_id, blocked=True, block_reason="DR pending")
    except Exception:
        if candidate.exists():
            candidate.unlink()
        raise

    return candidate


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
