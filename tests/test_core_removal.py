"""Failing tests for task #1297: P1-01 core removal - delete orchestrator package and
owlbear-project.json infrastructure.

Each test maps to an AC line and is expected to FAIL on the current codebase.
They pass once the builder completes the deletions and edits described in #1297.

AC coverage:
  AC1  — test_orchestrator_dir_absent
  AC2  — test_mock_acp_agent_absent
  AC3  — test_e2e_smoke_absent
  AC4  — test_root_project_json_absent
  AC5  — test_seed_project_json_absent
  AC6  — test_no_serve_orchestrator_in_pyproject, test_no_serve_orchestrator_in_tests_dir
  AC8  — test_allowed_imports_no_owlbear_namespace, test_allowed_imports_no_owlbear_orchestrator
    scope edit — test_write_project_json_not_in_init, test_project_json_not_in_skip_if_exists_rel,
                             test_project_json_dispatch_removed_from_init
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PY = _REPO_ROOT / "setup" / "init.py"
_PKG_BOUNDARY_PY = _REPO_ROOT / "tests" / "test_package_boundary.py"


def _load_init() -> ModuleType:
    """Import setup/init.py as a module; safe because it has an __main__ guard."""
    spec = importlib.util.spec_from_file_location("setup_init_1297", _INIT_PY)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _allowed_imports_keys() -> set[str]:
    """Return the string keys of ALLOWED_IMPORTS in test_package_boundary.py."""
    source = _PKG_BOUNDARY_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        # Handle both plain (ast.Assign) and annotated (ast.AnnAssign) assignments.
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
            if isinstance(target, ast.Name) and target.id == "ALLOWED_IMPORTS" and isinstance(value, ast.Dict):
                return {key.value for key in value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALLOWED_IMPORTS" and isinstance(node.value, ast.Dict):
                    return {
                        key.value
                        for key in node.value.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    }
    return set()


class TestFromAC_CoreRemoval:
    """AC 1-10: orchestrator package and owlbear-project.json infrastructure removed."""

    # ---- AC 1 ---------------------------------------------------------------

    def test_orchestrator_dir_absent(self) -> None:
        """serve/orchestrator/ directory must be deleted."""
        assert not (_REPO_ROOT / "serve" / "orchestrator").exists()

    # ---- AC 2 ---------------------------------------------------------------

    def test_mock_acp_agent_absent(self) -> None:
        """tests/fixtures/mock_acp_agent.py must be deleted."""
        assert not (_REPO_ROOT / "tests" / "fixtures" / "mock_acp_agent.py").exists()

    # ---- AC 3 ---------------------------------------------------------------

    def test_e2e_smoke_absent(self) -> None:
        """.owlbear/scripts/e2e_smoke.py must be deleted."""
        assert not (_REPO_ROOT / ".owlbear" / "scripts" / "e2e_smoke.py").exists()

    # ---- AC 4 ---------------------------------------------------------------

    def test_root_project_json_absent(self) -> None:
        """owlbear-project.json at repo root must be deleted."""
        assert not (_REPO_ROOT / "owlbear-project.json").exists()

    # ---- AC 5 ---------------------------------------------------------------

    def test_seed_project_json_absent(self) -> None:
        """seed/owlbear-project.json must be deleted."""
        assert not (_REPO_ROOT / "seed" / "owlbear-project.json").exists()

    # ---- AC 6: pyproject.toml -----------------------------------------------

    def test_no_serve_orchestrator_in_pyproject(self) -> None:
        """pyproject.toml must not reference serve/orchestrator."""
        text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "serve/orchestrator" not in text

    # ---- AC 6: tests/ -------------------------------------------------------

    def test_no_serve_orchestrator_in_tests_dir(self) -> None:
        """No .py file under tests/ may contain the string 'serve/orchestrator'."""
        # Exclude files that necessarily contain the literal as test-data strings:
        # - this file: contains the string in the scan expression itself
        # - test_dead_code_sweep.py: tests that *other* locations don't reference
        #   serve/orchestrator, so the literal appears in its own assertions/docstrings
        excluded = {
            Path(__file__).resolve(),
            (_REPO_ROOT / "tests" / "test_dead_code_sweep.py").resolve(),
        }
        hits = [
            str(p)
            for p in (_REPO_ROOT / "tests").rglob("*.py")
            if p.resolve() not in excluded and "serve/orchestrator" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"tests/ files still reference serve/orchestrator: {hits}"

    # ---- AC 6: setup/ -------------------------------------------------------

    def test_no_serve_orchestrator_in_setup_dir(self) -> None:
        """No .py file under setup/ may contain the string 'serve/orchestrator'."""
        hits = [
            str(p)
            for p in (_REPO_ROOT / "setup").rglob("*.py")
            if "serve/orchestrator" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"setup/ files still reference serve/orchestrator: {hits}"

    # ---- AC 6: serve/knowledge/ ---------------------------------------------

    def test_no_serve_orchestrator_in_knowledge_dir(self) -> None:
        """No file under serve/knowledge/ may contain the string 'serve/orchestrator'."""
        hits = [
            str(p)
            for p in (_REPO_ROOT / "serve" / "knowledge").rglob("*")
            if p.is_file() and "serve/orchestrator" in p.read_text(encoding="utf-8", errors="ignore")
        ]
        assert hits == [], f"serve/knowledge/ files still reference serve/orchestrator: {hits}"

    # ---- Scope edit: test_package_boundary.py ALLOWED_IMPORTS ---------------

    def test_allowed_imports_no_owlbear_namespace(self) -> None:
        """ALLOWED_IMPORTS must not have a bare 'owlbear' key (co-packaged entry removed)."""
        keys = _allowed_imports_keys()
        assert "owlbear" not in keys

    def test_allowed_imports_no_owlbear_orchestrator(self) -> None:
        """ALLOWED_IMPORTS must not have an 'owlbear_orchestrator' key."""
        keys = _allowed_imports_keys()
        assert "owlbear_orchestrator" not in keys

    # ---- Scope edit: setup/init.py ------------------------------------------

    def test_write_project_json_not_in_init(self) -> None:
        """_write_project_json function must be removed from setup/init.py."""
        mod = _load_init()
        assert not hasattr(mod, "_write_project_json")

    def test_project_json_not_in_skip_if_exists_rel(self) -> None:
        """'owlbear-project.json' must not be in _SKIP_IF_EXISTS_REL."""
        mod = _load_init()
        assert "owlbear-project.json" not in mod._SKIP_IF_EXISTS_REL

    def test_project_json_dispatch_removed_from_init(self) -> None:
        """The owlbear-project.json dispatch block must be removed from setup/init.py."""
        text = _INIT_PY.read_text(encoding="utf-8")
        assert 'rel_posix == "owlbear-project.json"' not in text
