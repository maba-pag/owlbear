"""kanban-migrate: migration script for owlbear-kanban boards (Brief C §5).

Migrates task files, archive files, and config.yml from the legacy schema
to the Brief-C canonical schema.

Usage:
    uv run kanban-migrate [--dry-run] [--lane tasks|archive|config|all]
                          [--kanban-dir PATH]
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from owlbear_kanban.storage_io import atomic_write

# ---------------------------------------------------------------------------
# Canonical frontmatter order (Brief C §2.3)
# ---------------------------------------------------------------------------

_CANONICAL_FIELDS = [
    "id", "title", "status", "priority", "created", "updated",
    "tags", "parent", "depends_on", "blocked", "block_reason",
    "claimed_at", "archival_reason", "archival_refs",
]

# New config required keys
_NEW_CONFIG_KEYS = frozenset({
    "statuses", "priorities", "entry_status", "wave_size",
    "agent_map", "agent_types", "agent_compatibility", "non_impl_tags",
    "archival_reasons", "status_predicates", "claim_timeout", "next_id",
})
_LEGACY_CONFIG_KEYS = frozenset({
    "board", "version", "tasks_dir", "archive_dir", "defaults", "activity_log",
})

_TS_FIELDS = frozenset({"created", "updated", "claimed_at"})


def _make_yaml_rt() -> YAML:
    """Return a round-trip YAML instance with timestamp resolution off."""
    y = YAML(typ="rt")
    _ts_tag = "tag:yaml.org,2002:timestamp"
    for char_key in list(y.resolver.yaml_implicit_resolvers.keys()):
        y.resolver.yaml_implicit_resolvers[char_key] = [
            (tag, regexp)
            for tag, regexp in y.resolver.yaml_implicit_resolvers[char_key]
            if tag != _ts_tag
        ]
    return y


def _make_yaml_safe() -> YAML:
    return YAML(typ="safe")


def _normalise_timestamp(ts: object) -> str | None:
    """Normalise an ISO-8601 timestamp to explicit UTC +00:00."""
    if ts is None:
        return None
    if not isinstance(ts, str):
        return str(ts)
    ts = ts.strip()
    import re  # noqa: PLC0415
    m = re.match(
        r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})((?:\.\d+)?)([+-]\d{2}:\d{2}|Z)?$",
        ts,
    )
    if not m:
        return ts
    base, frac, tz = m.groups()
    if tz:
        return ts  # already has tz
    return f"{base}{frac}+00:00"


def _is_task_migrated(fm: dict) -> bool:
    """Return True if the task frontmatter is already fully migrated."""
    if "claimed_by" in fm:
        return False
    ts_fields = ("created", "updated", "claimed_at")
    for field in ts_fields:
        val = fm.get(field)
        if isinstance(val, str) and val and not val.endswith("+00:00") and not val.endswith("Z"):
            return False
    if "archival_reason" not in fm:
        return False
    return "archival_refs" in fm


def _migrate_task_file(  # noqa: C901, PLR0911, PLR0912
    path: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Migrate one active task file.

    Returns:
        ('migrated', None), ('already', None), or ('failed', reason).
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "failed", str(exc)

    if not content.startswith("---"):
        return "failed", "missing --- delimiter"

    lines = content.split("\n")
    closing = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing = i
            break
    if closing is None:
        return "failed", "no closing ---"

    fm_text = "\n".join(lines[1:closing])
    body_text = "\n".join(lines[closing + 1:])

    try:
        y_safe = _make_yaml_safe()
        fm: dict = y_safe.load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    if _is_task_migrated(fm):
        return "already", None

    if dry_run:
        return "migrated", None

    # Apply transformations
    fm.pop("claimed_by", None)

    for field in _TS_FIELDS:
        val = fm.get(field)
        if val is not None:
            normalised = _normalise_timestamp(val)
            if normalised:
                fm[field] = normalised

    if "archival_reason" not in fm:
        fm["archival_reason"] = None
    if "archival_refs" not in fm:
        fm["archival_refs"] = []

    # Reorder frontmatter to canonical order
    ordered = CommentedMap()
    for key in _CANONICAL_FIELDS:
        if key in fm:
            ordered[key] = fm[key]
    for key, val in fm.items():
        if key not in ordered:
            ordered[key] = val

    y_rt = _make_yaml_rt()
    stream = io.StringIO()
    y_rt.dump(ordered, stream)
    yaml_str = stream.getvalue()
    new_content = f"---\n{yaml_str}---\n{body_text}"

    try:
        atomic_write(path, new_content)
    except OSError as exc:
        return "failed", str(exc)

    return "migrated", None


def _migrate_archive_file(  # noqa: C901, PLR0911
    path: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Migrate one archive file — metadata-only normalisation."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "failed", str(exc)

    if not content.startswith("---"):
        return "failed", "missing --- delimiter"

    lines = content.split("\n")
    closing = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing = i
            break
    if closing is None:
        return "failed", "no closing ---"

    fm_text = "\n".join(lines[1:closing])
    body_text = "\n".join(lines[closing + 1:])

    try:
        y_safe = _make_yaml_safe()
        fm: dict = y_safe.load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    has_ar = "archival_reason" in fm and fm.get("archival_reason") is not None
    has_refs = "archival_refs" in fm

    if has_ar and has_refs:
        return "already", None

    if dry_run:
        return "migrated", None

    if "archival_reason" not in fm:
        fm["archival_reason"] = "completed"
    if "archival_refs" not in fm:
        fm["archival_refs"] = []

    y_rt = _make_yaml_rt()
    cm = CommentedMap(fm)
    stream = io.StringIO()
    y_rt.dump(cm, stream)
    yaml_str = stream.getvalue()
    new_content = f"---\n{yaml_str}---\n{body_text}"

    try:
        atomic_write(path, new_content)
    except OSError as exc:
        return "failed", str(exc)

    return "migrated", None


def _is_config_migrated(raw: dict) -> bool:
    """Return True if config.yml is already in the new schema."""
    missing_new = _NEW_CONFIG_KEYS - set(raw.keys())
    has_legacy = bool(_LEGACY_CONFIG_KEYS & set(raw.keys()))
    # New schema: statuses must be list of strings
    statuses = raw.get("statuses")
    if isinstance(statuses, list) and statuses and isinstance(statuses[0], dict):
        return False
    return not missing_new and not has_legacy


def _migrate_config(  # noqa: C901, PLR0911
    kanban_dir: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Migrate config.yml to Brief-C schema."""
    config_path = kanban_dir / "config.yml"
    if not config_path.exists():
        return "failed", "config.yml not found"

    try:
        y_rt = _make_yaml_rt()
        with config_path.open("r", encoding="utf-8") as fh:
            raw: Any = y_rt.load(fh)
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    if not isinstance(raw, dict):
        return "failed", "config.yml is not a YAML mapping"

    plain_raw: dict = dict(raw)
    # Convert CommentedSeq to list
    for k, v in plain_raw.items():
        if hasattr(v, "items") or isinstance(v, list):
            import contextlib  # noqa: PLC0415
            with contextlib.suppress(Exception):
                plain_raw[k] = _to_plain(v)

    if _is_config_migrated(plain_raw):
        return "already", None

    if dry_run:
        return "migrated", None

    # Build new config
    new_cfg: dict[str, Any] = {}

    # Statuses: [{name: ...}] → [...]
    raw_statuses = plain_raw.get("statuses", [])
    if raw_statuses and isinstance(raw_statuses[0], dict):
        new_cfg["statuses"] = [s.get("name", str(s)) for s in raw_statuses if isinstance(s, dict)]
    elif isinstance(raw_statuses, list):
        new_cfg["statuses"] = [s for s in raw_statuses if isinstance(s, str)]
    else:
        new_cfg["statuses"] = []

    new_cfg["priorities"] = plain_raw.get("priorities", [])
    new_cfg["claim_timeout"] = plain_raw.get("claim_timeout", "1h")
    new_cfg["next_id"] = plain_raw.get("next_id", 1)

    # entry_status from defaults.status or first status
    defaults = plain_raw.get("defaults", {})
    new_cfg["entry_status"] = defaults.get("status", new_cfg["statuses"][0] if new_cfg["statuses"] else "research")
    new_cfg["wave_size"] = 4
    new_cfg["agent_map"] = {}
    new_cfg["agent_types"] = {}
    new_cfg["agent_compatibility"] = {}
    new_cfg["non_impl_tags"] = [
        "research", "docs", "type:config", "type:docs", "test",
        "type:test", "agent", "quality", "type:user-action",
    ]
    new_cfg["archival_reasons"] = ["completed", "deprecated", "dropped", "duplicate", "wontfix"]
    new_cfg["status_predicates"] = {}

    y_rt2 = _make_yaml_rt()
    cm = CommentedMap(new_cfg)
    stream = io.StringIO()
    y_rt2.dump(cm, stream)
    yaml_str = stream.getvalue()

    try:
        atomic_write(config_path, yaml_str)
    except OSError as exc:
        return "failed", str(exc)

    # Warn about stub fields
    sys.stderr.write(
        "WARNING: config.yml migrated. agent_map, agent_types, and agent_compatibility\n"
        "are empty stubs — populate them before starting the engine.\n"
    )

    return "migrated", None


def _to_plain(obj: Any) -> Any:  # noqa: ANN401
    """Recursively convert ruamel.yaml containers to plain Python types."""
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    return obj


def _run_lane(
    kanban_dir: Path,
    lane: str,
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Run the requested migration lane(s). Returns summary counts."""
    counts = {"scanned": 0, "migrated": 0, "already": 0, "failed": 0}

    def _process_files(files: list[Path], migrate_fn: Any) -> None:  # noqa: ANN401
        for path in files:
            counts["scanned"] += 1
            result, reason = migrate_fn(path, dry_run=dry_run)
            counts[result] += 1  # type: ignore[literal-required]
            if result == "failed":
                sys.stderr.write(f"FAIL {path}: {reason}\n")

    if lane in ("tasks", "all"):
        tasks_dir = kanban_dir / "tasks"
        if tasks_dir.exists():
            files = sorted(p for p in tasks_dir.glob("*.md") if not p.name.startswith(".tmp-"))
            _process_files(files, _migrate_task_file)

    if lane in ("archive", "all"):
        archive_dir = kanban_dir / "archive"
        if archive_dir.exists():
            files = sorted(p for p in archive_dir.glob("*.md") if not p.name.startswith(".tmp-"))
            _process_files(files, _migrate_archive_file)

    if lane in ("config", "all"):
        counts["scanned"] += 1
        result, reason = _migrate_config(kanban_dir, dry_run=dry_run)
        counts[result] += 1  # type: ignore[literal-required]
        if result == "failed":
            sys.stderr.write(f"FAIL {kanban_dir / 'config.yml'}: {reason}\n")

    return counts


def main() -> None:
    """Entry point for ``uv run kanban-migrate``."""
    parser = argparse.ArgumentParser(
        description="Migrate owlbear-kanban board to Brief-C canonical schema.",
    )
    parser.add_argument(
        "--kanban-dir",
        type=Path,
        default=None,
        help="Path to the kanban directory. Defaults to .owlbear/kanban/ in CWD.",
    )
    parser.add_argument(
        "--lane",
        choices=["tasks", "archive", "config", "all"],
        default="all",
        help="Which migration lane to run (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be migrated without writing any files.",
    )
    args = parser.parse_args()

    kanban_dir = args.kanban_dir
    if kanban_dir is None:
        # Walk CWD upwards to find .owlbear/kanban/
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            candidate = parent / ".owlbear" / "kanban"
            if candidate.is_dir():
                kanban_dir = candidate
                break
        if kanban_dir is None:
            kanban_dir = cwd / ".owlbear" / "kanban"

    if not kanban_dir.is_dir():
        sys.stderr.write(f"Error: kanban directory not found: {kanban_dir}\n")
        sys.exit(1)

    counts = _run_lane(kanban_dir, args.lane, dry_run=args.dry_run)

    # Summary output
    print(  # noqa: T201
        f"Scanned: {counts['scanned']}\n"
        f"Migrated: {counts['migrated']}\n"
        f"Already: {counts['already']}\n"
        f"Failed: {counts['failed']}"
    )

    sys.exit(0 if counts["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
