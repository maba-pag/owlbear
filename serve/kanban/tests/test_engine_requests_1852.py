"""Failing RED-phase tests for #1852: Engine API — create_request and get_request.

AC coverage:
  AC1 → TestFromAC_CreateRequest.test_create_request_decision_returns_model_fields
        TestFromAC_CreateRequest.test_create_request_action_returns_model_fields
        TestFromAC_CreateRequest.test_create_request_request_id_is_uuid4
        TestFromAC_CreateRequest.test_create_request_created_at_is_tz_aware_iso8601
        TestFromAC_CreateRequest.test_create_request_writes_file_to_pending_dir
        TestFromAC_CreateRequest.test_create_request_filename_is_request_id_dot_md
        TestFromAC_CreateRequest.test_create_request_returns_body_string
  AC2 → TestFromAC_CreateRequest.test_create_request_file_has_yaml_frontmatter
        TestFromAC_CreateRequest.test_create_request_resolution_selected_option_id_null
        TestFromAC_CreateRequest.test_create_request_resolution_free_text_null
        TestFromAC_CreateRequest.test_create_request_resolved_at_omitted_in_pending_file
        TestFromAC_CreateRequest.test_create_request_body_below_closing_delimiter
  AC3 → TestFromAC_CreateRequest.test_create_request_blocks_task
        TestFromAC_CreateRequest.test_create_request_rollback_deletes_file_on_block_failure
        TestFromAC_CreateRequest.test_create_request_rollback_reraises_exception
  AC4 → TestFromAC_GetRequest.test_get_request_finds_in_pending
        TestFromAC_GetRequest.test_get_request_finds_in_resolved
        TestFromAC_GetRequest.test_get_request_returns_model_fields_and_body
        TestFromAC_GetRequest.test_get_request_not_found_raises_not_found_error
        TestFromAC_GetRequest.test_get_request_corrupt_yaml_raises_validation_error
        TestFromAC_GetRequest.test_get_request_invalid_model_fields_raises_validation_error

All tests FAIL in RED phase: create_request and get_request do not exist yet.
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

# Two minimal valid options for a decision request.
_OPTIONS_VALID = [
    {
        "option_id": "option-a",
        "label": "Option A",
        "confidence": 0.7,
        "recommended": True,
        "rationale": "First option rationale.",
    },
    {
        "option_id": "option-b",
        "label": "Option B",
        "confidence": 0.4,
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


def _make_engine(base_dir: Path, task_id: int = 42) -> tuple[KanbanEngine, Path, int]:
    kanban_dir = _make_board(base_dir)
    _write_task(kanban_dir, task_id)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return engine, kanban_dir, task_id


def _write_request_file(  # noqa: PLR0913
    kanban_dir: Path,
    *,
    subdir: str = "pending",
    request_id: str | None = None,
    kind: str = "decision",
    extra_yaml: str = "",
    body: str = "",
) -> tuple[Path, str]:
    """Write a minimal valid request YAML file to decisions/{subdir}/."""
    rid = request_id or str(uuid.uuid4())
    decisions_dir = kanban_dir / "decisions" / subdir
    decisions_dir.mkdir(parents=True, exist_ok=True)

    if kind == "decision":
        options_yaml = (
            "options:\n"
            "  - option_id: option-a\n"
            "    label: Option A\n"
            "    confidence: 0.7\n"
            "    recommended: true\n"
            "    rationale: First rationale.\n"
            "  - option_id: option-b\n"
            "    label: Option B\n"
            "    confidence: 0.4\n"
            "    recommended: false\n"
            "    rationale: Second rationale.\n"
        )
    else:
        options_yaml = "options: []\n"

    content = (
        "---\n"
        f"request_id: '{rid}'\n"
        "task_id: 42\n"
        f"kind: {kind}\n"
        "title: Test Request\n"
        "summary: A test summary.\n"
        "agent: test-agent\n"
        "created_at: '2026-05-24T12:00:00+02:00'\n"
        f"{options_yaml}"
        "resolution:\n"
        "  selected_option_id: null\n"
        "  free_text: null\n"
        f"{extra_yaml}"
        "---\n"
        f"{body}"
    )
    path = decisions_dir / f"{rid}.md"
    path.write_text(content, encoding="utf-8")
    return path, rid


def _parse_frontmatter(path: Path) -> dict:
    """Return parsed YAML frontmatter from a DR file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), "File must start with ---"
    lines = text.splitlines()
    close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
    yaml_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(yaml_text) or {}


# ---------------------------------------------------------------------------
# TestFromAC_CreateRequest
# ---------------------------------------------------------------------------


class TestFromAC_CreateRequest:
    """Tests derived from AC1, AC2, and AC3."""

    # -----------------------------------------------------------------------
    # AC1 — happy path: returns object with model fields and body string
    # -----------------------------------------------------------------------

    def test_create_request_decision_returns_model_fields(self, tmp_path: Path) -> None:
        """AC1: create_request for decision kind returns object with expected model fields."""
        engine, _, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "decision",
            "Choose approach",
            "Pick one of the options.",
            "copilot",
            options=_OPTIONS_VALID,
        )
        assert result.task_id == task_id
        assert result.kind == "decision"
        assert result.title == "Choose approach"
        assert result.summary == "Pick one of the options."
        assert result.agent == "copilot"

    def test_create_request_action_returns_model_fields(self, tmp_path: Path) -> None:
        """AC1: create_request for action kind returns object with expected model fields."""
        engine, _, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Run migration",
            "Execute migration script.",
            "copilot",
        )
        assert result.task_id == task_id
        assert result.kind == "action"
        assert result.title == "Run migration"
        assert result.agent == "copilot"

    def test_create_request_request_id_is_uuid4(self, tmp_path: Path) -> None:
        """AC1: generated request_id must be a valid UUID4 string."""
        engine, _kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        parsed = uuid.UUID(result.request_id)
        assert parsed.version == 4

    def test_create_request_created_at_is_tz_aware_iso8601(self, tmp_path: Path) -> None:
        """AC1: generated created_at must be a timezone-aware ISO 8601 datetime."""
        engine, _kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        parsed = datetime.fromisoformat(result.created_at)
        assert parsed.tzinfo is not None

    def test_create_request_writes_file_to_pending_dir(self, tmp_path: Path) -> None:
        """AC1: create_request writes the file to decisions/pending/."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        pending_dir = kanban_dir / "decisions" / "pending"
        assert pending_dir.exists()
        md_files = list(pending_dir.glob("*.md"))
        assert len(md_files) == 1

    def test_create_request_filename_is_request_id_dot_md(self, tmp_path: Path) -> None:
        """AC1: the written file is named {request_id}.md in decisions/pending/."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        expected_path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        assert expected_path.exists()

    def test_create_request_returns_body_string(self, tmp_path: Path) -> None:
        """AC1: returned object exposes the body string passed at call time."""
        engine, _kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
            body="Extended context here.",
        )
        assert result.body == "Extended context here."

    def test_create_request_body_defaults_to_empty_string(self, tmp_path: Path) -> None:
        """AC1 edge: omitting body= defaults to empty string in returned object."""
        engine, _kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        assert result.body == ""

    def test_create_request_each_call_generates_unique_uuid(self, tmp_path: Path) -> None:
        """AC1 edge: consecutive calls produce distinct request_ids."""
        engine, _, task_id = _make_engine(tmp_path)
        r1 = engine.create_request(task_id, "action", "T1", "S1", "agent")
        r2 = engine.create_request(task_id, "action", "T2", "S2", "agent")
        assert r1.request_id != r2.request_id

    # -----------------------------------------------------------------------
    # AC2 — file format: frontmatter, resolution block, resolved_at absent
    # -----------------------------------------------------------------------

    def test_create_request_file_has_yaml_frontmatter(self, tmp_path: Path) -> None:
        """AC2: written file begins with YAML frontmatter delimited by ---."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        # Closing delimiter must also be present
        assert "\n---\n" in text

    def test_create_request_resolution_selected_option_id_null(self, tmp_path: Path) -> None:
        """AC2: frontmatter resolution block has selected_option_id: null."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        fm = _parse_frontmatter(path)
        assert fm["resolution"]["selected_option_id"] is None

    def test_create_request_resolution_free_text_null(self, tmp_path: Path) -> None:
        """AC2: frontmatter resolution block has free_text: null."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        fm = _parse_frontmatter(path)
        assert fm["resolution"]["free_text"] is None

    def test_create_request_resolved_at_omitted_in_pending_file(self, tmp_path: Path) -> None:
        """AC2: resolved_at must NOT appear in the frontmatter of a pending file."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        fm = _parse_frontmatter(path)
        resolution = fm.get("resolution", {})
        assert "resolved_at" not in resolution, "resolved_at must be absent in pending files"

    def test_create_request_body_below_closing_delimiter(self, tmp_path: Path) -> None:
        """AC2: markdown body is placed below the closing --- delimiter."""
        engine, kanban_dir, task_id = _make_engine(tmp_path)
        result = engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
            body="Markdown body content.",
        )
        path = kanban_dir / "decisions" / "pending" / f"{result.request_id}.md"
        text = path.read_text(encoding="utf-8")
        # Find the closing delimiter position
        parts = text.split("---\n", 2)
        # parts[0] = "" (before opening ---), parts[1] = frontmatter, parts[2] = body
        assert len(parts) >= 3
        assert "Markdown body content." in parts[2]

    # -----------------------------------------------------------------------
    # AC3 — task blocking and rollback
    # -----------------------------------------------------------------------

    def test_create_request_blocks_task(self, tmp_path: Path) -> None:
        """AC3: create_request sets task.blocked=True with block_reason='DR pending'."""
        engine, _kanban_dir, task_id = _make_engine(tmp_path)
        engine.create_request(
            task_id,
            "action",
            "Title",
            "Summary",
            "agent",
        )
        task = engine.show_task(str(task_id))
        assert task.blocked is True
        assert task.block_reason == "DR pending"

    def test_create_request_rollback_deletes_file_on_block_failure(self, tmp_path: Path) -> None:
        """AC3: if blocking fails, the created pending file is deleted (no orphan)."""
        engine, kanban_dir, _ = _make_engine(tmp_path)
        nonexistent_task_id = 9999  # task does not exist → edit_task will fail

        # Pre-condition: create_request must be defined — fails in RED phase
        assert callable(getattr(engine, "create_request", None)), (
            "create_request method not found on KanbanEngine"
        )

        with pytest.raises(Exception):  # noqa: B017 — any exception from blocking
            engine.create_request(
                nonexistent_task_id,
                "action",
                "Title",
                "Summary",
                "agent",
            )

        pending_dir = kanban_dir / "decisions" / "pending"
        orphan_files = list(pending_dir.glob("*.md")) if pending_dir.exists() else []
        assert orphan_files == [], f"Orphan files found after rollback: {orphan_files}"

    def test_create_request_rollback_reraises_exception(self, tmp_path: Path) -> None:
        """AC3: after rollback, the original blocking exception is re-raised."""
        engine, _, _ = _make_engine(tmp_path)
        nonexistent_task_id = 9999

        # Pre-condition: create_request must be defined — fails in RED phase
        assert callable(getattr(engine, "create_request", None)), (
            "create_request method not found on KanbanEngine"
        )

        with pytest.raises(Exception):  # noqa: B017
            engine.create_request(
                nonexistent_task_id,
                "action",
                "Title",
                "Summary",
                "agent",
            )


# ---------------------------------------------------------------------------
# TestFromAC_GetRequest
# ---------------------------------------------------------------------------


class TestFromAC_GetRequest:
    """Tests derived from AC4."""

    # -----------------------------------------------------------------------
    # AC4 — happy path: found in pending/ or resolved/
    # -----------------------------------------------------------------------

    def test_get_request_finds_in_pending(self, tmp_path: Path) -> None:
        """AC4: get_request returns validated fields when file is in pending/."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        _path, rid = _write_request_file(kanban_dir, subdir="pending")

        result = engine.get_request(rid)
        assert result.request_id == rid

    def test_get_request_finds_in_resolved(self, tmp_path: Path) -> None:
        """AC4: get_request returns validated fields when file is in resolved/."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        _path, rid = _write_request_file(kanban_dir, subdir="resolved")

        result = engine.get_request(rid)
        assert result.request_id == rid

    def test_get_request_returns_model_fields_and_body(self, tmp_path: Path) -> None:
        """AC4: returned object exposes validated model fields and body text."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        _path, rid = _write_request_file(
            kanban_dir,
            subdir="pending",
            kind="action",
            body="Extra context text.",
        )

        result = engine.get_request(rid)
        assert result.task_id == 42
        assert result.kind == "action"
        assert result.title == "Test Request"
        assert result.body == "Extra context text."

    # -----------------------------------------------------------------------
    # AC4 — error paths
    # -----------------------------------------------------------------------

    def test_get_request_not_found_raises_not_found_error(self, tmp_path: Path) -> None:
        """AC4: get_request raises NotFoundError when absent from both directories."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        missing_id = str(uuid.uuid4())

        with pytest.raises(NotFoundError):
            engine.get_request(missing_id)

    def test_get_request_corrupt_yaml_raises_validation_error(self, tmp_path: Path) -> None:
        """AC4: get_request raises ValidationError when file YAML is malformed."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        rid = str(uuid.uuid4())
        pending_dir = kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        (pending_dir / f"{rid}.md").write_text(
            "---\n: invalid: : yaml: {\n---\nbody\n",
            encoding="utf-8",
        )

        with pytest.raises(ValidationError):
            engine.get_request(rid)

    def test_get_request_invalid_model_fields_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: get_request raises ValidationError when YAML is valid but model fails."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        rid = str(uuid.uuid4())
        pending_dir = kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        # Valid YAML but request_id is not a UUID4 → model validation fails
        (pending_dir / f"{rid}.md").write_text(
            "---\n"
            "request_id: 'not-a-valid-uuid4'\n"
            "task_id: 42\n"
            "kind: action\n"
            "title: T\n"
            "summary: S\n"
            "agent: a\n"
            "created_at: '2026-01-01T00:00:00+00:00'\n"
            "options: []\n"
            "resolution:\n"
            "  selected_option_id: null\n"
            "  free_text: null\n"
            "---\n",
            encoding="utf-8",
        )

        with pytest.raises(ValidationError):
            engine.get_request(rid)

    # -----------------------------------------------------------------------
    # AC4 — edge cases
    # -----------------------------------------------------------------------

    def test_get_request_searches_pending_before_resolved(self, tmp_path: Path) -> None:
        """AC4 edge: if the same request_id exists in both dirs, pending is returned."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        rid = str(uuid.uuid4())
        # Write file to both directories with differing body to distinguish
        _write_request_file(kanban_dir, subdir="pending", request_id=rid, body="from-pending")
        _write_request_file(kanban_dir, subdir="resolved", request_id=rid, body="from-resolved")

        result = engine.get_request(rid)
        assert result.body == "from-pending"

    def test_get_request_empty_body_when_no_body_text(self, tmp_path: Path) -> None:
        """AC4 edge: body is empty string when file has no text below closing delimiter."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        _path, rid = _write_request_file(kanban_dir, subdir="pending", body="")

        result = engine.get_request(rid)
        assert result.body == ""

    def test_get_request_action_kind(self, tmp_path: Path) -> None:
        """AC4 edge: get_request correctly handles action-kind requests (no options)."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        _path, rid = _write_request_file(kanban_dir, subdir="pending", kind="action")

        result = engine.get_request(rid)
        assert result.kind == "action"
        assert result.options == []
