"""Pytest plugin for CI shards: keep this shard's tests, split by a hash of each node ID.

Load it with ``-p ci_shard`` and this folder on ``PYTHONPATH``. ``CI_SHARD_INDEX`` (1-based) and ``CI_SHARDS`` name
the shard; the same node ID always lands in the same shard, so together the shards run every collected test once.
"""

from __future__ import annotations

import os
import zlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def shard_of(nodeid: str, total: int) -> int:
    """Return the 1-based shard that runs ``nodeid``."""
    return zlib.crc32(nodeid.encode()) % total + 1


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect every test another shard runs."""
    index = int(os.environ["CI_SHARD_INDEX"])
    total = int(os.environ["CI_SHARDS"])
    keep = [item for item in items if shard_of(item.nodeid, total) == index]
    drop = [item for item in items if shard_of(item.nodeid, total) != index]
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
