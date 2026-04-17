"""Task file I/O for the native kanban engine.

Provides read_task, write_task, validate_path_containment, generate_slug,
and make_task_filename for reading and writing task files in the kanban
tasks directory.

File format: YAML frontmatter delimited by ``---`` lines, followed by
a markdown body section.

    ---
    id: 42
    title: My task
    status: todo
    ...
    ---

    ## Body markdown

Timestamps are preserved as plain strings to avoid Go 7-digit nanosecond
→ Python 6-digit microsecond truncation on round-trips.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from owlbear_kanban.models import Task

# ---------------------------------------------------------------------------
# YAML instance that keeps timestamps as plain strings
# ---------------------------------------------------------------------------

# Strip the timestamp resolver so that Go-style 7-digit nanosecond timestamps
# (e.g. 2026-04-09T03:24:26.6974428+02:00) are preserved verbatim instead of
# being parsed to Python datetime / ruamel TimeStamp objects.
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"


def _make_yaml() -> YAML:
    """Return a ruamel.yaml YAML instance (round-trip) with timestamp resolver off."""
    y = YAML(typ="rt")
    # ruamel.yaml's VersionedResolver uses _version_implicit_resolver (keyed by YAML
    # version tuple) rather than the legacy yaml_implicit_resolvers dict.  Access the
    # versioned_resolver property to force the (1, 2) entry to be built, then strip the
    # timestamp tag in-place so timestamp-like strings are kept as plain Python str.
    _ = y.resolver.versioned_resolver  # forces (1, 2) entry to be populated
    for resolver_dict in y.resolver._version_implicit_resolver.values():  # noqa: SLF001
        for char_key in list(resolver_dict.keys()):
            resolver_dict[char_key] = [
                (tag, regexp) for tag, regexp in resolver_dict[char_key] if tag != _TIMESTAMP_TAG
            ]
    return y


def _to_plain(obj: Any) -> Any:  # noqa: ANN401
    """Recursively convert ruamel.yaml containers to plain Python types."""
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Windows reserved filename set (case-folded)
# ---------------------------------------------------------------------------

_WINDOWS_RESERVED: frozenset[str] = frozenset(
    ["con", "prn", "aux", "nul"] + [f"com{i}" for i in range(1, 10)] + [f"lpt{i}" for i in range(1, 10)]
)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def generate_slug(title: str) -> str:
    """Return a filesystem-safe slug derived from *title*.

    Rules:
    - Output charset: ``[a-z0-9-]`` only.
    - Maximum length: 80 characters.
    - Windows reserved filenames (exact slug match) raise :class:`ValueError`.
    """
    if not title:
        return ""

    # Lowercase, replace any non-alphanumeric run with a single hyphen.
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:80]

    # Reject Windows device names (exact slug match, case-folded already).
    if slug in _WINDOWS_RESERVED:
        msg = f"Invalid title: '{slug}' is a Windows reserved filename"
        raise ValueError(msg)

    return slug


def make_task_filename(task_id: int, title: str) -> str:
    """Return the canonical task filename ``{id}-{slug}.md``.

    Args:
        task_id: Numeric task identifier.
        title:   Task title passed to :func:`generate_slug`.

    Returns:
        Filename string, e.g. ``717-p3-05-red-task-file-io.md``.
    """
    slug = generate_slug(title)
    return f"{task_id}-{slug}.md"


def validate_path_containment(tasks_dir: Path, path: Path) -> None:
    """Raise if *path* is not safely contained within *tasks_dir*.

    Checks performed:
    - Null-byte injection.
    - Directory traversal (``..``).
    - Path is not ``tasks_dir`` itself.
    - Resolved path is strictly inside ``tasks_dir``.

    Args:
        tasks_dir: Canonical tasks directory.
        path:      Candidate file path to validate.

    Raises:
        ValueError:      Null byte, or path resolves outside *tasks_dir*.
        PermissionError: Path resolves to or escapes *tasks_dir*.
    """
    if "\x00" in str(path):
        msg = "Path contains null byte"
        raise ValueError(msg)

    resolved_dir = tasks_dir.resolve()
    resolved_path = path.resolve()

    if resolved_path == resolved_dir:
        msg = f"Path must be a file inside tasks_dir, not tasks_dir itself: {path}"
        raise ValueError(msg)

    # Use os.path.commonpath-based check via Path.is_relative_to (Python 3.9+)
    try:
        resolved_path.relative_to(resolved_dir)
    except ValueError:
        msg = f"Path is outside tasks_dir '{tasks_dir}': {path}"
        raise PermissionError(msg) from None


# ---------------------------------------------------------------------------
# Core I/O
# ---------------------------------------------------------------------------


def read_task(path: Path) -> Task:
    """Parse a task file into a :class:`Task`.

    The file must follow the ``---``-delimited YAML frontmatter format.
    The markdown body (everything after the closing ``---`` line) is stored
    in :attr:`Task.body`.

    Args:
        path: Path to the task ``.md`` file.

    Returns:
        Populated :class:`Task` including any unknown frontmatter fields.

    Raises:
        FileNotFoundError: *path* does not exist.
        ValueError:        File is missing YAML frontmatter delimiters.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")

    if not content.startswith("---"):
        msg = f"Task file has no YAML frontmatter (missing opening '---'): {path}"
        raise ValueError(msg)

    lines = content.split("\n")

    # Find the closing --- on its own line (first occurrence after line 0).
    closing_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break

    if closing_idx is None:
        msg = f"Task file has no closing '---' frontmatter delimiter: {path}"
        raise ValueError(msg)

    frontmatter_str = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])

    data: dict[str, Any] = _to_plain(_make_yaml().load(frontmatter_str) or {})
    data["body"] = body

    return Task.model_validate(data)


def write_task(path: Path, record: Task) -> None:
    """Serialise a :class:`Task` to a task file.

    Produces the canonical format::

        ---
        id: 42
        title: My task title
        ...
        ---
        <markdown body>

    Any extra fields stored on the record (e.g. ``class``, ``started``)
    are written into the frontmatter so they survive round-trips.

    Args:
        path:   Destination path (created or overwritten).
        record: Task record to serialise.
    """
    data = record.model_dump()
    body: str = data.pop("body", "") or ""

    _stream = io.StringIO()
    _make_yaml().dump(data, _stream)
    yaml_str = _stream.getvalue()

    content = f"---\n{yaml_str}---\n{body}"

    fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp_path).replace(path)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        raise
