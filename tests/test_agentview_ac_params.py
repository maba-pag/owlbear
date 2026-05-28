"""Tests for AgentView.create_task / edit_task ac and proof_bundle passthrough (#1520).

AC coverage:
  AC1 → TestFromAC_CreateTaskAcProofBundle — create_task accepts ac/proof_bundle;
      returned SingleTaskResponse ac and proof_bundle fields reflect provided values
  AC2 → TestFromAC_EditTaskAcProofBundle — edit_task accepts ac/add_ac/remove_ac/proof_bundle;
         returned task fields reflect the edits
  AC3 → TestFromAC_ShowTaskAcProofBundleBackstop — show_task round-trip via
         AgentView.create_task returns ac and proof_bundle (regression backstop)
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView

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
    entry_status: research
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


def _make_view(base_dir: Path) -> tuple[AgentView, KanbanEngine]:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), engine


# ---------------------------------------------------------------------------
# AC1: AgentView.create_task ac / proof_bundle passthrough
# ---------------------------------------------------------------------------


class TestCreateTaskAcProofBundle:
    """AC1: create_task accepts ac and proof_bundle; returned task reflects provided values."""

    def test_create_task_ac_and_proof_bundle_in_returned_task(self, tmp_path: Path) -> None:
        """AC1 happy: both ac and proof_bundle appear in the returned SingleTaskResponse."""
        view, _ = _make_view(tmp_path)
        result = view.create_task(title="T", ac=["x"], proof_bundle="behavioral")
        assert result.ac == ["x"]
        assert result.proof_bundle == "behavioral"

    def test_create_task_ac_param_only(self, tmp_path: Path) -> None:
        """AC1 happy: ac-only param sets returned task.ac; proof_bundle remains None."""
        view, _ = _make_view(tmp_path)
        result = view.create_task(title="T", ac=["criterion-a"])
        assert result.ac == ["criterion-a"]
        assert result.proof_bundle is None

    def test_create_task_proof_bundle_param_only(self, tmp_path: Path) -> None:
        """AC1 happy: proof_bundle-only param sets returned task.proof_bundle; ac stays empty."""
        view, _ = _make_view(tmp_path)
        result = view.create_task(title="T", proof_bundle="smoke")
        assert result.proof_bundle == "smoke"
        assert result.ac == []

    def test_create_task_multiple_ac_items_all_preserved(self, tmp_path: Path) -> None:
        """AC1 boundary: all ac items are preserved in the returned task."""
        view, _ = _make_view(tmp_path)
        ac_items = ["AC-1: do X", "AC-2: do Y", "AC-3: do Z"]
        result = view.create_task(title="T", ac=ac_items)
        assert result.ac == ac_items

    def test_create_task_empty_ac_list(self, tmp_path: Path) -> None:
        """AC1 edge: empty ac list is accepted; returned task.ac is empty."""
        view, _ = _make_view(tmp_path)
        result = view.create_task(title="T", ac=[])
        assert result.ac == []

    def test_create_task_ac_and_proof_bundle_persisted_on_disk(self, tmp_path: Path) -> None:
        """AC1 edge: ac and proof_bundle are persisted; re-reading via engine returns same values."""
        view, engine = _make_view(tmp_path)
        result = view.create_task(title="T", ac=["persisted-item"], proof_bundle="behavioral")
        task_id = result.id
        stored = engine.show_task(str(task_id))
        assert stored.ac == ["persisted-item"]
        assert stored.proof_bundle == "behavioral"


# ---------------------------------------------------------------------------
# AC2: AgentView.edit_task ac / add_ac / remove_ac / proof_bundle passthrough
# ---------------------------------------------------------------------------


class TestEditTaskAcProofBundle:
    """AC2: edit_task accepts ac, add_ac, remove_ac, proof_bundle; returned task reflects edits."""

    def _seed(self, tmp_path: Path, **engine_kwargs: object) -> tuple[AgentView, KanbanEngine, int]:
        """Create a task directly via engine (bypasses AgentView.create_task). Return view, engine, id."""
        view, engine = _make_view(tmp_path)
        task = engine.create_task(title="Seed", **engine_kwargs)  # type: ignore[arg-type]
        return view, engine, task.id

    def test_edit_task_proof_bundle_sets_field(self, tmp_path: Path) -> None:
        """AC2 happy: proof_bundle='smoke' sets returned task.proof_bundle."""
        view, _, task_id = self._seed(tmp_path)
        result = view.edit_task(task_id, proof_bundle="smoke")
        assert result.proof_bundle == "smoke"

    def test_edit_task_add_ac_appends_item(self, tmp_path: Path) -> None:
        """AC2 happy: add_ac=['y'] appends to returned task.ac."""
        view, _, task_id = self._seed(tmp_path)
        result = view.edit_task(task_id, add_ac=["y"])
        assert "y" in result.ac

    def test_edit_task_ac_replaces_full_list(self, tmp_path: Path) -> None:
        """AC2 happy: ac=['x', 'y'] replaces the existing ac list entirely."""
        view, _, task_id = self._seed(tmp_path, ac=["old"])
        result = view.edit_task(task_id, ac=["x", "y"])
        assert result.ac == ["x", "y"]

    def test_edit_task_remove_ac_removes_item(self, tmp_path: Path) -> None:
        """AC2 edge: remove_ac removes the named item and leaves the rest unchanged."""
        view, _, task_id = self._seed(tmp_path, ac=["x", "y"])
        result = view.edit_task(task_id, remove_ac=["x"])
        assert "x" not in result.ac
        assert "y" in result.ac

    def test_edit_task_add_ac_and_proof_bundle_combined(self, tmp_path: Path) -> None:
        """AC2 edge: add_ac and proof_bundle can be combined in a single edit call."""
        view, _, task_id = self._seed(tmp_path)
        result = view.edit_task(task_id, add_ac=["z"], proof_bundle="critical")
        assert "z" in result.ac
        assert result.proof_bundle == "critical"

    def test_edit_task_proof_bundle_overwrites_previous_value(self, tmp_path: Path) -> None:
        """AC2 boundary: setting proof_bundle again overwrites the previous value."""
        view, _, task_id = self._seed(tmp_path, proof_bundle="smoke")
        result = view.edit_task(task_id, proof_bundle="behavioral")
        assert result.proof_bundle == "behavioral"


# ---------------------------------------------------------------------------
# AC3: show_task regression backstop — ac + proof_bundle visible end-to-end
# ---------------------------------------------------------------------------


class TestShowTaskAcProofBundleBackstop:
    """AC3: show_task response includes ac and proof_bundle set via AgentView.create_task."""

    def test_show_task_reflects_ac_and_proof_bundle_from_create(self, tmp_path: Path) -> None:
        """AC3: create_task with ac/proof_bundle → show_task returns same values."""
        view, _ = _make_view(tmp_path)
        created = view.create_task(title="T", ac=["AC1 line"], proof_bundle="behavioral")
        shown = view.show_task(created.id)
        assert shown.ac == ["AC1 line"]
        assert shown.proof_bundle == "behavioral"
