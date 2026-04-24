"""Config loader for .owlbear/kanban/config.yml using ruamel.yaml round-trip mode.

Provides load_config and save_config for lossless round-trips: YAML comments,
field order, inline annotations, and unknown/vendor fields are all preserved.

Timestamp resolver is disabled so that date-like strings (e.g. "2026-04-09",
ISO 8601 datetimes, duration strings like "1h") are never auto-coerced to
Python datetime / timedelta objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

if TYPE_CHECKING:
    from pathlib import Path

from owlbear_kanban.models import BoardConfig
from owlbear_kanban.yaml_rt import make_yaml as _make_yaml

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

    config = BoardConfig.model_validate(_to_plain(raw))
    _validate_claim_timeout(config)
    return config


def _validate_claim_timeout(config: BoardConfig) -> None:
    """Validate claim_timeout by delegating to the canonical parser (AC-C50)."""
    from owlbear_kanban.engine import _parse_duration  # noqa: PLC0415

    _parse_duration(config.claim_timeout)


def save_config(kanban_dir: Path, config: BoardConfig) -> None:
    """Write *config* back to ``config.yml`` in *kanban_dir*.

    Uses a read-modify-write strategy so that YAML comments, field order, and
    per-item sequence annotations are preserved: the existing file is loaded as
    a :class:`~ruamel.yaml.comments.CommentedMap`, values are updated in-place
    from *config*, then the map is written back.

    If ``config.yml`` does not yet exist the file is created from scratch.
    """
    config_path = kanban_dir / "config.yml"
    y = _make_yaml()

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            raw: CommentedMap = y.load(fh)
    else:
        raw = CommentedMap()

    _merge_into(raw, config.model_dump())

    with config_path.open("w", encoding="utf-8") as fh:
        y.dump(raw, fh)


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


def _merge_into(target: CommentedMap, source: dict[str, Any]) -> None:
    """Update *target* :class:`~ruamel.yaml.comments.CommentedMap` in-place.

    Strategy:
    - Nested mappings: recurse so that inline comments on child keys survive.
    - Sequences (same length): update items in-place so per-item comments
      (stored on the :class:`~ruamel.yaml.comments.CommentedSeq` object) are
      preserved.  Length change → replace the whole sequence.
    - Scalars: assign directly; ruamel.yaml keeps the inline comment on the
      mapping key even when the value changes.
    - Missing keys: add them (new vendor fields from model_dump).
    """
    for key, new_value in source.items():
        if key not in target:
            target[key] = new_value
            continue

        existing = target[key]
        if isinstance(existing, CommentedMap) and isinstance(new_value, dict):
            _merge_into(existing, new_value)
        elif (
            isinstance(existing, CommentedSeq)
            and isinstance(new_value, list)
            and len(existing) == len(new_value)
        ):
            for i, item in enumerate(new_value):
                existing[i] = item
        else:
            target[key] = new_value
