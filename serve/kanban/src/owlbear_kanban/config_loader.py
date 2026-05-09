"""Config loader for .owlbear/kanban/config.yml using ruamel.yaml round-trip mode.

Provides load_config for parsing and validating board configuration.

Timestamp resolver is disabled so that date-like strings (e.g. "2026-04-09",
ISO 8601 datetimes, duration strings like "1h") are never auto-coerced to
Python datetime / timedelta objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from owlbear_kanban._duration import _parse_duration
from owlbear_kanban.models import BoardConfig
from owlbear_kanban.topology import PRODUCT_TOPOLOGY
from owlbear_kanban.yaml_rt import make_yaml as _make_yaml

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(kanban_dir: Path) -> BoardConfig:
    """Load ``config.yml`` from *kanban_dir* and return a :class:`BoardConfig`.

    The board topology is product-owned and not loaded from disk. ``config.yml``
    is used only as a ``next_id`` checkpoint when present.

    Raises:
        ConfigError: when ``claim_timeout`` is present but cannot be parsed
            as a valid duration string (AC-C50).
    """
    next_id = 1
    config_path = kanban_dir / "config.yml"
    if config_path.exists():
        y = _make_yaml()
        with config_path.open("r", encoding="utf-8") as fh:
            raw = y.load(fh)
        plain = _to_plain(raw)
        if isinstance(plain, dict):
            raw_next_id = plain.get("next_id")
            if isinstance(raw_next_id, int):
                next_id = raw_next_id

    config = BoardConfig.model_validate(
        {
            "schema": "grouped",
            "statuses": list(PRODUCT_TOPOLOGY.statuses),
            "priorities": list(PRODUCT_TOPOLOGY.priorities),
            "next_id": next_id,
            "activity_log": PRODUCT_TOPOLOGY.activity_log,
            "paths": {
                "tasks_dir": PRODUCT_TOPOLOGY.tasks_dir,
                "archive_dir": PRODUCT_TOPOLOGY.archive_dir,
            },
            "pipeline": {
                "entry_status": PRODUCT_TOPOLOGY.entry_status,
                "terminal_status": PRODUCT_TOPOLOGY.terminal_status,
                "statuses": list(PRODUCT_TOPOLOGY.statuses),
                "priorities": list(PRODUCT_TOPOLOGY.priorities),
                "wave_size": PRODUCT_TOPOLOGY.wave_size,
                "claim_timeout": PRODUCT_TOPOLOGY.claim_timeout,
                "default_priority": PRODUCT_TOPOLOGY.default_priority,
            },
            "agents": {
                "agent_map": dict(PRODUCT_TOPOLOGY.agent_map),
                "agent_types": dict(PRODUCT_TOPOLOGY.agent_types),
                "agent_compatibility": dict(PRODUCT_TOPOLOGY.agent_compatibility),
            },
            "policy": {
                "non_impl_tags": sorted(PRODUCT_TOPOLOGY.non_impl_tags),
                "archival_reasons": sorted(PRODUCT_TOPOLOGY.archival_reasons),
                "status_predicates": dict(PRODUCT_TOPOLOGY.status_predicates),
            },
        }
    )
    _validate_claim_timeout(config)
    return config


def _validate_claim_timeout(config: BoardConfig) -> None:
    """Validate claim_timeout by delegating to the canonical parser (AC-C50)."""
    _parse_duration(config.pipeline.claim_timeout)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_plain(obj: Any) -> Any:  # noqa: ANN401
    """Recursively convert ruamel.yaml containers to plain Python types.

    :class:`~ruamel.yaml.comments.CommentedMap` → ``dict``,
    :class:`~ruamel.yaml.comments.CommentedSeq` → ``list``.
    Scalar values are returned unchanged.
    """
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(item) for item in obj]
    return obj
