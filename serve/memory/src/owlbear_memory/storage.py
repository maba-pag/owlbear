"""File I/O primitives for markdown-backed memory entries."""

from __future__ import annotations

import os
from contextlib import suppress
from io import StringIO
from pathlib import Path
from tempfile import mkstemp
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_memory.errors import NotFoundError
from owlbear_memory.models import MemoryEntry

_FRONTMATTER_PARTS = 3
_MAX_FILE_SIZE_BYTES = 8192
_YAML = YAML(typ="safe")


def _assert_within_memory_dir(path: Path, memory_dir: Path) -> None:
    resolved_path = path.resolve()
    resolved_memory_dir = memory_dir.resolve()
    if not resolved_path.is_relative_to(resolved_memory_dir):
        msg = f"Path escapes memory_dir: {path}"
        raise ValueError(msg)


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        msg = f"Symlink paths are not allowed: {path}"
        raise ValueError(msg)


def read_entry(path: Path) -> MemoryEntry | None:
    """Read one memory entry file; return None for malformed or unsafe files."""
    if path.is_symlink() or not path.is_file():
        return None

    try:
        if path.stat().st_size > _MAX_FILE_SIZE_BYTES:
            return None

        raw = path.read_text(encoding="utf-8-sig")
        parts = raw.split("---", 2)
        if len(parts) >= _FRONTMATTER_PARTS:
            _, frontmatter_raw, body = parts
            data = _YAML.load(frontmatter_raw)
            if data is None:
                data = {}
            if isinstance(data, dict):
                data["content"] = body.strip()
                return MemoryEntry(**data)
    except (OSError, UnicodeDecodeError, YAMLError, PydanticValidationError):
        return None
    else:
        return None


def write_entry(path: Path, entry: MemoryEntry | dict[str, Any], *, memory_dir: Path) -> None:
    """Write one memory entry file atomically after strict validation and guards."""
    _assert_within_memory_dir(path, memory_dir)
    _reject_symlink(path)
    validated = MemoryEntry.model_validate(entry)

    frontmatter = {
        "id": validated.id,
        "title": validated.title,
        "categories": list(validated.categories),
        "confidence": validated.confidence,
        "state": str(validated.state),
        "outstanding_count": validated.outstanding_count,
        "unremarkable_count": validated.unremarkable_count,
        "didnt_use_count": validated.didnt_use_count,
        "score": validated.score,
        "scope_agents": validated.scope_agents,
        "source_agent": validated.source_agent,
        "created_at": validated.created_at,
        "updated_at": validated.updated_at,
        "approved_at": validated.approved_at,
        "contested_by_task": validated.contested_by_task,
    }

    yaml_stream = StringIO()
    _YAML.dump(frontmatter, yaml_stream)
    content = f"---\n{yaml_stream.getvalue()}---\n\n{validated.content}\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        tmp_path.replace(path)
    except Exception:
        with suppress(OSError):
            tmp_path.unlink()
        raise


def delete_entry(path: Path, *, memory_dir: Path) -> None:
    """Delete one memory entry file with containment and symlink protection."""
    _assert_within_memory_dir(path, memory_dir)
    _reject_symlink(path)
    try:
        path.unlink()
    except FileNotFoundError as exc:
        msg = f"Entry not found: {path}"
        raise NotFoundError(msg) from exc
