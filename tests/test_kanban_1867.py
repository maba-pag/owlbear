from __future__ import annotations

"""Tests for task #1867 — Kanban: promote atomic_write to __all__ exports.

AC:
- AC1: "atomic_write" is a member of owlbear_kanban.__init__.__all__
- AC2: from owlbear_kanban import atomic_write resolves to the same callable
       as from owlbear_kanban.storage_io import atomic_write
- AC3: No changes to pyproject.toml [project.dependencies] or
       [tool.uv.sources] sections (regression guard)

Proof bundle: smoke — one test per AC line.
"""

import importlib
import pathlib

import tomllib


class TestFromAC_AtomicWriteExport:
    """Smoke tests derived from AC for task #1867."""

    # --- AC1: atomic_write present in __all__ ---

    def test_atomic_write_in_dunder_all(self) -> None:
        """AC1: 'atomic_write' must appear in owlbear_kanban.__all__."""
        import owlbear_kanban

        assert "atomic_write" in owlbear_kanban.__all__

    # --- AC2: resolves to the same callable as the submodule import ---

    def test_atomic_write_same_callable_as_storage_io(self) -> None:
        """AC2: atomic_write imported from package root is the same object
        as the one imported directly from owlbear_kanban.storage_io."""
        pkg = importlib.import_module("owlbear_kanban")
        submod = importlib.import_module("owlbear_kanban.storage_io")

        pkg_fn = getattr(pkg, "atomic_write", None)
        assert pkg_fn is not None, "atomic_write not found on owlbear_kanban"
        assert pkg_fn is submod.atomic_write

    # --- AC3: regression guard — no pyproject.toml dependency changes ---

    def test_kanban_pyproject_dependencies_unchanged(self) -> None:
        """AC3 regression guard: kanban pyproject.toml [project.dependencies]
        must not gain new entries relative to the pre-task baseline."""
        pyproject_path = (
            pathlib.Path(__file__).parent.parent
            / "serve"
            / "kanban"
            / "pyproject.toml"
        )
        with pyproject_path.open("rb") as fh:
            data = tomllib.load(fh)

        deps: list[str] = data["project"]["dependencies"]
        baseline = {
            "pydantic>=2.13.4",
            "ruamel.yaml>=0.19.1",
            "pyyaml>=6.0.3",
            "markdown-it-py>=4.2.0",
        }
        assert set(deps) == baseline, (
            f"pyproject.toml [project.dependencies] changed from baseline.\n"
            f"Expected: {sorted(baseline)}\n"
            f"Got:      {sorted(deps)}"
        )
        # [tool.uv.sources] must not exist in kanban's pyproject.toml
        assert "uv" not in data.get("tool", {}), (
            "[tool.uv.sources] must not be added to serve/kanban/pyproject.toml"
        )
