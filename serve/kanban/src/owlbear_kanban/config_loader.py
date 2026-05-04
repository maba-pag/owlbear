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
from owlbear_kanban.yaml_rt import make_yaml as _make_yaml

_DEFAULT_PRIORITIES = [
    "someday",
    "nice-to-have",
    "important",
    "needed",
    "critical",
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(kanban_dir: Path) -> BoardConfig:
    """Load ``config.yml`` from *kanban_dir* and return a :class:`BoardConfig`.

    Raises:
        FileNotFoundError: when ``config.yml`` is absent from *kanban_dir*.
        ConfigError: when ``claim_timeout`` is present but cannot be parsed
            as a valid duration string (AC-C50).
    """
    config_path = kanban_dir / "config.yml"
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    y = _make_yaml()
    with config_path.open("r", encoding="utf-8") as fh:
        raw = y.load(fh)

    plain = _to_plain(raw)
    if isinstance(plain, dict) and plain.get("schema") == "grouped":
        if "priorities" not in plain:
            plain["priorities"] = list(_DEFAULT_PRIORITIES)

        statuses = plain.get("statuses")
        if isinstance(statuses, list) and statuses:
            pipeline = plain.get("pipeline")
            if not isinstance(pipeline, dict):
                pipeline = {}
            if "entry_status" not in pipeline:
                pipeline["entry_status"] = statuses[0]
            if "terminal_status" not in pipeline:
                pipeline["terminal_status"] = statuses[-1]
            plain["pipeline"] = pipeline

    config = BoardConfig.model_validate(plain)
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
