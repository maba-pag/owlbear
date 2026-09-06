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


def _pydantic_error_detail(error: PydanticValidationError) -> str:
    fields: list[str] = []
    for item in error.errors(include_url=False, include_context=False, include_input=False):
        location = ".".join(str(part) for part in item.get("loc", ())) or "entry"
        fields.append(f"{location} ({item.get('type', 'invalid')})")
    return "schema validation failed: " + ", ".join(fields)


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
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return read_entry_strict(path)
    except (OSError, ValueError):
        return None


def _parse_frontmatter(frontmatter_raw: str) -> dict[str, Any]:
    data = _YAML.load(frontmatter_raw)
    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = "YAML frontmatter must be an object"
        raise TypeError(msg)
    return data


def _read_entry_file(path: Path) -> MemoryEntry:
    return _read_entry_bytes(path.read_bytes())


def _read_entry_bytes(raw: bytes) -> MemoryEntry:
    if len(raw) > _MAX_FILE_SIZE_BYTES:
        msg = f"file exceeds {_MAX_FILE_SIZE_BYTES} bytes"
        raise ValueError(msg)

    text = raw.decode("utf-8-sig")
    parts = text.split("---", 2)
    if len(parts) < _FRONTMATTER_PARTS:
        msg = "YAML frontmatter is missing"
        raise ValueError(msg)

    _, frontmatter_raw, body = parts
    data = _parse_frontmatter(frontmatter_raw)
    data["content"] = body.strip()
    return MemoryEntry(**data)


def read_entry_strict(path: Path) -> MemoryEntry:
    """Read one memory entry file or raise a safe validation diagnostic."""
    if path.is_symlink():
        msg = "symlink paths are not allowed"
        raise ValueError(msg)
    if not path.is_file():
        msg = "memory entry file is missing"
        raise ValueError(msg)

    try:
        return _read_entry_file(path)
    except OSError as exc:
        msg = f"file read failed ({type(exc).__name__})"
        raise ValueError(msg) from exc
    except UnicodeDecodeError as exc:
        msg = "file is not valid UTF-8"
        raise ValueError(msg) from exc
    except YAMLError as exc:
        msg = "YAML frontmatter is invalid"
        raise ValueError(msg) from exc
    except TypeError as exc:
        raise ValueError(str(exc)) from exc
    except PydanticValidationError as exc:
        raise ValueError(_pydantic_error_detail(exc)) from exc


def read_entry_bytes_strict(raw: bytes) -> MemoryEntry:
    """Parse one memory entry snapshot using the canonical storage rules."""
    try:
        return _read_entry_bytes(raw)
    except UnicodeDecodeError as exc:
        msg = "file is not valid UTF-8"
        raise ValueError(msg) from exc
    except YAMLError as exc:
        msg = "YAML frontmatter is invalid"
        raise ValueError(msg) from exc
    except TypeError as exc:
        raise ValueError(str(exc)) from exc
    except PydanticValidationError as exc:
        raise ValueError(_pydantic_error_detail(exc)) from exc


def _serialize_entry(entry: MemoryEntry) -> bytes:
    frontmatter = {
        "id": entry.id,
        "title": entry.title,
        "categories": list(entry.categories),
        "confidence": entry.confidence,
        "state": str(entry.state),
        "outstanding_count": entry.outstanding_count,
        "unremarkable_count": entry.unremarkable_count,
        "didnt_use_count": entry.didnt_use_count,
        "score": entry.score,
        "scope_agents": entry.scope_agents,
        "source_agent": entry.source_agent,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "approved_at": entry.approved_at,
        "contested_by_task": entry.contested_by_task,
    }

    yaml_stream = StringIO()
    _YAML.dump(frontmatter, yaml_stream)
    content = f"---\n{yaml_stream.getvalue()}---\n\n{entry.content}\n"
    return content.encode("utf-8")


def write_entry(path: Path, entry: MemoryEntry | dict[str, Any], *, memory_dir: Path) -> None:
    """Write one memory entry file atomically after strict validation and guards."""
    _assert_within_memory_dir(path, memory_dir)
    _reject_symlink(path)
    validated = MemoryEntry.model_validate(entry)
    serialized = _serialize_entry(validated)
    serialized_size = len(serialized)
    if serialized_size > _MAX_FILE_SIZE_BYTES:
        msg = (
            f"serialized entry exceeds {_MAX_FILE_SIZE_BYTES} bytes "
            f"(got {serialized_size}); shorten the title, content, or metadata"
        )
        raise ValueError(msg)
    read_entry_bytes_strict(serialized)

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(serialized)
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
