"""Smoke tests for #1518: user_message listings in proof_bundle ValidationError.

AC coverage:
  AC1 → TestFromAC_ProofBundleUserMessage — create_task/edit_task ValidationError
         user_message contains every member of VALID_PROOF_BUNDLES
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import VALID_PROOF_BUNDLES
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Shared board configuration (minimal copy — avoids cross-task import)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: todo
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: builder
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
blocked: false
block_reason: null
depends_on: []
claimed_at: null
archival_reason: null
archival_refs: []
---
Body.
"""


def _make_engine(base_dir: Path) -> tuple[KanbanEngine, Path]:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return engine, kanban_dir


def _write_task(kanban_dir: Path, task_id: int = 1) -> None:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title="Task",
        status="todo",
        priority="needed",
    )
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{task_id}-task.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# AC1 — user_message contains all VALID_PROOF_BUNDLES members
# ---------------------------------------------------------------------------


class TestFromAC_ProofBundleUserMessage:
    """AC1: ValidationError from invalid proof_bundle has user_message listing every valid bundle."""

    def test_create_task_invalid_proof_bundle_user_message_contains_all_valid_bundles(
        self, tmp_path: Path
    ) -> None:
        """AC1: create_task invalid proof_bundle → user_message mentions every VALID_PROOF_BUNDLES member."""
        engine, _ = _make_engine(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task(title="T", proof_bundle="bogus")
        msg = exc_info.value.user_message
        for member in VALID_PROOF_BUNDLES:
            assert member in msg, (
                f"Expected VALID_PROOF_BUNDLES member {member!r} in user_message, got: {msg!r}"
            )

    def test_edit_task_invalid_proof_bundle_user_message_contains_all_valid_bundles(
        self, tmp_path: Path
    ) -> None:
        """AC1: edit_task invalid proof_bundle → user_message mentions every VALID_PROOF_BUNDLES member."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", proof_bundle="not-a-bundle")
        msg = exc_info.value.user_message
        for member in VALID_PROOF_BUNDLES:
            assert member in msg, (
                f"Expected VALID_PROOF_BUNDLES member {member!r} in user_message, got: {msg!r}"
            )
