"""kanban-migrate: migration script for owlbear-kanban boards.

Migrates task files, archive files, and config.yml from the legacy schema
to the grouped canonical schema (schema: grouped).

Usage:
    uv run kanban-migrate [--dry-run] [--lane tasks|archive|config|all]
                          [--kanban-dir PATH]
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from owlbear_kanban.body_parser import parse_body
from owlbear_kanban.storage_io import atomic_write

# ---------------------------------------------------------------------------
# Canonical frontmatter order (Brief C §2.3)
# ---------------------------------------------------------------------------

_CANONICAL_FIELDS = [
    "id",
    "title",
    "status",
    "priority",
    "created",
    "updated",
    "tags",
    "parent",
    "depends_on",
    "blocked",
    "block_reason",
    "claimed_at",
    "archival_reason",
    "archival_refs",
]

# New config required keys
_NEW_CONFIG_KEYS = frozenset(
    {
        "statuses",
        "priorities",
        "next_id",
        "schema",
        "paths",
        "pipeline",
        "agents",
        "policy",
    }
)
_LEGACY_CONFIG_KEYS = frozenset(
    {
        "board",
        "version",
        "tasks_dir",
        "archive_dir",
        "defaults",
    }
)

_TS_FIELDS = frozenset({"created", "updated", "claimed_at"})
_REQUIRED_TASK_TS_FIELDS = frozenset({"created", "updated"})
_CONFIG_STUB_FIELDS = ("agent_map", "agent_types", "agent_compatibility")
_ACTIVE_TASK_DEFAULTS: dict[str, Any] = {
    "tags": [],
    "parent": None,
    "depends_on": [],
    "blocked": False,
    "block_reason": None,
    "claimed_at": None,
    "archival_reason": None,
    "archival_refs": [],
}
_PROOF_BUNDLE_LINE_RE = re.compile(r"^Proof bundle:\s*(.*)$")


def _make_yaml_rt() -> YAML:
    """Return a round-trip YAML instance with timestamp resolution off."""
    y = YAML(typ="rt")
    _ts_tag = "tag:yaml.org,2002:timestamp"
    for char_key in list(y.resolver.yaml_implicit_resolvers.keys()):
        y.resolver.yaml_implicit_resolvers[char_key] = [
            (tag, regexp) for tag, regexp in y.resolver.yaml_implicit_resolvers[char_key] if tag != _ts_tag
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
    text = ts.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return ts
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _has_canonical_order(fm: dict[str, Any]) -> bool:
    """Return True when canonical keys appear in canonical relative order."""
    keys = list(fm.keys())
    seen = [key for key in keys if key in _CANONICAL_FIELDS]
    return seen == [key for key in _CANONICAL_FIELDS if key in fm]


def _is_timestamp_utc_plus_00(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value.endswith("+00:00")


def _is_archive_reason_valid(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_archive_refs_valid(value: object) -> bool:
    return isinstance(value, list) and all(
        (isinstance(item, str) or (isinstance(item, int) and not isinstance(item, bool))) for item in value
    )


def _is_task_migrated(fm: dict[str, Any]) -> bool:
    """Return True if the task frontmatter is already fully migrated."""
    if "claimed_by" in fm:
        return False
    for field in _REQUIRED_TASK_TS_FIELDS:
        if field not in fm:
            return False
    for field in _TS_FIELDS:
        if not _is_timestamp_utc_plus_00(fm.get(field)):
            return False
    for field in _ACTIVE_TASK_DEFAULTS:
        if field not in fm:
            return False
    return _has_canonical_order(fm)


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
    body_text = "\n".join(lines[closing + 1 :])

    try:
        y_safe = _make_yaml_safe()
        fm: dict = y_safe.load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    if _is_task_migrated(fm):
        return "already", None

    # Apply transformations
    fm.pop("claimed_by", None)

    for field in _TS_FIELDS:
        val = fm.get(field)
        if val is not None:
            normalised = _normalise_timestamp(val)
            if normalised:
                fm[field] = normalised

    for key, default in _ACTIVE_TASK_DEFAULTS.items():
        if key not in fm:
            fm[key] = default

    try:
        parse_body(body_text)
    except Exception as exc:  # noqa: BLE001
        return "failed", f"body parse error: {exc}"

    if dry_run:
        return "migrated", None

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


def _migrate_proof_bundle_field(  # noqa: C901, PLR0911, PLR0912
    path: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Extract first body ``Proof bundle:`` line into frontmatter ``proof_bundle``."""
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
    body_lines = lines[closing + 1 :]

    try:
        y_safe = _make_yaml_safe()
        fm: dict = y_safe.load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    if fm.get("proof_bundle") is not None:
        return "already", None

    match_index = None
    extracted_value: str | None = None
    for index, line in enumerate(body_lines):
        match = _PROOF_BUNDLE_LINE_RE.match(line)
        if match is None:
            continue
        value = match.group(1).strip()
        if not value:
            return "already", None
        match_index = index
        extracted_value = value
        break

    if match_index is None or extracted_value is None:
        return "already", None

    fm["proof_bundle"] = extracted_value
    body_lines.pop(match_index)

    if dry_run:
        return "migrated", None

    y_rt = _make_yaml_rt()
    stream = io.StringIO()
    y_rt.dump(CommentedMap(fm), stream)
    yaml_str = stream.getvalue()
    body_text = "\n".join(body_lines)
    new_content = f"---\n{yaml_str}---\n{body_text}"

    try:
        atomic_write(path, new_content)
    except OSError as exc:
        return "failed", str(exc)

    return "migrated", None


def _migrate_archive_file(  # noqa: C901, PLR0911, PLR0912
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
    body_text = "\n".join(lines[closing + 1 :])

    try:
        y_safe = _make_yaml_safe()
        fm: dict = y_safe.load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001
        return "failed", f"YAML parse error: {exc}"

    reason = fm.get("archival_reason")
    refs = fm.get("archival_refs")
    has_reason = "archival_reason" in fm
    has_refs = "archival_refs" in fm
    reason_valid = _is_archive_reason_valid(reason)
    refs_valid = _is_archive_refs_valid(refs)

    if has_reason and reason_valid and has_refs and refs_valid:
        return "already", None

    if has_reason and not reason_valid:
        return "failed", "manual-action required: invalid archival_reason"
    if has_refs and not refs_valid:
        return "failed", "manual-action required: invalid archival_refs"

    if dry_run:
        return "migrated", None

    if not has_reason:
        fm["archival_reason"] = "completed"
    if not has_refs:
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
    # New schema: statuses must be list[str] (including empty list).
    statuses = raw.get("statuses")
    if not isinstance(statuses, list):
        return False
    if not all(isinstance(item, str) for item in statuses):
        return False
    return not missing_new and not has_legacy


def _has_unresolved_config_stubs(raw: dict[str, Any]) -> bool:
    """Return True when config still has unresolved stub mapping fields."""
    for field in _CONFIG_STUB_FIELDS:
        value = raw.get(field)
        if not isinstance(value, dict) or not value:
            return True
    return False


def _config_requires_manual_action(kanban_dir: Path) -> bool:
    """Check whether config lane still leaves manual follow-up work."""
    config_path = kanban_dir / "config.yml"
    try:
        y_safe = _make_yaml_safe()
        with config_path.open("r", encoding="utf-8") as fh:
            loaded: Any = y_safe.load(fh)
    except Exception:  # noqa: BLE001
        return False

    if not isinstance(loaded, dict):
        return False

    plain_loaded = _to_plain(loaded)
    if not isinstance(plain_loaded, dict):
        return False

    return _has_unresolved_config_stubs(plain_loaded)


def _migrate_config(  # noqa: C901, PLR0911, PLR0915
    kanban_dir: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Migrate config.yml to grouped schema (schema: grouped); idempotent on already-migrated configs."""
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
    new_cfg["next_id"] = plain_raw.get("next_id", 1)
    new_cfg["activity_log"] = plain_raw.get("activity_log", True)
    new_cfg["schema"] = "grouped"

    # entry_status from defaults.status or first status
    defaults = plain_raw.get("defaults", {})
    entry_status = defaults.get("status", new_cfg["statuses"][0] if new_cfg["statuses"] else "research")
    default_priority = defaults.get("priority", "important")
    wave_size = 4
    claim_timeout = plain_raw.get("claim_timeout", "1h")
    agent_map = {status: [] for status in new_cfg["statuses"]}
    agent_types: dict[str, Any] = {}
    agent_compatibility: dict[str, Any] = {}
    non_impl_tags = [
        "research",
        "docs",
        "type:config",
        "type:docs",
        "test",
        "type:test",
        "agent",
        "quality",
        "type:user-action",
    ]
    archival_reasons = [
        "completed",
        "deprecated",
        "dropped",
        "duplicate",
        "wontfix",
    ]
    status_predicates: dict[str, Any] = {}

    # Emit canonical grouped sections only.
    tasks_dir = plain_raw.get("tasks_dir", "tasks")
    archive_dir = plain_raw.get("archive_dir", "archive")
    new_cfg["paths"] = {
        "tasks_dir": tasks_dir,
        "archive_dir": archive_dir,
    }
    new_cfg["pipeline"] = {
        "entry_status": entry_status,
        "terminal_status": plain_raw.get("terminal_status", "done"),
        "wave_size": wave_size,
        "claim_timeout": claim_timeout,
        "default_priority": default_priority,
    }
    new_cfg["agents"] = {
        "agent_map": agent_map,
        "agent_types": agent_types,
        "agent_compatibility": agent_compatibility,
    }
    new_cfg["policy"] = {
        "non_impl_tags": non_impl_tags,
        "archival_reasons": archival_reasons,
        "status_predicates": status_predicates,
    }

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
        "See serve/kanban/README.md for the standard pipeline configuration.\n"
    )

    return "migrated", None


def _to_plain(obj: Any) -> Any:  # noqa: ANN401
    """Recursively convert ruamel.yaml containers to plain Python types."""
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    return obj


def _run_lane(  # noqa: C901
    kanban_dir: Path,
    lane: str,
    *,
    dry_run: bool,
) -> tuple[dict[str, int], list[str]]:
    """Run the requested migration lane(s). Returns summary counts."""
    counts = {"scanned": 0, "migrated": 0, "already": 0, "failed": 0}
    manual_actions: list[str] = []
    crash_after_env = os.environ.get("KANBAN_MIGRATE_CRASH_AFTER")
    crash_after = int(crash_after_env) if crash_after_env and crash_after_env.isdigit() else None
    successful_writes = 0

    def _process_files(files: list[Path], migrate_fn: Any) -> None:  # noqa: ANN401
        nonlocal successful_writes
        for path in files:
            counts["scanned"] += 1
            result, reason = migrate_fn(path, dry_run=dry_run)
            counts[result] += 1  # type: ignore[literal-required]
            if result == "failed":
                sys.stderr.write(f"FAIL {path}: {reason}\n")
                if reason and "manual-action required" in reason:
                    manual_actions.append(f"archive: {path} - {reason}")
            if result == "migrated" and not dry_run:
                successful_writes += 1
                if crash_after is not None and successful_writes >= crash_after:
                    msg = "simulated crash via KANBAN_MIGRATE_CRASH_AFTER"
                    raise OSError(msg)

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
        if result in {"migrated", "already"} and not dry_run and _config_requires_manual_action(kanban_dir):
            manual_actions.append(
                "config: populate agent_map, agent_types, and "
                "agent_compatibility, then create type:user-action task(s) "
                "before final --lane tasks cutover"
            )

    return counts, manual_actions


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

    try:
        counts, manual_actions = _run_lane(kanban_dir, args.lane, dry_run=args.dry_run)
    except OSError as exc:
        sys.stderr.write(f"FAIL migration run: {exc}\n")
        sys.exit(1)

    # Summary output
    print(  # noqa: T201
        f"Scanned: {counts['scanned']}\n"
        f"Migrated: {counts['migrated']}\n"
        f"Already: {counts['already']}\n"
        f"Failed: {counts['failed']}"
    )

    if manual_actions:
        sys.stderr.write(
            "MANUAL ACTION SUMMARY: unresolved follow-up remains. "
            "Materialise as type:user-action task(s) before final "
            "--lane tasks cutover.\n"
        )
        for item in manual_actions:
            sys.stderr.write(f" - {item}\n")

    sys.exit(0 if counts["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
