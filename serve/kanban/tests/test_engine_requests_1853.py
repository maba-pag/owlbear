"""Failing RED-phase tests for #1853: Engine API — resolve_request with conditional unblock.

AC coverage:
  AC1 → TestFromAC_ResolveRequest:
        test_resolve_decision_returns_populated_resolution
        test_resolve_action_returns_populated_resolution
        test_resolve_writes_to_resolved_dir
        test_resolve_deletes_from_pending_dir
        test_resolve_resolved_at_is_tz_aware_iso8601
        test_resolve_resolved_file_has_resolved_at_in_frontmatter
  AC2 →
        test_resolve_not_found_raises_not_found_error
        test_resolve_already_resolved_raises_validation_error
        test_resolve_already_resolved_exact_error_code
  AC3 →
        test_resolve_decision_invalid_option_id_raises_validation_error
        test_resolve_action_with_non_none_option_id_raises_validation_error
        test_resolve_both_null_raises_validation_error
        test_resolve_decision_text_only_valid
        test_resolve_action_free_text_only_valid
  AC4 →
        test_writeback_decision_option_only
        test_writeback_decision_option_and_text
        test_writeback_decision_text_only
        test_writeback_action
  AC5 →
        test_unblocks_task_when_no_sibling_pending
        test_keeps_task_blocked_with_sibling_pending
        test_legacy_dr_not_counted_as_sibling
        test_sibling_different_task_id_not_counted

All 22 tests FAIL in RED phase: resolve_request does not exist yet.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from owlbear_kanban import KanbanEngine, NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Board / task scaffolding
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

# Two valid options for a decision request.
_OPTIONS_VALID = [
    {
        "option_id": "option-a",
        "label": "Option Alpha",
        "confidence": 0.8,
        "recommended": True,
        "rationale": "First option rationale.",
    },
    {
        "option_id": "option-b",
        "label": "Option Beta",
        "confidence": 0.5,
        "recommended": False,
        "rationale": "Second option rationale.",
    },
]


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
    body: str = "",
    resolved_at: str | None = None,
) -> tuple[Path, str]:
    """Write a minimal valid structured request YAML file to decisions/{subdir}/."""
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

    resolved_at_line = f"  resolved_at: '{resolved_at}'\n" if resolved_at else "  resolved_at: null\n"

    content = (
        "---\n"
        f"request_id: '{rid}'\n"
        f"task_id: {task_id}\n"
        f"kind: {kind}\n"
        "title: Test Request\n"
        "summary: A test summary.\n"
        "agent: test-agent\n"
        "created_at: '2026-05-24T12:00:00+02:00'\n"
        f"{options_yaml}"
        "resolution:\n"
        "  selected_option_id: null\n"
        "  free_text: null\n"
        f"{resolved_at_line}"
        "---\n"
        f"{body}"
    )
    path = decisions_dir / f"{rid}.md"
    path.write_text(content, encoding="utf-8")
    return path, rid


def _parse_frontmatter(path: Path) -> dict:
    """Return parsed YAML frontmatter from a request file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), "File must start with ---"
    lines = text.splitlines()
    close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
    yaml_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(yaml_text) or {}


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


# ---------------------------------------------------------------------------
# TestFromAC_ResolveRequest
# ---------------------------------------------------------------------------


class TestFromAC_ResolveRequest:
    """Tests derived from AC1-AC5 for resolve_request."""

    # -----------------------------------------------------------------------
    # AC1 — returns RequestRecord with populated resolution fields,
    #        writes to resolved/, deletes from pending/
    # -----------------------------------------------------------------------

    def test_resolve_decision_returns_populated_resolution(self, tmp_path: Path) -> None:
        """AC1: resolve_request for a decision returns RequestRecord with resolution fields set."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        result = engine.resolve_request(rid, "option-a", None)

        assert result.resolution.selected_option_id == "option-a"
        assert result.resolution.free_text is None
        assert result.resolution.resolved_at is not None

    def test_resolve_action_returns_populated_resolution(self, tmp_path: Path) -> None:
        """AC1: resolve_request for an action returns RequestRecord with resolution fields set."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        result = engine.resolve_request(rid, None, "Completed the action.")

        assert result.resolution.selected_option_id is None
        assert result.resolution.free_text == "Completed the action."
        assert result.resolution.resolved_at is not None

    def test_resolve_writes_to_resolved_dir(self, tmp_path: Path) -> None:
        """AC1: resolve_request writes updated file to decisions/resolved/{request_id}.md."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Done.")

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        assert resolved_path.exists()

    def test_resolve_deletes_from_pending_dir(self, tmp_path: Path) -> None:
        """AC1: resolve_request deletes the file from decisions/pending/ after resolving."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Done.")

        pending_path = kanban_dir / "decisions" / "pending" / f"{rid}.md"
        assert not pending_path.exists()

    def test_resolve_resolved_at_is_tz_aware_iso8601(self, tmp_path: Path) -> None:
        """AC1: resolved_at on returned RequestRecord is a tz-aware ISO 8601 datetime string."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        result = engine.resolve_request(rid, None, "Done.")

        assert result.resolution.resolved_at is not None
        parsed = datetime.fromisoformat(result.resolution.resolved_at)
        assert parsed.tzinfo is not None, "resolved_at must include timezone information"

    def test_resolve_resolved_file_has_resolved_at_in_frontmatter(self, tmp_path: Path) -> None:
        """AC1: the file written to resolved/ has resolved_at populated in its frontmatter."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Done.")

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        fm = _parse_frontmatter(resolved_path)
        assert fm.get("resolution", {}).get("resolved_at") is not None

    # -----------------------------------------------------------------------
    # AC2 — error paths: not found, already resolved
    # -----------------------------------------------------------------------

    def test_resolve_not_found_raises_not_found_error(self, tmp_path: Path) -> None:
        """AC2: resolve_request raises NotFoundError when request_id not in pending/."""
        engine, _ = _make_engine(tmp_path, 42)
        missing_id = str(uuid.uuid4())

        with pytest.raises(NotFoundError) as exc_info:
            engine.resolve_request(missing_id, None, "text")

        assert exc_info.value.code == "ERR_NOT_FOUND"

    def test_resolve_already_resolved_raises_validation_error(self, tmp_path: Path) -> None:
        """AC2: resolve_request raises ValidationError when file exists only in resolved/."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(
            kanban_dir,
            subdir="resolved",
            task_id=42,
            kind="action",
            resolved_at="2026-05-24T10:00:00+02:00",
        )

        with pytest.raises(ValidationError):
            engine.resolve_request(rid, None, "Again.")

    def test_resolve_already_resolved_exact_error_code(self, tmp_path: Path) -> None:
        """AC2: ValidationError raised for already-resolved request uses ERR_ALREADY_RESOLVED code."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(
            kanban_dir,
            subdir="resolved",
            task_id=42,
            kind="action",
            resolved_at="2026-05-24T10:00:00+02:00",
        )

        with pytest.raises(ValidationError) as exc_info:
            engine.resolve_request(rid, None, "Again.")

        assert exc_info.value.code == "ERR_ALREADY_RESOLVED"

    # -----------------------------------------------------------------------
    # AC3 — validation: option_id cross-check, kind constraints, both-None guard
    # -----------------------------------------------------------------------

    def test_resolve_decision_invalid_option_id_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC3: resolve_request raises ValidationError when selected_option_id doesn't match any option."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        with pytest.raises(ValidationError):
            engine.resolve_request(rid, "option-nonexistent", None)

    def test_resolve_action_with_non_none_option_id_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC3: resolve_request raises ValidationError when action request receives non-None selected_option_id."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        with pytest.raises(ValidationError):
            engine.resolve_request(rid, "option-a", "Some text.")

    def test_resolve_both_null_raises_validation_error(self, tmp_path: Path) -> None:
        """AC3: resolve_request raises ValidationError when both selected_option_id and free_text are None."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        with pytest.raises(ValidationError):
            engine.resolve_request(rid, None, None)

    def test_resolve_decision_text_only_valid(self, tmp_path: Path) -> None:
        """AC3: resolve_request accepts decision + None option_id + free_text (write-back variant 3)."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        result = engine.resolve_request(rid, None, "My decision rationale.")

        assert result.resolution.selected_option_id is None
        assert result.resolution.free_text == "My decision rationale."

    def test_resolve_action_free_text_only_valid(self, tmp_path: Path) -> None:
        """AC3: resolve_request accepts action + None option_id + free_text."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        result = engine.resolve_request(rid, None, "Action completed successfully.")

        assert result.resolution.selected_option_id is None
        assert result.resolution.free_text == "Action completed successfully."

    # -----------------------------------------------------------------------
    # AC4 — write-back: four format variants appended to task body
    # -----------------------------------------------------------------------

    def test_writeback_decision_option_only(self, tmp_path: Path) -> None:
        """AC4 variant 1: decision + option selected → '## DR: {title}\\n- **Selected:** {label}'."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, "option-a", None)

        task = engine.show_task("42")
        assert "## DR: Test Request" in task.body
        assert "**Selected:** Option Alpha" in task.body

    def test_writeback_decision_option_and_text(self, tmp_path: Path) -> None:
        """AC4 variant 2: decision + option + text → selected label + notes line."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, "option-b", "Some extra context.")

        task = engine.show_task("42")
        assert "## DR: Test Request" in task.body
        assert "**Selected:** Option Beta" in task.body
        assert "**Notes:** Some extra context." in task.body

    def test_writeback_decision_text_only(self, tmp_path: Path) -> None:
        """AC4 variant 3: decision + text only → '## DR: {title}\\n- **Answer:** {free_text}'."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Free-text answer here.")

        task = engine.show_task("42")
        assert "## DR: Test Request" in task.body
        assert "**Answer:** Free-text answer here." in task.body

    def test_writeback_action(self, tmp_path: Path) -> None:
        """AC4 variant 4: action → '## AR: {title}\\n- **Outcome:** {free_text}'."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Action outcome text.")

        task = engine.show_task("42")
        assert "## AR: Test Request" in task.body
        assert "**Outcome:** Action outcome text." in task.body

    # -----------------------------------------------------------------------
    # AC5 — conditional unblock: sibling check (UUID4-named, matching task_id)
    # -----------------------------------------------------------------------

    def test_unblocks_task_when_no_sibling_pending(self, tmp_path: Path) -> None:
        """AC5: task is unblocked (blocked=False) when no other structured pending requests remain."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Done.")

        task = engine.show_task("42")
        assert task.blocked is False

    def test_keeps_task_blocked_with_sibling_pending(self, tmp_path: Path) -> None:
        """AC5: task remains blocked when another structured pending request for same task_id exists."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid1 = _write_request_file(kanban_dir, task_id=42, kind="action")
        _, _rid2 = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid1, None, "First done.")

        task = engine.show_task("42")
        assert task.blocked is True

    def test_legacy_dr_not_counted_as_sibling(self, tmp_path: Path) -> None:
        """AC5: a legacy DR file (non-UUID4 filename) in pending/ is NOT counted as a sibling."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        _write_legacy_dr(kanban_dir, task_id=42, slug="some-decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Done.")

        task = engine.show_task("42")
        assert task.blocked is False, (
            "Legacy DR (non-UUID4 filename) must not count as a structured sibling"
        )

    def test_sibling_different_task_id_not_counted(self, tmp_path: Path) -> None:
        """AC5: a structured pending request belonging to a different task_id is not a sibling."""
        engine, kanban_dir = _make_engine(tmp_path, 42, 43)
        _, rid42 = _write_request_file(kanban_dir, task_id=42, kind="action")
        _write_request_file(kanban_dir, task_id=43, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid42, None, "Task 42 done.")

        task42 = engine.show_task("42")
        assert task42.blocked is False, (
            "Structured request for a different task_id must not prevent unblocking"
        )

    # -----------------------------------------------------------------------
    # Retry-gap tests — AC1: resolved-file field assertions (Findings 1+2)
    # -----------------------------------------------------------------------

    def test_resolved_file_has_selected_option_id_serialized(self, tmp_path: Path) -> None:
        """AC1 (retry): resolved file frontmatter has selected_option_id matching the resolved option."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, "option-a", None)

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        fm = _parse_frontmatter(resolved_path)
        assert fm["resolution"]["selected_option_id"] == "option-a"

    def test_resolved_file_has_free_text_serialized_action(self, tmp_path: Path) -> None:
        """AC1 (retry): resolved file frontmatter has free_text matching the provided action outcome."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "My action outcome.")

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        fm = _parse_frontmatter(resolved_path)
        assert fm["resolution"]["free_text"] == "My action outcome."

    def test_resolved_file_has_free_text_serialized_decision(self, tmp_path: Path) -> None:
        """AC1 (retry): resolved file frontmatter has free_text for decision+text-only variant."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Decision rationale.")

        resolved_path = kanban_dir / "decisions" / "resolved" / f"{rid}.md"
        fm = _parse_frontmatter(resolved_path)
        assert fm["resolution"]["free_text"] == "Decision rationale."

    def test_resolved_at_bounded_to_current_time(self, tmp_path: Path) -> None:
        """AC1 (retry): resolved_at in the returned record is bounded to the current resolution time (not stale)."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        before = datetime.now().astimezone()
        result = engine.resolve_request(rid, None, "Done.")
        after = datetime.now().astimezone()

        resolved_at = datetime.fromisoformat(result.resolution.resolved_at)
        assert before <= resolved_at <= after, (
            f"resolved_at {resolved_at} must be between {before} and {after}"
        )

    # -----------------------------------------------------------------------
    # Retry-gap tests — AC4: exact write-back blocks (Finding 3)
    # -----------------------------------------------------------------------

    def test_writeback_decision_option_only_exact_block(self, tmp_path: Path) -> None:
        """AC4 (retry): variant 1 write-back is exactly '## DR: {title}\\n- **Selected:** {label}', no extra lines."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, "option-a", None)

        task = engine.show_task("42")
        exact_block = "## DR: Test Request\n- **Selected:** Option Alpha"
        assert exact_block in task.body
        # Variant 1 must not contain Notes or Answer lines
        assert "**Notes:**" not in task.body
        assert "**Answer:**" not in task.body

    def test_writeback_decision_option_and_text_exact_block(self, tmp_path: Path) -> None:
        """AC4 (retry): variant 2 write-back includes selected label + notes line; no Answer line."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, "option-b", "Some extra context.")

        task = engine.show_task("42")
        exact_block = (
            "## DR: Test Request\n"
            "- **Selected:** Option Beta\n"
            "- **Notes:** Some extra context."
        )
        assert exact_block in task.body
        # Variant 2 must not contain Answer line
        assert "**Answer:**" not in task.body

    def test_writeback_decision_text_only_exact_block(self, tmp_path: Path) -> None:
        """AC4 (retry): variant 3 write-back is exactly '## DR: {title}\\n- **Answer:** {free_text}'; no Selected line."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="decision")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Free-text answer here.")

        task = engine.show_task("42")
        exact_block = "## DR: Test Request\n- **Answer:** Free-text answer here."
        assert exact_block in task.body
        # Variant 3 must not contain Selected or Notes lines
        assert "**Selected:**" not in task.body
        assert "**Notes:**" not in task.body

    def test_writeback_action_exact_block(self, tmp_path: Path) -> None:
        """AC4 (retry): variant 4 write-back is exactly '## AR: {title}\\n- **Outcome:** {free_text}'; no DR header."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Action outcome text.")

        task = engine.show_task("42")
        exact_block = "## AR: Test Request\n- **Outcome:** Action outcome text."
        assert exact_block in task.body
        # Variant 4 must not contain DR header, Selected, or Answer lines
        assert "## DR:" not in task.body
        assert "**Selected:**" not in task.body
        assert "**Answer:**" not in task.body

    def test_writeback_appends_not_replaces_existing_body(self, tmp_path: Path) -> None:
        """AC4 (retry): write-back is appended to existing task body content, not replacing it."""
        engine, kanban_dir = _make_engine(tmp_path, 42)
        _, rid = _write_request_file(kanban_dir, task_id=42, kind="action")
        engine.edit_task("42", blocked=True, block_reason="DR pending")

        engine.resolve_request(rid, None, "Action done.")

        task = engine.show_task("42")
        # Pre-existing body text from the task template must still be present
        assert "Body text." in task.body
        # The write-back block must also be present
        assert "## AR: Test Request" in task.body
