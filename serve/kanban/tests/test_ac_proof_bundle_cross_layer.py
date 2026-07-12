"""Durable consolidation tests: ac / proof_bundle cross-layer interactions.

Backstop for #1514 feature (structured task specification).
Covers engine-AgentView and migration-engine integration paths; complements
single-layer unit tests in #1517-#1523.

AC1 → TestEngineWriteAgentViewRead
AC2 → TestEngineMutateAgentViewRead
AC3 → TestMigrationEngineRead
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import AgentView, KanbanEngine
from owlbear_kanban.migrate import _migrate_proof_bundle_field

# ---------------------------------------------------------------------------
# Shared board configuration
# ---------------------------------------------------------------------------

_BASE_CONFIG = "next_id: 1\n"


def _make_board(base_dir: Path) -> tuple[AgentView, KanbanEngine]:
    """Set up a minimal board and return (AgentView, KanbanEngine)."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), engine


# ---------------------------------------------------------------------------
# AC1 — engine-write → AgentView-read
# ---------------------------------------------------------------------------


class TestEngineWriteAgentViewRead:
    """AC1: tasks written via engine.create_task are readable by AgentView.show_task
    with ac and proof_bundle values intact."""

    def test_show_task_returns_ac_and_proof_bundle_from_engine_create(self, tmp_path: Path) -> None:
        """AC1 happy: engine.create_task ac/proof_bundle visible via AgentView.show_task."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=["criterion1"], proof_bundle="behavioral")
        response = view.show_task(task.id)
        assert response.ac == ["criterion1"]
        assert response.proof_bundle == "behavioral"

    def test_show_task_ac_only_proof_bundle_is_none(self, tmp_path: Path) -> None:
        """AC1 happy: engine.create_task ac only; show_task proof_bundle is None."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=["criterion1"])
        response = view.show_task(task.id)
        assert response.ac == ["criterion1"]
        assert response.proof_bundle is None

    def test_show_task_proof_bundle_only_ac_is_empty(self, tmp_path: Path) -> None:
        """AC1 happy: engine.create_task proof_bundle only; show_task ac is empty list."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", proof_bundle="behavioral")
        response = view.show_task(task.id)
        assert response.proof_bundle == "behavioral"
        assert response.ac == []

    def test_show_task_empty_ac_list_reflects_empty(self, tmp_path: Path) -> None:
        """AC1 edge: engine.create_task with empty ac list; show_task returns []."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=[])
        response = view.show_task(task.id)
        assert response.ac == []

    def test_show_task_multiple_ac_items_preserved_in_order(self, tmp_path: Path) -> None:
        """AC1 boundary: multiple ac items are all preserved and in original order."""
        ac_items = ["line-A", "line-B", "line-C"]
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=ac_items)
        response = view.show_task(task.id)
        assert response.ac == ac_items


# ---------------------------------------------------------------------------
# AC2 — engine-mutation → AgentView-read (append semantics)
# ---------------------------------------------------------------------------


class TestEngineMutateAgentViewRead:
    """AC2: engine.edit_task add_ac / proof_bundle mutations visible via AgentView.show_task
    with correct append semantics."""

    def test_add_ac_and_proof_bundle_mutation_visible_via_show_task(self, tmp_path: Path) -> None:
        """AC2 happy (exact AC2 assertion): after add_ac=['criterion2'] + proof_bundle='smoke'
        on a task with ac=['criterion1'], show_task returns ac==['criterion1','criterion2']
        and proof_bundle=='smoke'."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=["criterion1"])
        engine.edit_task(str(task.id), add_ac=["criterion2"], proof_bundle="smoke")
        response = view.show_task(task.id)
        assert response.ac == ["criterion1", "criterion2"]
        assert response.proof_bundle == "smoke"

    def test_add_ac_appends_without_losing_original(self, tmp_path: Path) -> None:
        """AC2 happy: add_ac preserves prior item; original criterion1 present after edit."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=["criterion1"])
        engine.edit_task(str(task.id), add_ac=["criterion2"], proof_bundle="smoke")
        response = view.show_task(task.id)
        assert "criterion1" in response.ac

    def test_proof_bundle_none_to_smoke_via_edit(self, tmp_path: Path) -> None:
        """AC2 edge: proof_bundle transitions from None to 'smoke' after edit_task."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", ac=["criterion1"])
        assert task.proof_bundle is None
        engine.edit_task(str(task.id), proof_bundle="smoke")
        response = view.show_task(task.id)
        assert response.proof_bundle == "smoke"

    def test_proof_bundle_behavioral_to_smoke_via_edit(self, tmp_path: Path) -> None:
        """AC2 boundary: proof_bundle overwritten from 'behavioral' to 'smoke'."""
        _, engine = _make_board(tmp_path)
        view = AgentView(engine)
        task = engine.create_task(title="T", proof_bundle="behavioral")
        engine.edit_task(str(task.id), proof_bundle="smoke")
        response = view.show_task(task.id)
        assert response.proof_bundle == "smoke"


# ---------------------------------------------------------------------------
# AC3 — migration → engine-read
# ---------------------------------------------------------------------------


def _write_task_file(
    kanban_dir: Path,
    task_id: int,
    *,
    frontmatter_extra: str = "",
    body: str = "",
    filename_slug: str = "task",
) -> Path:
    """Write a minimal valid task file into kanban_dir/tasks/."""
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    path = tasks_dir / f"{task_id}-{filename_slug}.md"
    fm = (
        f"id: {task_id}\n"
        f"title: Fixture Task\n"
        f"status: shape\n"
        f"priority: medium\n"
        f"created: '2026-01-01T00:00:00+00:00'\n"
        f"updated: '2026-01-01T00:00:00+00:00'\n"
        f"tags: []\n"
    )
    if frontmatter_extra:
        fm += frontmatter_extra.rstrip("\n") + "\n"
    content = f"---\n{fm}---\n{body}"
    path.write_text(content, encoding="utf-8")
    return path


def _make_migration_board(base_dir: Path) -> Path:
    """Create a board directory for migration tests; return kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


class TestMigrationEngineRead:
    """AC3: after _migrate_proof_bundle_field extracts 'Proof bundle: critical' from body,
    engine.show_task returns proof_bundle=='critical' and body does not contain the line."""

    def test_engine_show_task_returns_proof_bundle_after_migration(self, tmp_path: Path) -> None:
        """AC3 happy: after migration, engine.show_task proof_bundle == 'critical'."""
        kanban_dir = _make_migration_board(tmp_path)
        body = "Some notes.\nProof bundle: critical\nMore text.\n"
        path = _write_task_file(kanban_dir, 100, body=body)
        status, reason = _migrate_proof_bundle_field(path)
        assert status == "migrated", reason
        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.show_task("100")
        assert task.proof_bundle == "critical"

    def test_engine_show_task_body_has_no_proof_bundle_line_after_migration(self, tmp_path: Path) -> None:
        """AC3 happy: after migration, task.body does not contain 'Proof bundle: critical'."""
        kanban_dir = _make_migration_board(tmp_path)
        body = "Some notes.\nProof bundle: critical\nMore text.\n"
        path = _write_task_file(kanban_dir, 101, body=body)
        _migrate_proof_bundle_field(path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.show_task("101")
        assert "Proof bundle: critical" not in (task.body or "")

    def test_engine_body_other_content_preserved_after_migration(self, tmp_path: Path) -> None:
        """AC3 edge: body content before and after Proof bundle: line is preserved."""
        kanban_dir = _make_migration_board(tmp_path)
        body = "Before content.\nProof bundle: critical\nAfter content.\n"
        path = _write_task_file(kanban_dir, 102, body=body)
        _migrate_proof_bundle_field(path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.show_task("102")
        assert "Before content." in (task.body or "")
        assert "After content." in (task.body or "")

    def test_single_occurrence_constraint_only_one_proof_bundle_line_in_fixture(self, tmp_path: Path) -> None:
        """AC3 boundary: fixture with exactly one Proof bundle: line; engine reads
        'critical' and body has no remaining Proof bundle: line."""
        kanban_dir = _make_migration_board(tmp_path)
        body = "Proof bundle: critical\n"
        path = _write_task_file(kanban_dir, 103, body=body)
        _migrate_proof_bundle_field(path)
        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.show_task("103")
        assert task.proof_bundle == "critical"
        remaining_body = task.body or ""
        proof_bundle_lines = [line for line in remaining_body.splitlines() if "Proof bundle:" in line]
        assert proof_bundle_lines == []
