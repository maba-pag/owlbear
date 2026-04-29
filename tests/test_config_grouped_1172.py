"""Tests for #1172 — P1-02: Implement config sub-models, detection cascade, and forwarding compat.

AC coverage:
  AC9:  migrate._migrate_config produces grouped output — CLEAN, no flat-key duplicates.
  AC10: Seed template (seed/.owlbear/kanban/config.yml) updated to grouped format.

These tests MUST FAIL until the builder:
  - Removes flat-key duplicates from _migrate_config output (currently writes both
    entry_status/default_priority/agent_map etc. at root AND inside pipeline/agents/policy).
  - Rewrites seed/.owlbear/kanban/config.yml to grouped format (currently legacy v10).

Context for 1171 overlap:
  AC1-AC8 and partial AC9 are covered by test_config_schema_1171.py and
  test_config_loader_1171.py.  This file covers the remaining AC9 (clean output)
  and the entirely untested AC10 (seed template).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from owlbear_kanban.migrate import _migrate_config
from owlbear_kanban.storage import load_config, save_config

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_SEED_CONFIG = _REPO_ROOT / "seed" / ".owlbear" / "kanban" / "config.yml"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_LEGACY_YAML = """\
version: 10
board:
  name: TestBoard
statuses:
  - name: research
  - name: backlog
  - name: done
priorities:
  - someday
  - important
  - critical
defaults:
  status: research
  priority: someday
claim_timeout: 1h
next_id: 1
tasks_dir: custom-tasks
archive_dir: custom-archive
"""

# The set of flat root-level keys that must NOT appear in a clean grouped output.
# These belong exclusively inside the nested pipeline: / agents: / policy: sections.
_FLAT_DUPLICATE_KEYS = {
    "entry_status",
    "terminal_status",
    "wave_size",
    "default_priority",
    "agent_map",
    "agent_types",
    "agent_compatibility",
    "non_impl_tags",
    "archival_reasons",
    "status_predicates",
}


def _make_board(tmp_path: Path, config_yaml: str) -> Path:
    """Create a minimal kanban board directory with *config_yaml*. Returns kanban_dir."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


def _read_yaml(path: Path) -> dict:
    """Parse a YAML file and return a plain dict."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ---------------------------------------------------------------------------
# AC10 — Seed template must be in grouped format
# ---------------------------------------------------------------------------


class TestFromAC_SeedTemplateGroupedFormat:
    """AC10 — seed/.owlbear/kanban/config.yml must use schema: grouped.

    ALL tests MUST FAIL until the builder rewrites the seed template.
    The file is currently in legacy v10 format (version: 10, flat keys, no nested sections).
    """

    def test_seed_config_has_schema_grouped_field(self) -> None:
        """Seed config must declare schema: grouped as the canonical format sentinel.

        MUST FAIL: current seed has no 'schema' key (version: 10 legacy format).
        """
        data = _read_yaml(_SEED_CONFIG)
        assert data.get("schema") == "grouped", (
            f"seed config.yml must have 'schema: grouped'; "
            f"got schema={data.get('schema')!r}, keys={list(data.keys())!r}"
        )

    def test_seed_config_has_nested_paths_section(self) -> None:
        """Seed config must contain a nested paths: dict with tasks_dir and archive_dir.

        MUST FAIL: current seed has flat tasks_dir/archive_dir at root, no paths: section.
        """
        data = _read_yaml(_SEED_CONFIG)
        assert isinstance(data.get("paths"), dict), (
            f"seed config.yml must have nested 'paths:' section; got paths={data.get('paths')!r}"
        )
        assert "tasks_dir" in data["paths"], "paths: section must contain tasks_dir"
        assert "archive_dir" in data["paths"], "paths: section must contain archive_dir"

    def test_seed_config_has_nested_pipeline_section(self) -> None:
        """Seed config must contain a nested pipeline: dict with all pipeline fields.

        MUST FAIL: current seed has no pipeline: section (entry_status is flat, wave_size flat).
        """
        data = _read_yaml(_SEED_CONFIG)
        assert isinstance(data.get("pipeline"), dict), (
            f"seed config.yml must have nested 'pipeline:' section; "
            f"got pipeline={data.get('pipeline')!r}"
        )
        pipeline = data["pipeline"]
        for field in ("entry_status", "terminal_status", "wave_size", "claim_timeout", "default_priority"):
            assert field in pipeline, (
                f"pipeline: section must contain '{field}'; got pipeline={pipeline!r}"
            )

    def test_seed_config_has_nested_agents_section(self) -> None:
        """Seed config must contain a nested agents: dict with agent_map/types/compatibility.

        MUST FAIL: current seed has flat agent_map/agent_types/agent_compatibility at root.
        """
        data = _read_yaml(_SEED_CONFIG)
        assert isinstance(data.get("agents"), dict), (
            f"seed config.yml must have nested 'agents:' section; "
            f"got agents={data.get('agents')!r}"
        )
        agents = data["agents"]
        for field in ("agent_map", "agent_types", "agent_compatibility"):
            assert field in agents, (
                f"agents: section must contain '{field}'; got agents={agents!r}"
            )

    def test_seed_config_has_nested_policy_section(self) -> None:
        """Seed config must contain a nested policy: dict with non_impl_tags/archival_reasons.

        MUST FAIL: current seed has flat non_impl_tags/archival_reasons/status_predicates at root.
        """
        data = _read_yaml(_SEED_CONFIG)
        assert isinstance(data.get("policy"), dict), (
            f"seed config.yml must have nested 'policy:' section; "
            f"got policy={data.get('policy')!r}"
        )
        policy = data["policy"]
        for field in ("non_impl_tags", "archival_reasons", "status_predicates"):
            assert field in policy, (
                f"policy: section must contain '{field}'; got policy={policy!r}"
            )

    def test_seed_config_no_flat_tasks_dir_at_root(self) -> None:
        """Grouped seed config must NOT have tasks_dir as a flat root-level key.

        MUST FAIL: current seed has 'tasks_dir: tasks' at root (legacy format).
        """
        data = _read_yaml(_SEED_CONFIG)
        assert "tasks_dir" not in data, (
            f"seed config.yml must not have flat 'tasks_dir' at root in grouped format; "
            f"keys={list(data.keys())!r}"
        )

    def test_seed_config_no_flat_entry_status_at_root(self) -> None:
        """Grouped seed config must NOT have entry_status as a flat root-level key.

        MUST FAIL: current seed has 'entry_status: research' at root (legacy format).
        """
        data = _read_yaml(_SEED_CONFIG)
        assert "entry_status" not in data, (
            f"seed config.yml must not have flat 'entry_status' at root in grouped format; "
            f"keys={list(data.keys())!r}"
        )

    def test_seed_config_no_legacy_version_key(self) -> None:
        """Grouped seed config must NOT have a version: key (legacy marker).

        MUST FAIL: current seed has 'version: 10' at root.
        """
        data = _read_yaml(_SEED_CONFIG)
        assert "version" not in data, (
            f"seed config.yml must not have legacy 'version:' key; got version={data.get('version')!r}"
        )

    def test_seed_config_loaded_has_no_legacy_version_in_extra(self, tmp_path: Path) -> None:
        """Grouped seed config when loaded must not expose 'version' key in model_extra.

        MUST FAIL: current seed has 'version: 10' at root, which BoardConfig stores in
        model_extra (extra='allow').  A proper grouped seed omits the version key entirely,
        so model_extra has no 'version' entry after loading.
        """
        board_dir = tmp_path / "seed-board"
        board_dir.mkdir()
        (board_dir / "config.yml").write_text(
            _SEED_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (board_dir / "tasks").mkdir()
        config = load_config(board_dir)
        extra = config.model_extra or {}
        assert "version" not in extra, (
            f"Seed config must not store legacy 'version' key in model_extra; "
            f"got model_extra['version']={extra.get('version')!r}. "
            f"A grouped seed has no 'version:' key in the YAML file."
        )


# ---------------------------------------------------------------------------
# AC9 — _migrate_config must produce CLEAN grouped output (no flat duplicates)
# ---------------------------------------------------------------------------


class TestFromAC_MigrateConfigCleanGroupedOutput:
    """AC9 — _migrate_config output must have ONLY grouped sections, no flat root duplicates.

    ALL tests MUST FAIL until the builder removes flat-key assignments from _migrate_config.
    Currently the function writes BOTH e.g. new_cfg["entry_status"] = ... AND
    new_cfg["pipeline"]["entry_status"] = ..., producing a flat+grouped mix.

    The comment in migrate.py reads 'Emit canonical grouped sections while keeping flat
    compatibility keys' — this 'keeping' must be removed for clean grouped output.
    """

    def test_migrate_output_no_flat_entry_status_at_root(self, tmp_path: Path) -> None:
        """_migrate_config output must NOT have flat entry_status at root level.

        MUST FAIL: current code writes new_cfg['entry_status'] = ... before building
        the pipeline: section — the flat key ends up in the YAML root.
        entry_status belongs exclusively inside pipeline: section.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = _read_yaml(kanban_dir / "config.yml")
        assert "entry_status" not in data, (
            f"migrate must NOT write flat 'entry_status' at root; found it with value={data['entry_status']!r}. "
            f"'entry_status' belongs only inside pipeline: section."
        )

    def test_migrate_output_no_flat_default_priority_at_root(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config output must NOT have flat default_priority at root level.

        MUST FAIL: current code writes new_cfg['default_priority'] as root key.
        default_priority belongs exclusively inside pipeline: section.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = _read_yaml(kanban_dir / "config.yml")
        assert "default_priority" not in data, (
            f"migrate must NOT write flat 'default_priority' at root; "
            f"found value={data.get('default_priority')!r}. "
            f"'default_priority' belongs only inside pipeline: section."
        )

    def test_migrate_output_no_flat_agent_map_at_root(self, tmp_path: Path) -> None:
        """_migrate_config output must NOT have flat agent_map at root level.

        MUST FAIL: current code writes new_cfg['agent_map'] = {...} as root key.
        agent_map belongs exclusively inside agents: section.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = _read_yaml(kanban_dir / "config.yml")
        assert "agent_map" not in data, (
            f"migrate must NOT write flat 'agent_map' at root; "
            f"found value={data.get('agent_map')!r}. "
            f"'agent_map' belongs only inside agents: section."
        )

    def test_migrate_output_no_flat_non_impl_tags_at_root(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config output must NOT have flat non_impl_tags at root level.

        MUST FAIL: current code writes new_cfg['non_impl_tags'] = [...] as root key.
        non_impl_tags belongs exclusively inside policy: section.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = _read_yaml(kanban_dir / "config.yml")
        assert "non_impl_tags" not in data, (
            f"migrate must NOT write flat 'non_impl_tags' at root; "
            f"found value={data.get('non_impl_tags')!r}. "
            f"'non_impl_tags' belongs only inside policy: section."
        )

    def test_migrate_output_no_flat_duplicates_comprehensive(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config output must have NONE of the flat-duplicate keys at root.

        MUST FAIL: checks all keys from _FLAT_DUPLICATE_KEYS simultaneously.
        A single grouped output cannot have any of these as top-level YAML keys.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = _read_yaml(kanban_dir / "config.yml")
        leaked = _FLAT_DUPLICATE_KEYS & set(data.keys())
        assert not leaked, (
            f"migrate output must not have flat-duplicate keys at root. "
            f"Leaked keys: {sorted(leaked)!r}. "
            f"These belong inside their respective nested sections."
        )


# ---------------------------------------------------------------------------
# AC9 (round-trip) — migrate → load → save must not re-introduce flat keys
# ---------------------------------------------------------------------------


class TestFromAC_MigrateLoadSaveNoFlatKeyLeak:
    """AC9 (round-trip) — flat keys from migrate output must not survive load → save.

    When _migrate_config writes flat keys alongside grouped sections, BoardConfig
    stores them as model_extra (extra='allow'). Then save_config writes model_extra
    back, re-leaking the flat keys into the saved file.

    ALL tests MUST FAIL until _migrate_config stops writing flat duplicates.
    If migrate is clean, there are no extra fields to leak — the round-trip is clean.
    """

    def test_migrate_load_save_no_flat_entry_status_leak(
        self, tmp_path: Path
    ) -> None:
        """entry_status must not re-appear as a flat root key after migrate → load → save.

        MUST FAIL: _migrate_config writes flat entry_status → load stores it in
        model_extra → save_config writes model_extra back → flat key re-introduced.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        _migrate_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert "entry_status" not in data, (
            f"entry_status must not be re-introduced as flat root key after "
            f"migrate → load → save; found value={data.get('entry_status')!r}"
        )

    def test_migrate_load_save_no_flat_agent_map_leak(self, tmp_path: Path) -> None:
        """agent_map must not re-appear as a flat root key after migrate → load → save.

        MUST FAIL: same model_extra → save_config leak path as entry_status.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        _migrate_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert "agent_map" not in data, (
            f"agent_map must not be re-introduced as flat root key after "
            f"migrate → load → save; found value={data.get('agent_map')!r}"
        )

    def test_migrate_load_save_no_flat_duplicates_comprehensive(
        self, tmp_path: Path
    ) -> None:
        """No flat-duplicate key must survive migrate → load → save round-trip.

        MUST FAIL: comprehensive check for all _FLAT_DUPLICATE_KEYS.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        _migrate_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        leaked = _FLAT_DUPLICATE_KEYS & set(data.keys())
        assert not leaked, (
            f"Flat-duplicate keys must not survive migrate → load → save. "
            f"Leaked: {sorted(leaked)!r}"
        )


# ---------------------------------------------------------------------------
# AC9 (REFINED) — idempotency on grouped config with activity_log
# ---------------------------------------------------------------------------

# A fully-grouped config with activity_log: false and non-default pipeline values.
# All NEW_CONFIG_KEYS are present; no legacy root-level keys except activity_log
# (which is erroneously listed in _LEGACY_CONFIG_KEYS, breaking idempotency).
_GROUPED_WITH_ACTIVITY_LOG_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
next_id: 1
activity_log: false
paths:
  tasks_dir: tasks
  archive_dir: archive
pipeline:
  entry_status: research
  terminal_status: archived
  wave_size: 8
  claim_timeout: 2h
  default_priority: critical
agents:
  agent_map:
    research: []
    backlog: []
    done: []
  agent_types: {}
  agent_compatibility: {}
policy:
  non_impl_tags:
    - research
    - docs
  archival_reasons:
    - completed
    - deprecated
    - dropped
    - duplicate
    - wontfix
  status_predicates: {}
"""


class TestFromAC_MigrateIdempotencyAndPreservation:
    """AC9 (REFINED) — _migrate_config must be idempotent on grouped configs with
    activity_log, and must not reset non-default nested pipeline values.

    Root cause: activity_log is listed in _LEGACY_CONFIG_KEYS, so
    _is_config_migrated returns False for any grouped config that includes
    activity_log (even though it is a live, non-legacy field).  This triggers
    a full re-migration which reads pipeline sub-values from flat root keys
    that do not exist in grouped format — resetting claim_timeout, terminal_status,
    default_priority, and wave_size to their hardcoded defaults.

    ALL tests MUST FAIL until the builder removes "activity_log" from
    _LEGACY_CONFIG_KEYS so that _is_config_migrated returns True for grouped
    configs that contain activity_log.
    """

    def test_grouped_with_activity_log_returns_already(self, tmp_path: Path) -> None:
        """_migrate_config on an already-grouped config with activity_log must return
        "already", not "migrated".

        MUST FAIL: _is_config_migrated returns False because activity_log ∈
        _LEGACY_CONFIG_KEYS, so the function falls through to a full re-migration
        and returns "migrated" instead of "already".
        """
        kanban_dir = _make_board(tmp_path, _GROUPED_WITH_ACTIVITY_LOG_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "already", (
            f"_migrate_config must return 'already' for a fully-grouped config "
            f"that contains activity_log; got {result!r}. "
            f"activity_log is a live runtime field, not a legacy sentinel — "
            f"it must be removed from _LEGACY_CONFIG_KEYS."
        )

    def test_grouped_with_activity_log_claim_timeout_preserved(
        self, tmp_path: Path
    ) -> None:
        """pipeline.claim_timeout must not be reset after _migrate_config on a grouped
        config with activity_log.

        MUST FAIL: re-migration reads claim_timeout via plain_raw.get("claim_timeout",
        "1h") which finds no flat root key in grouped format, so the value is reset
        from "2h" to the default "1h".
        """
        kanban_dir = _make_board(tmp_path, _GROUPED_WITH_ACTIVITY_LOG_YAML)
        _migrate_config(kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert data.get("pipeline", {}).get("claim_timeout") == "2h", (
            f"pipeline.claim_timeout must remain '2h' after _migrate_config; "
            f"got {data.get('pipeline', {}).get('claim_timeout')!r}. "
            f"Re-migration resets it to '1h' because the grouped pipeline.claim_timeout "
            f"key is not read from the nested section."
        )

    def test_grouped_with_activity_log_terminal_status_preserved(
        self, tmp_path: Path
    ) -> None:
        """pipeline.terminal_status must not be reset after _migrate_config on a grouped
        config with activity_log.

        MUST FAIL: re-migration reads terminal_status via plain_raw.get(
        "terminal_status", "done") which finds no flat root key in grouped format,
        so the value is reset from "archived" to the default "done".
        """
        kanban_dir = _make_board(tmp_path, _GROUPED_WITH_ACTIVITY_LOG_YAML)
        _migrate_config(kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert data.get("pipeline", {}).get("terminal_status") == "archived", (
            f"pipeline.terminal_status must remain 'archived' after _migrate_config; "
            f"got {data.get('pipeline', {}).get('terminal_status')!r}. "
            f"Re-migration resets it to 'done' because the grouped pipeline.terminal_status "
            f"key is not read from the nested section."
        )

    def test_grouped_with_activity_log_default_priority_preserved(
        self, tmp_path: Path
    ) -> None:
        """pipeline.default_priority must not be reset after _migrate_config on a
        grouped config with activity_log.

        MUST FAIL: re-migration reads default_priority from defaults.get("priority",
        "important") where defaults={} in grouped format, so the value is reset
        from "critical" to the default "important".
        """
        kanban_dir = _make_board(tmp_path, _GROUPED_WITH_ACTIVITY_LOG_YAML)
        _migrate_config(kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert data.get("pipeline", {}).get("default_priority") == "critical", (
            f"pipeline.default_priority must remain 'critical' after _migrate_config; "
            f"got {data.get('pipeline', {}).get('default_priority')!r}. "
            f"Re-migration resets it to 'important' because the grouped pipeline "
            f"section is not read during re-migration."
        )

    def test_grouped_with_activity_log_wave_size_preserved(
        self, tmp_path: Path
    ) -> None:
        """pipeline.wave_size must not be reset after _migrate_config on a grouped
        config with activity_log.

        MUST FAIL: re-migration hardcodes wave_size=4, so any non-default value
        in the grouped pipeline section is silently overwritten.
        """
        kanban_dir = _make_board(tmp_path, _GROUPED_WITH_ACTIVITY_LOG_YAML)
        _migrate_config(kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert data.get("pipeline", {}).get("wave_size") == 8, (
            f"pipeline.wave_size must remain 8 after _migrate_config; "
            f"got {data.get('pipeline', {}).get('wave_size')!r}. "
            f"Re-migration hardcodes wave_size=4 regardless of the grouped "
            f"pipeline.wave_size value."
        )
