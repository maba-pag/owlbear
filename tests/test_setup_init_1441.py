"""Tests for task #1441: Remove config.yml from setup seed and board initialization.

AC coverage:
  AC-3: setup.init() creates four board directories under .owlbear/kanban/ —
        tasks, archive, decisions/pending, decisions/resolved — using
        Path.mkdir(parents=True, exist_ok=True) after the seed-tree walk,
        without writing config.yml.

All tests in this file MUST FAIL against current code:
  - Current code never creates .owlbear/kanban/decisions/pending or
    .owlbear/kanban/decisions/resolved (no seed file triggers their creation,
    no explicit mkdir call exists).
  - Current code copies seed/.owlbear/kanban/config.yml to the target.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _load_init() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_1441", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def init_module() -> types.ModuleType:
    return _load_init()


# ---------------------------------------------------------------------------
# AC-3 — Board directory creation
# ---------------------------------------------------------------------------


class TestFromAC_BoardDirectoryCreation:
    """AC-3: init() creates tasks, archive, decisions/pending, decisions/resolved
    under .owlbear/kanban/ on a fresh target, without writing config.yml.
    """

    def test_decisions_pending_dir_created_on_fresh_target(self, tmp_path: Path, init_module: types.ModuleType) -> None:
        """decisions/pending directory must exist after init() on a fresh target.

        MUST FAIL: current code never creates .owlbear/kanban/decisions/pending.
        No seed file triggers its creation and no explicit mkdir call exists.
        """
        target = tmp_path / "project"
        target.mkdir()

        init_module.init(target, _REPO_ROOT, interactive=False)

        decisions_pending = target / ".owlbear" / "kanban" / "decisions" / "pending"
        assert decisions_pending.is_dir(), (
            f"init() must create .owlbear/kanban/decisions/pending; directory not found at {decisions_pending}"
        )

    def test_decisions_resolved_dir_created_on_fresh_target(
        self, tmp_path: Path, init_module: types.ModuleType
    ) -> None:
        """decisions/resolved directory must exist after init() on a fresh target.

        MUST FAIL: current code never creates .owlbear/kanban/decisions/resolved.
        No seed file triggers its creation and no explicit mkdir call exists.
        """
        target = tmp_path / "project"
        target.mkdir()

        init_module.init(target, _REPO_ROOT, interactive=False)

        decisions_resolved = target / ".owlbear" / "kanban" / "decisions" / "resolved"
        assert decisions_resolved.is_dir(), (
            f"init() must create .owlbear/kanban/decisions/resolved; directory not found at {decisions_resolved}"
        )

    def test_all_four_board_dirs_exist_after_init(self, tmp_path: Path, init_module: types.ModuleType) -> None:
        """All four board directories must exist after init() on a fresh target.

        MUST FAIL: decisions/pending and decisions/resolved are absent with
        current code. tasks/ and archive/ are created implicitly via seed
        .gitkeep files, but the decisions directories have no such mechanism.
        """
        target = tmp_path / "project"
        target.mkdir()

        init_module.init(target, _REPO_ROOT, interactive=False)

        kanban_root = target / ".owlbear" / "kanban"
        missing = [
            name
            for name in [
                "tasks",
                "archive",
                "decisions/pending",
                "decisions/resolved",
            ]
            if not (kanban_root / name).is_dir()
        ]
        assert not missing, (
            f"init() must create all four board directories under .owlbear/kanban/; missing: {missing!r}"
        )

    def test_config_yml_not_written_to_board_dir(self, tmp_path: Path, init_module: types.ModuleType) -> None:
        """init() must not write config.yml under .owlbear/kanban/.

        MUST FAIL: seed/.owlbear/kanban/config.yml currently exists in the
        seed tree, so init() copies it unconditionally to the target.
        """
        target = tmp_path / "project"
        target.mkdir()

        init_module.init(target, _REPO_ROOT, interactive=False)

        config_yml = target / ".owlbear" / "kanban" / "config.yml"
        assert not config_yml.exists(), (
            f"init() must not write .owlbear/kanban/config.yml (seed file must "
            f"be removed as part of AC-1); found file at {config_yml}"
        )

    def test_board_dirs_created_idempotently(self, tmp_path: Path, init_module: types.ModuleType) -> None:
        """Running init() twice must not error and all four board dirs must exist.

        Verifies that mkdir uses exist_ok=True so a second run does not raise
        FileExistsError.

        MUST FAIL: current code never creates decisions/pending or
        decisions/resolved on the first run; they remain absent on the second run.
        """
        target = tmp_path / "project"
        target.mkdir()

        init_module.init(target, _REPO_ROOT, interactive=False)
        # Second run: existing files must not cause errors (exist_ok=True).
        init_module.init(target, _REPO_ROOT, interactive=False)

        decisions_pending = target / ".owlbear" / "kanban" / "decisions" / "pending"
        decisions_resolved = target / ".owlbear" / "kanban" / "decisions" / "resolved"
        assert decisions_pending.is_dir(), "After idempotent second init(), decisions/pending must still be present"
        assert decisions_resolved.is_dir(), "After idempotent second init(), decisions/resolved must still be present"

    def test_decisions_dirs_created_with_parents(self, tmp_path: Path, init_module: types.ModuleType) -> None:
        """decisions/pending and decisions/resolved are nested and require parents=True.

        When the target has tasks/ and archive/ already seeded but no decisions/
        parent at all, init() must still create both decisions subdirectories.
        This validates that mkdir is called with parents=True, not just mkdir().

        MUST FAIL: current code never creates .owlbear/kanban/decisions/,
        so the nested subdirectories are never created regardless of pre-existing state.
        """
        target = tmp_path / "project"
        target.mkdir()

        # Pre-seed tasks and archive to simulate a partially-initialized board.
        (target / ".owlbear" / "kanban" / "tasks").mkdir(parents=True)
        (target / ".owlbear" / "kanban" / "archive").mkdir(parents=True)
        # Intentionally leave decisions/ absent to verify parents=True is needed.

        init_module.init(target, _REPO_ROOT, interactive=False)

        kanban_root = target / ".owlbear" / "kanban"
        assert (kanban_root / "decisions" / "pending").is_dir(), (
            "init() must create decisions/pending even when decisions/ parent is absent (requires mkdir(parents=True))"
        )
        assert (kanban_root / "decisions" / "resolved").is_dir(), (
            "init() must create decisions/resolved even when decisions/ parent is absent (requires mkdir(parents=True))"
        )
