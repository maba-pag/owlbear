"""RED-phase failing tests for #1517: Engine ac/proof_bundle in create_task, edit_task, search.

AC coverage:
  AC1 → TestFromAC_ProofBundleValidation — create_task/edit_task ac/proof_bundle params,
         VALID_PROOF_BUNDLES frozenset enumerating bases x modifier subsets
  AC2 → TestFromAC_EditTaskAcMutation — edit_task ac/add_ac/remove_ac contract,
         mutual exclusivity with ValidationError(ERR_AC_EXCLUSIVE)
  AC3 → TestFromAC_EditTaskAddAcDuplicates — duplicate add_ac rejection with
         ValidationError(ERR_AC_DUPLICATE) listing existing items
  AC4 → TestFromAC_AcGuardrails — max 20 items (ERR_AC_LIMIT), 500-char limit
         (ERR_AC_ITEM_TOO_LONG) on create_task and edit_task
  AC5 → TestFromAC_ListTasksAcSearch — list_tasks search= matches ac items
         case-insensitively as substring match
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Shared board configuration
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
{extra_fields}---
{body}
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    body: str = "Body.",
    extra_fields: str = "",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        body=body,
        extra_fields=extra_fields,
    )
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    path = tasks_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> tuple[KanbanEngine, Path]:
    kanban_dir = _make_board(base_dir, config_yaml)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return engine, kanban_dir


# ---------------------------------------------------------------------------
# AC1 — create_task/edit_task accept ac/proof_bundle; VALID_PROOF_BUNDLES frozenset
# ---------------------------------------------------------------------------


class TestFromAC_ProofBundleValidation:
    """AC1: create_task/edit_task accept ac and proof_bundle; VALID_PROOF_BUNDLES frozenset."""

    def test_create_task_accepts_ac_param(self, tmp_path: Path) -> None:
        """AC1: create_task(ac=[...]) stores ac items on the returned Task."""
        engine, _ = _make_engine(tmp_path)
        ac_items = ["AC1: does X", "AC2: handles Y"]
        task = engine.create_task(title="T", ac=ac_items)
        assert task.ac == ac_items

    def test_create_task_accepts_proof_bundle_param(self, tmp_path: Path) -> None:
        """AC1: create_task(proof_bundle="behavioral") stores proof_bundle on the returned Task."""
        engine, _ = _make_engine(tmp_path)
        task = engine.create_task(title="T", proof_bundle="behavioral")
        assert task.proof_bundle == "behavioral"

    def test_create_task_valid_proof_bundle_with_modifier(self, tmp_path: Path) -> None:
        """AC1: create_task with a valid base+modifier proof_bundle is accepted and normalized."""
        engine, _ = _make_engine(tmp_path)
        task = engine.create_task(title="T", proof_bundle="behavioral+challenge")
        assert task.proof_bundle == "behavioral+challenge"

    def test_create_task_invalid_proof_bundle_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC1: create_task with proof_bundle not in VALID_PROOF_BUNDLES raises ValidationError."""
        engine, _ = _make_engine(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task(title="T", proof_bundle="bogus")
        assert exc_info.value.code == "ERR_PROOF_BUNDLE_INVALID"

    def test_edit_task_accepts_proof_bundle_param(self, tmp_path: Path) -> None:
        """AC1: edit_task(proof_bundle="smoke") updates proof_bundle on the task."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        task = engine.edit_task("1", proof_bundle="smoke")
        assert task.proof_bundle == "smoke"

    def test_edit_task_invalid_proof_bundle_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC1: edit_task with proof_bundle not in VALID_PROOF_BUNDLES raises ValidationError."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", proof_bundle="not-a-bundle")
        assert exc_info.value.code == "ERR_PROOF_BUNDLE_INVALID"

    def test_valid_proof_bundles_frozenset_exists(self) -> None:
        """AC1: VALID_PROOF_BUNDLES is exported from owlbear_kanban.engine as a frozenset."""
        from owlbear_kanban.engine import VALID_PROOF_BUNDLES  # noqa: PLC0415
        assert isinstance(VALID_PROOF_BUNDLES, frozenset)

    def test_valid_proof_bundles_contains_all_five_bases(self) -> None:
        """AC1: VALID_PROOF_BUNDLES contains all five base values."""
        from owlbear_kanban.engine import VALID_PROOF_BUNDLES  # noqa: PLC0415
        bases = {"skip", "existing", "smoke", "behavioral", "critical"}
        assert bases <= VALID_PROOF_BUNDLES

    def test_valid_proof_bundles_contains_challenge_modifier_variants(self) -> None:
        """AC1: VALID_PROOF_BUNDLES contains base+challenge for every base."""
        from owlbear_kanban.engine import VALID_PROOF_BUNDLES  # noqa: PLC0415
        for base in ("skip", "existing", "smoke", "behavioral", "critical"):
            assert f"{base}+challenge" in VALID_PROOF_BUNDLES, (
                f"Expected '{base}+challenge' in VALID_PROOF_BUNDLES"
            )

    def test_valid_proof_bundles_contains_reader_modifier_variants(self) -> None:
        """AC1: VALID_PROOF_BUNDLES contains base+reader for every base."""
        from owlbear_kanban.engine import VALID_PROOF_BUNDLES  # noqa: PLC0415
        for base in ("skip", "existing", "smoke", "behavioral", "critical"):
            assert f"{base}+reader" in VALID_PROOF_BUNDLES, (
                f"Expected '{base}+reader' in VALID_PROOF_BUNDLES"
            )

    def test_valid_proof_bundles_contains_challenge_reader_modifier_variants(self) -> None:
        """AC1: VALID_PROOF_BUNDLES contains base+challenge+reader for every base."""
        from owlbear_kanban.engine import VALID_PROOF_BUNDLES  # noqa: PLC0415
        for base in ("skip", "existing", "smoke", "behavioral", "critical"):
            assert f"{base}+challenge+reader" in VALID_PROOF_BUNDLES, (
                f"Expected '{base}+challenge+reader' in VALID_PROOF_BUNDLES"
            )


# ---------------------------------------------------------------------------
# AC2 — edit_task ac/add_ac/remove_ac contract + mutual exclusivity
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskAcMutation:
    """AC2: edit_task supports ac (replace), add_ac (append), remove_ac (remove); mutual exclusivity."""

    def test_edit_task_ac_replaces_existing_ac_list(self, tmp_path: Path) -> None:
        """AC2: edit_task(ac=[...]) fully replaces the task's ac list."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "old item"\n')
        task = engine.edit_task("1", ac=["new item 1", "new item 2"])
        assert task.ac == ["new item 1", "new item 2"]

    def test_edit_task_ac_clears_list_when_empty(self, tmp_path: Path) -> None:
        """AC2: edit_task(ac=[]) replaces ac list with empty list."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "old item"\n')
        task = engine.edit_task("1", ac=[])
        assert task.ac == []

    def test_edit_task_add_ac_appends_to_existing_list(self, tmp_path: Path) -> None:
        """AC2: edit_task(add_ac=[...]) appends new items to the existing ac list."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "existing item"\n')
        task = engine.edit_task("1", add_ac=["appended item"])
        assert "existing item" in task.ac
        assert "appended item" in task.ac

    def test_edit_task_remove_ac_removes_exact_match(self, tmp_path: Path) -> None:
        """AC2: edit_task(remove_ac=[...]) removes items matching exactly."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            extra_fields='ac:\n  - "item to keep"\n  - "item to remove"\n',
        )
        task = engine.edit_task("1", remove_ac=["item to remove"])
        assert task.ac == ["item to keep"]

    def test_edit_task_remove_ac_nonexistent_item_is_noop(self, tmp_path: Path) -> None:
        """AC2: remove_ac with item not in ac list leaves the list unchanged."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "kept item"\n')
        task = engine.edit_task("1", remove_ac=["nonexistent"])
        assert task.ac == ["kept item"]

    def test_edit_task_ac_and_add_ac_together_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC2: edit_task with both ac= and add_ac= raises ValidationError(ERR_AC_EXCLUSIVE)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", ac=["item"], add_ac=["other"])
        assert exc_info.value.code == "ERR_AC_EXCLUSIVE"

    def test_edit_task_ac_and_remove_ac_together_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC2: edit_task with both ac= and remove_ac= raises ValidationError(ERR_AC_EXCLUSIVE)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "existing"\n')
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", ac=["item"], remove_ac=["existing"])
        assert exc_info.value.code == "ERR_AC_EXCLUSIVE"


# ---------------------------------------------------------------------------
# AC3 — edit_task add_ac duplicate rejection
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskAddAcDuplicates:
    """AC3: edit_task rejects add_ac items already in task ac with ValidationError(ERR_AC_DUPLICATE)."""

    def test_edit_task_add_ac_duplicate_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC3: add_ac with an item already in task ac raises ValidationError(ERR_AC_DUPLICATE)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "already here"\n')
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", add_ac=["already here"])
        assert exc_info.value.code == "ERR_AC_DUPLICATE"

    def test_edit_task_add_ac_duplicate_error_lists_duplicate_items(
        self, tmp_path: Path
    ) -> None:
        """AC3: ValidationError for duplicate add_ac lists the existing duplicate items."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "dup item"\n')
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", add_ac=["dup item"])
        assert "dup item" in exc_info.value.user_message

    def test_edit_task_add_ac_new_item_is_not_rejected(self, tmp_path: Path) -> None:
        """AC3: add_ac with a genuinely new item is not rejected."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "existing"\n')
        task = engine.edit_task("1", add_ac=["brand new"])
        assert "brand new" in task.ac

    def test_edit_task_add_ac_partial_duplicate_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC3: add_ac with mix of new and duplicate items raises ValidationError."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, extra_fields='ac:\n  - "dup"\n')
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", add_ac=["dup", "new item"])
        assert exc_info.value.code == "ERR_AC_DUPLICATE"


# ---------------------------------------------------------------------------
# AC4 — AC guardrails: max 20 items, 500-char limit
# ---------------------------------------------------------------------------


class TestFromAC_AcGuardrails:
    """AC4: create_task and edit_task enforce max 20 ac items and 500-char item limit."""

    def test_create_task_exactly_20_ac_items_succeeds(self, tmp_path: Path) -> None:
        """AC4: create_task with exactly 20 ac items is accepted (boundary)."""
        engine, _ = _make_engine(tmp_path)
        ac_items = [f"AC{i}: item" for i in range(20)]
        task = engine.create_task(title="T", ac=ac_items)
        assert len(task.ac) == 20

    def test_create_task_21_ac_items_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: create_task with 21 ac items raises ValidationError(ERR_AC_LIMIT)."""
        engine, _ = _make_engine(tmp_path)
        ac_items = [f"AC{i}: item" for i in range(21)]
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task(title="T", ac=ac_items)
        assert exc_info.value.code == "ERR_AC_LIMIT"

    def test_create_task_ac_item_exactly_500_chars_succeeds(
        self, tmp_path: Path
    ) -> None:
        """AC4: create_task with an ac item of exactly 500 chars is accepted (boundary)."""
        engine, _ = _make_engine(tmp_path)
        task = engine.create_task(title="T", ac=["x" * 500])
        assert len(task.ac[0]) == 500

    def test_create_task_ac_item_501_chars_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: create_task with an ac item of 501 chars raises ValidationError(ERR_AC_ITEM_TOO_LONG)."""
        engine, _ = _make_engine(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task(title="T", ac=["x" * 501])
        assert exc_info.value.code == "ERR_AC_ITEM_TOO_LONG"

    def test_edit_task_ac_replace_21_items_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: edit_task(ac=[21 items]) raises ValidationError(ERR_AC_LIMIT)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        ac_items = [f"AC{i}: item" for i in range(21)]
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", ac=ac_items)
        assert exc_info.value.code == "ERR_AC_LIMIT"

    def test_edit_task_add_ac_exceeding_20_total_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: edit_task(add_ac=[...]) that pushes total ac count above 20 raises ValidationError."""
        engine, kanban_dir = _make_engine(tmp_path)
        existing = "\n".join(f'  - "item {i}"' for i in range(19))
        _write_task(kanban_dir, task_id=1, extra_fields=f"ac:\n{existing}\n")
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", add_ac=["item A", "item B"])
        assert exc_info.value.code == "ERR_AC_LIMIT"

    def test_edit_task_ac_item_501_chars_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: edit_task(ac=[item > 500 chars]) raises ValidationError(ERR_AC_ITEM_TOO_LONG)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", ac=["x" * 501])
        assert exc_info.value.code == "ERR_AC_ITEM_TOO_LONG"

    def test_edit_task_add_ac_item_501_chars_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        """AC4: edit_task(add_ac=[item > 500 chars]) raises ValidationError(ERR_AC_ITEM_TOO_LONG)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("1", add_ac=["x" * 501])
        assert exc_info.value.code == "ERR_AC_ITEM_TOO_LONG"


# ---------------------------------------------------------------------------
# AC5 — list_tasks search matches ac items
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksAcSearch:
    """AC5: list_tasks(search=) matches keyword as case-insensitive substring in any ac item."""

    def test_list_tasks_search_matches_ac_item(self, tmp_path: Path) -> None:
        """AC5: task with matching keyword in ac is returned by list_tasks(search=keyword)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="Unrelated title",
            body="Unrelated body.",
            extra_fields='ac:\n  - "implement caching layer"\n',
        )
        results = engine.list_tasks(search="caching")
        assert any(t.id == 1 for t in results)

    def test_list_tasks_search_ac_is_case_insensitive(self, tmp_path: Path) -> None:
        """AC5: ac search is case-insensitive (uppercase keyword matches lowercase ac item)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="Unrelated",
            body="Unrelated body.",
            extra_fields='ac:\n  - "implement OAuth integration"\n',
        )
        results = engine.list_tasks(search="OAUTH")
        assert any(t.id == 1 for t in results)

    def test_list_tasks_search_ac_substring_match(self, tmp_path: Path) -> None:
        """AC5: partial keyword matches substring anywhere in an ac item."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="Unrelated",
            body="Unrelated body.",
            extra_fields='ac:\n  - "must handle authentication errors gracefully"\n',
        )
        results = engine.list_tasks(search="authentication")
        assert any(t.id == 1 for t in results)

    def test_list_tasks_search_ac_does_not_match_title_or_body(
        self, tmp_path: Path
    ) -> None:
        """AC5: search only in ac items returns task; title/body alone don't add to ac match."""
        engine, kanban_dir = _make_engine(tmp_path)
        # Task 1: keyword only in ac
        _write_task(
            kanban_dir,
            task_id=1,
            title="plain title",
            body="plain body",
            extra_fields='ac:\n  - "contains uniquekeyword here"\n',
        )
        # Task 2: keyword only in title (should still match via existing title search)
        _write_task(
            kanban_dir,
            task_id=2,
            title="title with uniquekeyword",
            body="plain body",
        )
        results = engine.list_tasks(search="uniquekeyword")
        ids = {t.id for t in results}
        # Both tasks should match — task 1 via ac, task 2 via title
        assert 1 in ids
        assert 2 in ids

    def test_list_tasks_search_ac_multiple_items_any_match_returns_task(
        self, tmp_path: Path
    ) -> None:
        """AC5: task is returned when keyword matches any one of its ac items."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="Unrelated",
            body="Unrelated body.",
            extra_fields=(
                'ac:\n  - "first AC item"\n  - "second AC item with targetword"\n'
            ),
        )
        results = engine.list_tasks(search="targetword")
        assert any(t.id == 1 for t in results)
