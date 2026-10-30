"""Pytest plugin for CI shards: keep this shard's tests, by test file before import or by a hash of each node ID.

Load it with ``-p ci_shard`` and this folder on ``PYTHONPATH``. ``CI_SHARD_INDEX`` (1-based) and ``CI_SHARDS`` name
the shard. With ``CI_SHARD_DURATIONS`` naming a JSON file of test file path to seconds, whole test files are packed
into shards by those durations, and a shard never imports another shard's test files; a file the durations don't name
goes by a hash of its path. Without it, each node ID goes by its hash. Either way a test's shard depends only on its
own path or node ID, so together the shards run every collected test once, however stale the durations are.
"""

from __future__ import annotations

import fnmatch
import json
import os
import zlib
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def shard_of(nodeid: str, total: int) -> int:
    """Return the 1-based shard that runs ``nodeid``."""
    return zlib.crc32(nodeid.encode()) % total + 1


def pack(durations: dict[str, float], total: int) -> dict[str, int]:
    """Return each file's 1-based shard: longest first, each into the shard with the least time so far."""
    loads = [0.0] * total
    shards: dict[str, int] = {}
    for path, seconds in sorted(durations.items(), key=lambda item: (-item[1], item[0])):
        index = min(range(total), key=lambda i: (loads[i], i))
        loads[index] += seconds
        shards[path] = index + 1
    return shards


@cache
def _packed(durations_file: str, total: int) -> dict[str, int]:
    return pack(json.loads(Path(durations_file).read_text(encoding="utf-8")), total)


def _shard() -> tuple[int, int]:
    return int(os.environ["CI_SHARD_INDEX"]), int(os.environ["CI_SHARDS"])


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """Skip, before import, a test file another shard runs, when shards split by file."""
    durations_file = os.environ.get("CI_SHARD_DURATIONS")
    if not durations_file or not collection_path.is_file() or not collection_path.is_relative_to(config.rootpath):
        return None
    if not any(fnmatch.fnmatch(collection_path.name, pattern) for pattern in config.getini("python_files")):
        return None
    index, total = _shard()
    path = collection_path.relative_to(config.rootpath).as_posix()
    shard = _packed(durations_file, total).get(path) or shard_of(path, total)
    return True if shard != index else None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect every test another shard runs, when shards split by node ID."""
    if os.environ.get("CI_SHARD_DURATIONS"):
        return
    index, total = _shard()
    keep = [item for item in items if shard_of(item.nodeid, total) == index]
    drop = [item for item in items if shard_of(item.nodeid, total) != index]
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
