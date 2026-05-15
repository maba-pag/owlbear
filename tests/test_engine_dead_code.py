from __future__ import annotations

# --- merged from tests/test_engine_dead_code_1112.py ---
"""Structural-proof regression guards for dead-code removal in engine.py (task #1112).

AC1: Six dict-status ``isinstance`` branches removed from five methods.
AC2: ``# pragma: no cover`` added to the ``sys.platform == "win32"`` line.
AC4: ``_status_rank()`` simplified to a single dict comprehension.

These are regression guards: they prove the structural properties that the builder
was tasked to establish and will FAIL if the dead code is ever re-introduced.
They also include behavioural runtime checks that exercise each affected code path
with a list[str] config — the only form that can reach these methods post-normalise.

Note (retry context): the implementation was already complete when these tests were
added (reviewer FAIL citing missing task-owned structural proof). All tests are
expected to pass immediately; they serve as permanent regression anchors.
"""


import ast
import inspect
import re
from pathlib import Path

import pytest

import owlbear_kanban.engine as _engine_mod
from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Engine source helpers
# ---------------------------------------------------------------------------

_ENGINE_PATH = Path(inspect.getfile(_engine_mod))
_ENGINE_SOURCE = _ENGINE_PATH.read_text(encoding="utf-8")
_ENGINE_LINES = _ENGINE_SOURCE.splitlines()
_ENGINE_TREE = ast.parse(_ENGINE_SOURCE)


def _class_method_source(method_name: str, class_name: str = "KanbanEngine") -> str:
    """Return the source text of *method_name* in *class_name*."""
    for node in ast.walk(_ENGINE_TREE):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return "\n".join(_ENGINE_LINES[item.lineno - 1 : item.end_lineno])
    raise AssertionError(f"{class_name}.{method_name} not found in engine.py")


def _class_method_ast(
    method_name: str, class_name: str = "KanbanEngine"
) -> ast.FunctionDef:
    """Return the AST node for *method_name* in *class_name*."""
    for node in ast.walk(_ENGINE_TREE):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"{class_name}.{method_name} not found in AST")


# ---------------------------------------------------------------------------
# Board / fixture helpers (mirrors test_engine_coverage_1113.py conventions)
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
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
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
Body.
"""


def _make_board(base_dir: Path) -> Path:
    board = base_dir / "board"
    board.mkdir(parents=True, exist_ok=True)
    (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board / "tasks").mkdir(exist_ok=True)
    (board / "archive").mkdir(exist_ok=True)
    return board


def _write_task(
    board: Path,
    *,
    task_id: int,
    title: str = "Task",
    status: str = "todo",
) -> Path:
    path = board / "tasks" / f"{task_id}-task.md"
    path.write_text(
        _TASK_TMPL.format(task_id=task_id, title=title, status=status),
        encoding="utf-8",
    )
    return path


# ===========================================================================
# AC1 — Structural: all 6 dict-status isinstance branches removed
# ===========================================================================

_DICT_STATUS_ISINSTANCE_PATTERN = re.compile(
    r"isinstance\s*\([^)]*,\s*(?:list\[dict\]|dict)\s*\)"
)

_DICT_FIRST_ISINSTANCE_PATTERN = re.compile(r"isinstance\s*\(\s*\w+\s*,\s*dict\s*\)")


class TestFromAC_DictStatusBranchRemoval:
    """AC1: All 6 dead dict-status isinstance branches removed from engine.py.

    The branches were unreachable because ``BoardConfig._normalise_legacy``
    converts any legacy ``list[dict]`` statuses to ``list[str]`` before field
    assignment — so the isinstance guards in the engine were provably dead.

    One test per affected method; ``_apply_outcome`` covers both branches (5 and 6).
    """

    def test_status_rank_has_no_isinstance_check(self) -> None:
        """_status_rank must not contain any isinstance check after dead-code removal."""
        src = _class_method_source("_status_rank")
        assert "isinstance" not in src, (
            "_status_rank still contains an isinstance check — "
            "dict-status dead branch (branch 1) not removed"
        )

    def test_valid_transitions_has_no_isinstance_check(self) -> None:
        """valid_transitions must not contain an isinstance check."""
        src = _class_method_source("valid_transitions")
        assert "isinstance" not in src, (
            "valid_transitions still contains an isinstance check — "
            "dict-status dead branch (branch 2) not removed"
        )

    def test_edit_task_has_no_dict_isinstance_on_statuses(self) -> None:
        """edit_task must not guard valid_statuses with an isinstance(…, dict) check."""
        src = _class_method_source("edit_task")
        # The dead branch pattern checked isinstance(first, dict) on statuses.
        assert not _DICT_FIRST_ISINSTANCE_PATTERN.search(src), (
            "edit_task still contains an isinstance(…, dict) check — "
            "dict-status dead branch (branch 3) not removed"
        )

    def test_move_task_has_no_dict_isinstance_on_statuses(self) -> None:
        """move_task must not guard valid_statuses with an isinstance(…, dict) check."""
        src = _class_method_source("move_task")
        assert not _DICT_FIRST_ISINSTANCE_PATTERN.search(src), (
            "move_task still contains an isinstance(…, dict) check — "
            "dict-status dead branch (branch 4) not removed"
        )

    def test_apply_outcome_has_no_dict_isinstance_check(self) -> None:
        """_apply_outcome must not contain any isinstance(…, dict) guard.

        This covers both branches 5 (original list) and 6 (success-path ternary)
        that the architect identified in the Architecture Review correction.
        """
        src = _class_method_source("_apply_outcome")
        assert not _DICT_FIRST_ISINSTANCE_PATTERN.search(src), (
            "_apply_outcome still contains an isinstance(…, dict) check — "
            "dict-status dead branches (branches 5 and/or 6) not removed"
        )

    def test_status_rank_has_no_dot_get_call(self) -> None:
        """_status_rank must not use .get() — that was part of the dead dict-key branch."""
        src = _class_method_source("_status_rank")
        assert ".get(" not in src, (
            "_status_rank still calls .get() — suggests dict-status branch remains"
        )


# ===========================================================================
# AC4 — Structural: _status_rank simplified to single dict comprehension
# ===========================================================================


class TestFromAC_StatusRankSimplification:
    """AC4: _status_rank() simplified to a dict comprehension with no dead branching.

    The AC states "simplifies to single-line dict comprehension"; the builder may
    retain a local variable assignment for readability.  What must hold is:
    - The method body contains no ``if`` branching (no dead dict-status guard).
    - The return value is a DictComp.
    - enumerate() is used for correct index-keyed mapping.
    """

    def test_status_rank_body_has_no_if_branching(self) -> None:
        """_status_rank must contain no ``if`` statement — the dead dict-status branch removed."""
        node = _class_method_ast("_status_rank")
        has_if = any(isinstance(stmt, ast.If) for stmt in ast.walk(node))
        assert not has_if, (
            "_status_rank still contains an if statement — "
            "dead dict-status branch (branch 1) may not have been fully removed"
        )

    def test_status_rank_return_value_is_dict_comprehension(self) -> None:
        """The Return value in _status_rank must be a DictComp, not a conditional or dict."""
        node = _class_method_ast("_status_rank")
        return_node = next(
            (stmt for stmt in node.body if isinstance(stmt, ast.Return)), None
        )
        assert return_node is not None, "_status_rank has no Return statement"
        assert isinstance(return_node.value, ast.DictComp), (
            f"_status_rank returns a {type(return_node.value).__name__}; expected DictComp. "
            "AC4 simplification to a dict comprehension was not applied."
        )

    def test_status_rank_comprehension_uses_enumerate(self) -> None:
        """The dict comprehension must iterate via enumerate() for index-keyed output."""
        src = _class_method_source("_status_rank")
        assert "enumerate" in src, (
            "_status_rank dict comprehension does not call enumerate() — "
            "index-based rank mapping will be incorrect without it"
        )


# ===========================================================================
# AC1 + AC4 — Behavioural: runtime proof with list[str] config
# ===========================================================================


class TestFromAC_StrStatusBehaviouralContracts:
    """Runtime proof that all five affected methods work correctly with list[str] statuses.

    These tests exercise the simplified code paths end-to-end and confirm that
    removing the dead dict-status branches did not alter observable behaviour.
    """

    def test_list_tasks_sorted_by_status_respects_config_order(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(sort='status') must order tasks by their index in config.statuses."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        _write_task(board, task_id=2, status="todo")
        _write_task(board, task_id=3, status="research")
        engine = KanbanEngine(board, activity_log=False)

        tasks = engine.list_tasks(sort="status")
        returned_statuses = [t.status for t in tasks]

        config_order = [
            "research",
            "backlog",
            "todo",
            "in-progress",
            "review",
            "docs",
            "done",
        ]
        expected_order = sorted(returned_statuses, key=config_order.index)
        assert returned_statuses == expected_order, (
            f"list_tasks(sort='status') returned {returned_statuses!r}; "
            f"expected config order {expected_order!r}. "
            "_status_rank() may not be returning a correct str→int mapping."
        )

    def test_valid_transitions_returns_all_statuses_except_current(
        self, tmp_path: Path
    ) -> None:
        """valid_transitions('todo') must return every configured status except 'todo'."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)

        result = engine.valid_transitions("todo")
        expected = {"research", "backlog", "in-progress", "review", "docs", "done"}
        assert result == expected, (
            f"valid_transitions('todo') returned {result!r}; expected {expected!r}"
        )

    def test_valid_transitions_raises_for_unknown_status(self, tmp_path: Path) -> None:
        """valid_transitions must raise ValueError for a status absent from config."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.valid_transitions("dict-shaped-nonsense")

    def test_edit_task_rejects_invalid_status_with_value_error(
        self, tmp_path: Path
    ) -> None:
        """edit_task must reject a status not in config.statuses with ValueError.

        This confirms the valid_statuses check in edit_task uses set(list[str])
        with no dead dict-status branch interfering.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.edit_task("1", status="not-a-configured-status")

    def test_move_task_rejects_invalid_status_with_value_error(
        self, tmp_path: Path
    ) -> None:
        """move_task must reject a status not in config.statuses with ValueError."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.move_task("1", "not-in-config")

    def test_apply_outcome_success_advances_to_next_status(
        self, tmp_path: Path
    ) -> None:
        """end_work(outcome='success') must advance status to the next in config sequence.

        Exercises _apply_outcome's success branch which uses list(statuses).index()
        — the simplified version with no dict-status isinstance guard (branches 5+6).
        config order: …, todo (idx 2), in-progress (idx 3), …
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.end_work("1", note="advancing", outcome="success")
        assert result.status == "in-progress", (
            f"end_work(success) from 'todo' expected 'in-progress', got {result.status!r}. "
            "_apply_outcome success branch may have a dict-status regression."
        )

    def test_apply_outcome_success_from_last_status_archives_task(
        self, tmp_path: Path
    ) -> None:
        """end_work(outcome='success') from the final configured status must archive the task.

        This exercises the boundary path in _apply_outcome where
        ``current_idx == len(statuses) - 1`` triggers archival.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.end_work("1", note="completing", outcome="success")
        assert result.status == "archived", (
            f"end_work(success) from 'done' (last status) expected 'archived', "
            f"got {result.status!r}."
        )
        # Task file must have moved to archive directory
        archive_path = board / "archive" / "1-task.md"
        assert archive_path.exists(), (
            "Task file was not moved to archive/ after success from final status"
        )


# --- merged from tests/test_engine_dead_code_1204.py ---
"""Tests for task #1204 — Remove _validate_engine_config; trust model validator.

AC1 (td:1): _validate_engine_config function deleted from engine.py.

AC5 (td:1): BoardConfig._validate_semantics still rejects invalid configs.
  — Covered by TestFromAC_ValidateSemanticsStillRejects below (retry cycle:
    reviewer required direct executable proof replacing the false reference to
    the non-existent TestFromAC_BoardConfigSemanticValidation class).
"""


import importlib
import sys

import pytest


class TestFromAC_RemoveValidateEngineConfig:
    """AC1: _validate_engine_config must not exist in owlbear_kanban.engine after deletion."""

    def _fresh_engine_module(self):  # type: ignore[return]
        """Reload engine module to defeat any cached import of the function."""
        mod_name = "owlbear_kanban.engine"
        # Ensure a clean import from disk, not from sys.modules cache.
        saved = sys.modules.pop(mod_name, None)
        try:
            return importlib.import_module(mod_name)
        finally:
            if saved is not None:
                sys.modules[mod_name] = saved

    def test_function_not_in_engine_module(self) -> None:
        """_validate_engine_config must not be a module-level attribute of owlbear_kanban.engine."""
        import owlbear_kanban.engine as engine_mod

        assert not hasattr(engine_mod, "_validate_engine_config"), (
            "_validate_engine_config still present in owlbear_kanban.engine — "
            "function must be deleted (task #1204)"
        )

    def test_function_not_importable_from_engine(self) -> None:
        """Direct import of _validate_engine_config from owlbear_kanban.engine must raise ImportError."""
        with pytest.raises(ImportError):
            from owlbear_kanban.engine import _validate_engine_config  # noqa: F401


# ---------------------------------------------------------------------------
# AC5 — BoardConfig._validate_semantics still rejects invalid configurations
# ---------------------------------------------------------------------------

# Minimal valid flat-key dict (no grouped sub-model instances) used as a base
# for each invalid variant.  Flat keys avoid the "mixing" branch in
# _normalise_legacy that would raise ERR_INVALID_STATUS before _validate_semantics runs.
_VALID_BASE: dict = {
    "statuses": ["research", "done"],
    "priorities": ["low"],
    "entry_status": "research",
    "terminal_status": "done",
    "claim_timeout": "1h",
}


class TestFromAC_ValidateSemanticsStillRejects:
    """AC5: BoardConfig._validate_semantics rejects all listed invalid configs.

    Proof that the model-level semantic validator still enforces the same
    invariants that _validate_engine_config used to check — empty statuses,
    empty priorities, invalid entry_status, invalid terminal_status, invalid
    claim_timeout, non-list agent_compatibility, asymmetric agent_compatibility.

    All tests use BoardConfig.model_validate() with flat-key dicts so that
    _normalise_legacy routes through the non-grouped path, leaving
    _validate_semantics as the sole gate under test.
    """

    def test_empty_statuses_raises(self) -> None:
        """Empty statuses list must be rejected with ERR_INVALID_STATUS."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "statuses": []}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_empty_priorities_raises(self) -> None:
        """Empty priorities list must be rejected with ERR_INVALID_PRIORITY."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "priorities": []}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_PRIORITY"

    def test_invalid_entry_status_raises(self) -> None:
        """entry_status not in statuses must be rejected with ERR_ENTRY_STATUS_INVALID."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "entry_status": "nonexistent"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_invalid_terminal_status_raises(self) -> None:
        """terminal_status != statuses[-1] must be rejected with ERR_TERMINAL_STATUS_INVALID."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        # "research" is in statuses but is not the last element
        cfg = {**_VALID_BASE, "terminal_status": "research"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_invalid_claim_timeout_raises(self) -> None:
        """Unparseable claim_timeout must be rejected with ERR_INVALID_CLAIM_TIMEOUT."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "claim_timeout": "not-a-duration"}
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(cfg)
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_non_list_agent_compatibility_raises(self) -> None:
        """agent_compatibility value that is not a list must be rejected."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        cfg = {**_VALID_BASE, "agent_compatibility": {"agent-a": "should-be-a-list"}}
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(cfg)

    def test_asymmetric_agent_compatibility_raises(self) -> None:
        """One-sided agent_compatibility entry must be rejected."""
        from owlbear_kanban.models import BoardConfig, ConfigError

        # agent-a lists agent-b as compatible but agent-b has no entry at all
        cfg = {**_VALID_BASE, "agent_compatibility": {"agent-a": ["agent-b"]}}
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(cfg)
