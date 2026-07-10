"""Canonical product topology constants for the kanban engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductTopology:
    """Immutable, canonical topology authority for kanban boards."""

    statuses: tuple[str, ...]
    priorities: tuple[str, ...]
    entry_status: str
    terminal_status: str
    default_priority: str
    claim_timeout: str
    wave_size: int
    agent_map: dict[str, str]
    non_impl_tags: frozenset[str]
    archival_reasons: frozenset[str]
    activity_log: bool
    tasks_dir: str
    archive_dir: str
    decisions_dir: str
    status_predicates: dict[str, Any]
    agent_types: dict[str, Any]
    agent_compatibility: dict[str, Any]


PRODUCT_TOPOLOGY = ProductTopology(
    statuses=(
        "shape",
        "build",
        "verify",
        "collect",
    ),
    priorities=(
        "low",
        "medium",
        "high",
    ),
    entry_status="shape",
    terminal_status="collect",
    default_priority="medium",
    claim_timeout="1h",
    wave_size=4,
    agent_map={
        "shape": "shaper",
        "build": "builder",
        "verify": "verifier",
        "collect": "collector",
    },
    non_impl_tags=frozenset(
        {
            "research",
            "docs",
            "type:config",
            "type:docs",
            "test",
            "type:test",
            "agent",
            "quality",
            "type:user-action",
        }
    ),
    archival_reasons=frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"}),
    activity_log=True,
    tasks_dir="tasks",
    archive_dir="archive",
    decisions_dir="decisions",
    status_predicates={},
    agent_types={},
    agent_compatibility={},
)
