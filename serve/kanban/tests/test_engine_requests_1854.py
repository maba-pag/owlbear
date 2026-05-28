"""Tests for #1854: Engine API — list_requests and sweep.

AC coverage:
  AC1 → TestFromAC_ListRequests:
        test_list_pending_returns_records
        test_list_resolved_returns_records
        test_list_all_returns_both_dirs
        test_list_empty_returns_empty_list
        test_list_pending_task_id_filter
        test_list_pending_task_id_no_match_returns_empty
        test_list_excludes_legacy_filenames
        test_list_skips_corrupt_yaml_no_raise
        test_list_ordered_by_created_at_ascending
  AC2 → TestFromAC_SweepRequests:
        test_sweep_returns_empty_when_nothing_resolvable
        test_sweep_resolves_decision_with_selected_option_id
        test_sweep_resolves_action_with_free_text
        test_sweep_moves_to_resolved_dir
        test_sweep_deletes_from_pending_dir
        test_sweep_resolved_at_is_tz_aware_iso8601
        test_sweep_appends_writeback_to_task
        test_sweep_unblocks_task_when_no_sibling_pending
        test_sweep_keeps_task_blocked_with_sibling_pending
        test_sweep_returns_multiple_request_ids
        test_sweep_processes_in_sorted_filename_order
  AC3 → TestFromAC_SweepErrorHandling:
        test_sweep_skips_corrupt_yaml_no_raise
        test_sweep_skips_pydantic_validation_failure_no_raise
        test_sweep_includes_request_id_when_writeback_raises
        test_sweep_continues_after_writeback_error
        test_sweep_includes_request_id_when_unblock_raises
        test_sweep_move_preserved_when_unblock_raises_resolved_exists
        test_sweep_move_preserved_when_unblock_raises_pending_absent
        test_sweep_unblock_failure_logs_warning
        test_sweep_continues_after_unblock_error
  AC4 → TestFromAC_PickTasksSweepWiring:
        test_pick_tasks_calls_sweep_requests
        test_pick_tasks_continues_when_sweep_raises
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from owlbear_kanban import KanbanEngine
from owlbear_kanban.request_models import RequestRecord

# ---------------------------------------------------------------------------
# Board / task scaffolding (shared with 1853 pattern)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_TASK_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: todo
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

Body text.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir: Path, task_id: int) -> Path:
    content = _TASK_TMPL.format(task_id=task_id)
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path, *task_ids: int) -> tuple[KanbanEngine, Path]:
    """Create a board with one or more tasks and return (engine, kanban_dir)."""
    kanban_dir = _make_board(base_dir)
    for tid in task_ids:
        _write_task(kanban_dir, tid)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return engine, kanban_dir


def _write_request_file(  # noqa: PLR0913
    kanban_dir: Path,
    *,
    subdir: str = "pending",
    request_id: str | None = None,
    task_id: int = 42,
    kind: str = "decision",
    created_at: str = "2026-05-24T12:00:00+02:00",
    selected_option_id: str | None = None,
    free_text: str | None = None,
    resolved_at: str | None = None,
    body: str = "",
) -> tuple[Path, str]:
    """Write a structured request file to decisions/{subdir}/."""
    rid = request_id or str(uuid.uuid4())
    decisions_dir = kanban_dir / "decisions" / subdir
    decisions_dir.mkdir(parents=True, exist_ok=True)

    if kind == "decision":
        options_yaml = (
            "options:\n"
            "  - option_id: option-a\n"
            "    label: Option Alpha\n"
            "    confidence: 0.8\n"
            "    recommended: true\n"
            "    rationale: First option rationale.\n"
            "  - option_id: option-b\n"
            "    label: Option Beta\n"
            "    confidence: 0.5\n"
            "    recommended: false\n"
            "    rationale: Second option rationale.\n"
        )
    else:
        options_yaml = "options: []\n"

    def _yaml_null_or_str(value: str | None) -> str:
        return f"'{value}'" if value is not None else "null"

    resolution_block = (
        "resolution:\n"
        f"  selected_option_id: {_yaml_null_or_str(selected_option_id)}\n"
        f"  free_text: {_yaml_null_or_str(free_text)}\n"
        f"  resolved_at: {_yaml_null_or_str(resolved_at)}\n"
    )

    content = (
        "---\n"
        f"request_id: '{rid}'\n"
        f"task_id: {task_id}\n"
        f"kind: {kind}\n"
        "title: Test Request\n"
        "summary: A test summary.\n"
        "agent: test-agent\n"
        f"created_at: '{created_at}'\n"
        f"{options_yaml}"
        f"{resolution_block}"
        "---\n"
        f"{body}"
    )
    path = decisions_dir / f"{rid}.md"
    path.write_text(content, encoding="utf-8")
    return path, rid


def _write_legacy_dr(kanban_dir: Path, task_id: int, slug: str = "decision") -> Path:
    """Write a legacy DR file (non-UUID4 named) to decisions/pending/."""
    pending_dir = kanban_dir / "decisions" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    path = pending_dir / f"{task_id}-{slug}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: legacy-agent\n"
        "request_type: legacy-decision\n"
        "created: '2026-01-01'\n"
        "response: pending\n"
        "---\n\n"
        "Legacy DR body.\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _parse_frontmatter(path: Path) -> dict:
    """Return parsed YAML frontmatter from a request file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), "File must start with ---"
    lines = text.splitlines()
    close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
    yaml_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(yaml_text) or {}


# ---------------------------------------------------------------------------
# TestFromAC_ListRequests  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_ListRequests:
    """AC1: list_requests scans pending/resolved/both dirs, filters, skips corrupt, orders by created_at."""

    def test_list_pending_returns_records(self, tmp_path: Path) -> None:
        """AC1 happy: list_requests(status='pending') returns one RequestRecord per UUID4 file in pending/."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")

        result = engine.list_requests(status="pending")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], RequestRecord)
        assert result[0].request_id == rid

    def test_list_resolved_returns_records(self, tmp_path: Path) -> None:
        """AC1 happy: list_requests(status='resolved') scans resolved/ only."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _write_request_file(kanban_dir, subdir="pending", task_id=42, kind="action")
        _, rid = _write_request_file(
            kanban_dir,
            subdir="resolved",
            task_id=42,
            kind="action",
            resolved_at="2026-05-24T14:00:00+02:00",
        )

        result = engine.list_requests(status="resolved")

        assert len(result) == 1
        assert result[0].request_id == rid

    def test_list_all_returns_both_dirs(self, tmp_path: Path) -> None:
        """AC1 happy: list_requests(status='all') returns records from pending/ and resolved/."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _write_request_file(
            kanban_dir, subdir="pending", task_id=42, kind="action", created_at="2026-05-24T10:00:00+02:00"
        )
        _write_request_file(
            kanban_dir,
            subdir="resolved",
            task_id=42,
            kind="action",
            created_at="2026-05-24T11:00:00+02:00",
            resolved_at="2026-05-24T14:00:00+02:00",
        )

        result = engine.list_requests(status="all")

        assert len(result) == 2

    def test_list_empty_returns_empty_list(self, tmp_path: Path) -> None:
        """AC1 edge: list_requests returns [] when no files exist in the scanned dir."""
        engine, _ = _make_engine(tmp_path, 42)

        result = engine.list_requests(status="pending")

        assert result == []

    def test_list_pending_task_id_filter(self, tmp_path: Path) -> None:
        """AC1 happy: list_requests with task_id filters to matching records only."""
        engine, kanban_dir = _make_engine(tmp_path, 42, 99)
        _, rid_42 = _write_request_file(kanban_dir, task_id=42, kind="action")
        _write_request_file(kanban_dir, task_id=99, kind="action")

        result = engine.list_requests(status="pending", task_id=42)

        assert len(result) == 1
        assert result[0].request_id == rid_42

    def test_list_pending_task_id_no_match_returns_empty(self, tmp_path: Path) -> None:
        """AC1 edge: list_requests with task_id that matches no file returns []."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _write_request_file(kanban_dir, task_id=42, kind="action")

        result = engine.list_requests(status="pending", task_id=999)

        assert result == []

    def test_list_excludes_legacy_filenames(self, tmp_path: Path) -> None:
        """AC1 edge: legacy {task_id}-{slug}.md files are excluded from list_requests."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _write_legacy_dr(kanban_dir, task_id=42)

        result = engine.list_requests(status="pending")

        assert result == []

    def test_list_skips_corrupt_yaml_no_raise(self, tmp_path: Path) -> None:
        """AC1 error: corrupt YAML in a pending file is skipped with no exception raised."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        # Write a corrupt UUID4-named file
        corrupt_id = str(uuid.uuid4())
        decisions_dir = kanban_dir / "decisions" / "pending"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / f"{corrupt_id}.md").write_text(
            "---\n: invalid: yaml: {[}\n---\n",
            encoding="utf-8",
        )

        result = engine.list_requests(status="pending")

        assert result == []

    def test_list_skips_corrupt_yaml_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """AC1 error: corrupt YAML skip emits a WARNING-level log."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        corrupt_id = str(uuid.uuid4())
        decisions_dir = kanban_dir / "decisions" / "pending"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / f"{corrupt_id}.md").write_text(
            "---\n: invalid: yaml: {[}\n---\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="owlbear_kanban.engine"):
            engine.list_requests(status="pending")

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_list_ordered_by_created_at_ascending(self, tmp_path: Path) -> None:
        """AC1 boundary: list_requests results are ordered by created_at ascending."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid_later = _write_request_file(
            kanban_dir, task_id=42, kind="action", created_at="2026-05-24T14:00:00+02:00"
        )
        _, rid_earlier = _write_request_file(
            kanban_dir, task_id=42, kind="action", created_at="2026-05-24T10:00:00+02:00"
        )

        result = engine.list_requests(status="pending")

        assert len(result) == 2
        assert result[0].request_id == rid_earlier
        assert result[1].request_id == rid_later


# ---------------------------------------------------------------------------
# TestFromAC_SweepRequests  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_SweepRequests:
    """AC2: sweep_requests detects manually-resolved pending requests and finalizes them."""

    def test_sweep_returns_empty_when_nothing_resolvable(self, tmp_path: Path) -> None:
        """AC2 happy: no pending files with resolution fields set → returns []."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _write_request_file(kanban_dir, task_id=42, kind="action")  # both null → not swept

        result = engine.sweep_requests()

        assert result == []

    def test_sweep_resolves_decision_with_selected_option_id(self, tmp_path: Path) -> None:
        """AC2 happy: pending decision file with selected_option_id non-null → request_id in returned list."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision", selected_option_id="option-a")

        result = engine.sweep_requests()

        assert rid in result

    def test_sweep_resolves_action_with_free_text(self, tmp_path: Path) -> None:
        """AC2 happy: pending action file with free_text non-null → request_id in returned list."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Action done.")

        result = engine.sweep_requests()

        assert rid in result

    def test_sweep_moves_to_resolved_dir(self, tmp_path: Path) -> None:
        """AC2 happy: sweep writes the request file to decisions/resolved/{id}.md."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        engine.sweep_requests()

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        assert resolved_path.exists()

    def test_sweep_deletes_from_pending_dir(self, tmp_path: Path) -> None:
        """AC2 happy: sweep removes the file from decisions/pending/ after move."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        engine.sweep_requests()

        pending_path = kanban_dir / "decisions" / "pending" / f"{rid}.md"
        assert not pending_path.exists()

    def test_sweep_resolved_at_is_tz_aware_iso8601(self, tmp_path: Path) -> None:
        """AC2 happy: after sweep, resolved file has a tz-aware ISO 8601 resolved_at."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        engine.sweep_requests()

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        fm = _parse_frontmatter(resolved_path)
        resolved_at = fm.get("resolution", {}).get("resolved_at")
        assert resolved_at is not None
        parsed = datetime.fromisoformat(resolved_at)
        assert parsed.tzinfo is not None

    def test_sweep_appends_writeback_to_task(self, tmp_path: Path) -> None:
        """AC2 happy: sweep appends a ## AR/DR: title write-back block to the task body."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Action outcome.")

        engine.sweep_requests()

        task = engine.show_task("42")
        assert "## AR: Test Request" in task.body
        assert "**Outcome:** Action outcome." in task.body

    def test_sweep_unblocks_task_when_no_sibling_pending(self, tmp_path: Path) -> None:
        """AC2 happy: task is unblocked after sweep when it is the only pending structured request."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        engine.sweep_requests()

        task = engine.show_task("42")
        assert task.blocked is False

    def test_sweep_keeps_task_blocked_with_sibling_pending(self, tmp_path: Path) -> None:
        """AC2 edge: task stays blocked when another structured pending request for the same task remains."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        # One resolvable request
        _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")
        # Sibling still pending (no resolution fields set)
        _write_request_file(kanban_dir, task_id=42, kind="action")

        engine.sweep_requests()

        task = engine.show_task("42")
        assert task.blocked is True

    def test_sweep_returns_multiple_request_ids(self, tmp_path: Path) -> None:
        """AC2 happy: two resolvable pending files → both request_ids in returned list."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid1 = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done A.")
        _, rid2 = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done B.")

        result = engine.sweep_requests()

        assert rid1 in result
        assert rid2 in result
        assert len(result) == 2

    def test_sweep_processes_in_sorted_filename_order(self, tmp_path: Path) -> None:
        """AC2 edge: sweep processes files in sorted filename order (deterministic)."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        # Use fixed UUIDs with predictable sort order
        rid_a = "00000000-0000-4000-8000-000000000001"
        rid_b = "ffffffff-ffff-4fff-bfff-ffffffffffff"
        _write_request_file(kanban_dir, request_id=rid_b, task_id=42, kind="action", free_text="B.")
        _write_request_file(kanban_dir, request_id=rid_a, task_id=42, kind="action", free_text="A.")

        result = engine.sweep_requests()

        # rid_a sorts before rid_b lexicographically
        assert result.index(rid_a) < result.index(rid_b)


# ---------------------------------------------------------------------------
# TestFromAC_SweepErrorHandling  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_SweepErrorHandling:
    """AC3: sweep_requests handles corrupt files and post-move side-effect failures gracefully."""

    def test_sweep_skips_corrupt_yaml_no_raise(self, tmp_path: Path) -> None:
        """AC3 error: corrupt YAML in a pending UUID4 file is skipped — no exception raised."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        decisions_dir = kanban_dir / "decisions" / "pending"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        corrupt_id = str(uuid.uuid4())
        (decisions_dir / f"{corrupt_id}.md").write_text(
            "---\n: invalid: yaml: {[}\n---\n",
            encoding="utf-8",
        )

        result = engine.sweep_requests()

        assert result == []

    def test_sweep_skips_corrupt_yaml_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """AC3 error: corrupt YAML skip in sweep emits a WARNING-level log."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        decisions_dir = kanban_dir / "decisions" / "pending"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        corrupt_id = str(uuid.uuid4())
        (decisions_dir / f"{corrupt_id}.md").write_text(
            "---\n: invalid: yaml: {[}\n---\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="owlbear_kanban.engine"):
            engine.sweep_requests()

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_sweep_skips_pydantic_validation_failure_no_raise(self, tmp_path: Path) -> None:
        """AC3 error: file with valid YAML but invalid model fields (kind missing) is skipped."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        decisions_dir = kanban_dir / "decisions" / "pending"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        bad_id = str(uuid.uuid4())
        (decisions_dir / f"{bad_id}.md").write_text(
            "---\n"
            f"request_id: '{bad_id}'\n"
            "task_id: 42\n"
            # kind is missing — will fail Pydantic discriminated union
            "title: Bad request\n"
            "summary: summary\n"
            "agent: test-agent\n"
            "created_at: '2026-05-24T12:00:00+02:00'\n"
            "options: []\n"
            "resolution:\n"
            "  selected_option_id: 'option-a'\n"  # non-null → would trigger sweep
            "  free_text: null\n"
            "  resolved_at: null\n"
            "---\n",
            encoding="utf-8",
        )

        result = engine.sweep_requests()

        assert result == []

    def test_sweep_includes_request_id_when_writeback_raises(self, tmp_path: Path) -> None:
        """AC3 error: if edit_task (write-back) raises after move, request_id is still in result."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with patch.object(engine, "edit_task", side_effect=RuntimeError("disk full")):
            result = engine.sweep_requests()

        assert rid in result

    def test_sweep_move_preserved_when_edit_task_raises_resolved_exists(self, tmp_path: Path) -> None:
        """AC3 error: resolved file exists in decisions/resolved/ even when edit_task raises."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with patch.object(engine, "edit_task", side_effect=RuntimeError("disk full")):
            engine.sweep_requests()

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        assert resolved_path.exists()

    def test_sweep_move_preserved_when_edit_task_raises_pending_absent(self, tmp_path: Path) -> None:
        """AC3 error: pending file is removed from decisions/pending/ even when edit_task raises."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with patch.object(engine, "edit_task", side_effect=RuntimeError("disk full")):
            engine.sweep_requests()

        pending_path = kanban_dir / "decisions" / "pending" / f"{rid}.md"
        assert not pending_path.exists()

    def test_sweep_side_effect_failure_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """AC3 error: post-move side-effect failure emits a WARNING-level log."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with (
            patch.object(engine, "edit_task", side_effect=RuntimeError("disk full")),
            caplog.at_level(logging.WARNING, logger="owlbear_kanban.engine"),
        ):
            engine.sweep_requests()

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_sweep_continues_after_writeback_error(self, tmp_path: Path) -> None:
        """AC3 error: when the first file's writeback raises, the second file is still processed."""
        engine, kanban_dir = _make_engine(tmp_path, 42, 99)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        engine.edit_task("99", blocked=True, block_reason="DR pending")

        rid_a = "00000000-0000-4000-8000-000000000001"
        rid_b = "ffffffff-ffff-4fff-bfff-ffffffffffff"
        _write_request_file(kanban_dir, request_id=rid_a, task_id=42, kind="action", free_text="A.")
        _write_request_file(kanban_dir, request_id=rid_b, task_id=99, kind="action", free_text="B.")

        call_count = 0
        real_edit_task = engine.edit_task

        def _failing_first_call(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "disk full"
                raise RuntimeError(msg)
            return real_edit_task(*args, **kwargs)

        with patch.object(engine, "edit_task", side_effect=_failing_first_call):
            result = engine.sweep_requests()

        # Both request IDs must appear in the result
        assert rid_a in result
        assert rid_b in result

    # ------------------------------------------------------------------
    # AC3b — unblock-failure branch (write-back succeeds, unblock raises)
    # ------------------------------------------------------------------

    def test_sweep_includes_request_id_when_unblock_raises(self, tmp_path: Path) -> None:
        """AC3b error: if unblock edit_task raises after successful write-back, request_id is still returned."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        # First call (write-back) succeeds; second call (unblock) raises.
        with patch.object(engine, "edit_task", side_effect=[None, RuntimeError("unblock failed")]):
            result = engine.sweep_requests()

        assert rid in result

    def test_sweep_move_preserved_when_unblock_raises_resolved_exists(self, tmp_path: Path) -> None:
        """AC3b error: resolved file exists in decisions/resolved/ even when unblock raises."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with patch.object(engine, "edit_task", side_effect=[None, RuntimeError("unblock failed")]):
            engine.sweep_requests()

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        assert resolved_path.exists()

    def test_sweep_move_preserved_when_unblock_raises_pending_absent(self, tmp_path: Path) -> None:
        """AC3b error: pending file is removed from decisions/pending/ even when unblock raises."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with patch.object(engine, "edit_task", side_effect=[None, RuntimeError("unblock failed")]):
            engine.sweep_requests()

        pending_path = kanban_dir / "decisions" / "pending" / f"{rid}.md"
        assert not pending_path.exists()

    def test_sweep_unblock_failure_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """AC3b error: unblock failure after successful write-back emits a WARNING-level log."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        _write_request_file(kanban_dir, task_id=42, kind="action", free_text="Done.")

        with (
            patch.object(engine, "edit_task", side_effect=[None, RuntimeError("unblock failed")]),
            caplog.at_level(logging.WARNING, logger="owlbear_kanban.engine"),
        ):
            engine.sweep_requests()

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_sweep_continues_after_unblock_error(self, tmp_path: Path) -> None:
        """AC3b error: when first file's unblock raises, second file is still processed."""
        engine, kanban_dir = _make_engine(tmp_path, 42, 99)
        engine.edit_task("42", blocked=True, block_reason="DR pending")
        engine.edit_task("99", blocked=True, block_reason="DR pending")

        rid_a = "00000000-0000-4000-8000-aaaaaaaaaaaa"
        rid_b = "ffffffff-ffff-4fff-bfff-ffffffffffff"
        _write_request_file(kanban_dir, request_id=rid_a, task_id=42, kind="action", free_text="A.")
        _write_request_file(kanban_dir, request_id=rid_b, task_id=99, kind="action", free_text="B.")

        # Four edit_task calls during sweep: writeback(42), unblock(42), writeback(99), unblock(99).
        # unblock(42) → call 2 → fails; remaining calls succeed.
        with patch.object(
            engine,
            "edit_task",
            side_effect=[None, RuntimeError("unblock 42 failed"), None, None],
        ):
            result = engine.sweep_requests()

        assert rid_a in result
        assert rid_b in result


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksSweepWiring  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksSweepWiring:
    """AC4: AgentView.pick_tasks calls engine.sweep_requests() first; handles its failure gracefully."""

    def test_pick_tasks_calls_sweep_requests(self, tmp_path: Path) -> None:
        """AC4 happy: pick_tasks invokes engine.sweep_requests() exactly once."""
        engine, _ = _make_engine(tmp_path)

        with patch.object(engine, "sweep_requests", return_value=[]) as mock_sweep:
            engine.agent_view().pick_tasks()

        mock_sweep.assert_called_once()

    def test_pick_tasks_continues_when_sweep_raises(self, tmp_path: Path) -> None:
        """AC4 error: pick_tasks does not propagate exceptions from sweep_requests."""
        engine, _ = _make_engine(tmp_path)

        with patch.object(engine, "sweep_requests", side_effect=RuntimeError("sweep boom")):
            # Must not raise — pick_tasks catches and continues
            result = engine.agent_view().pick_tasks()

        assert result is not None

    def test_pick_tasks_logs_warning_when_sweep_raises(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """AC4 error: pick_tasks emits a WARNING when sweep_requests raises."""
        engine, _ = _make_engine(tmp_path)

        with (
            patch.object(engine, "sweep_requests", side_effect=RuntimeError("sweep boom")),
            caplog.at_level(logging.WARNING, logger="owlbear_kanban.agent_view"),
        ):
            engine.agent_view().pick_tasks()

        assert any(r.levelno == logging.WARNING for r in caplog.records)
