"""Failing tests for task #308: Add strictyaml to knowledge package dependencies.

AC:
  1. strictyaml>=1.7 added to [project.dependencies] in packages/knowledge/pyproject.toml
  2. uv lock updated (owlbear-knowledge entry must reflect the new dep)
  3. import strictyaml works in package context (declared as runtime dep in metadata)

All tests fail in RED — strictyaml is not yet in packages/knowledge/pyproject.toml.
"""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).parent.parent
_KNOWLEDGE_PYPROJECT = _WORKSPACE_ROOT / "serve" / "knowledge" / "pyproject.toml"
_UV_LOCK = _WORKSPACE_ROOT / "uv.lock"
_PACKAGE_NAME = "owlbear-knowledge"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_pyproject() -> dict:
    return tomllib.loads(_KNOWLEDGE_PYPROJECT.read_text(encoding="utf-8"))


def _load_lock() -> dict:
    return tomllib.loads(_UV_LOCK.read_text(encoding="utf-8"))


def _find_lock_package(lock: dict, name: str) -> dict:
    packages = lock["package"]
    return next(p for p in packages if p["name"] == name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_StrictYAMLDependency:
    """Contract tests for #308: strictyaml runtime dep for owlbear-knowledge."""

    # -- AC 1: strictyaml>=1.7 in [project.dependencies] --

    def test_pyproject_has_strictyaml_in_project_dependencies(self) -> None:
        """[project.dependencies] in packages/knowledge/pyproject.toml must include strictyaml."""
        data = _load_pyproject()
        deps: list[str] = data["project"]["dependencies"]
        assert any("strictyaml" in dep for dep in deps), (
            f"strictyaml not found in [project.dependencies]; got: {deps}"
        )

    def test_pyproject_strictyaml_version_spec_gte_1_7(self) -> None:
        """The strictyaml entry must specify >=1.7 (not an exact pin or different floor)."""
        data = _load_pyproject()
        deps: list[str] = data["project"]["dependencies"]
        strictyaml_entries = [d for d in deps if "strictyaml" in d]
        assert len(strictyaml_entries) == 1, (
            f"Expected exactly 1 strictyaml entry, got {strictyaml_entries}"
        )
        assert ">=1.7" in strictyaml_entries[0], (
            f"Version spec must be >=1.7, got: {strictyaml_entries[0]!r}"
        )

    def test_pyproject_strictyaml_uses_gte_operator_not_exact_pin(self) -> None:
        """The strictyaml version specifier must use >= (not ==), to avoid over-pinning."""
        data = _load_pyproject()
        deps: list[str] = data["project"]["dependencies"]
        strictyaml_entries = [d for d in deps if "strictyaml" in d]
        assert strictyaml_entries, "strictyaml not in [project.dependencies]"
        entry = strictyaml_entries[0]
        # Must not be an exact pin
        assert "==" not in entry, f"Must use >= not ==, got: {entry!r}"
        # Must have a lower-bound operator
        assert ">=" in entry, f"Must use >= operator, got: {entry!r}"

    # -- AC 2: uv lock updated --

    def test_lock_owlbear_knowledge_runtime_deps_include_strictyaml(self) -> None:
        """uv.lock:owlbear-knowledge.dependencies must include {name: strictyaml}."""
        lock = _load_lock()
        pkg = _find_lock_package(lock, _PACKAGE_NAME)
        runtime_dep_names = [d["name"] for d in pkg.get("dependencies", [])]
        assert "strictyaml" in runtime_dep_names, (
            f"strictyaml missing from owlbear-knowledge lock deps; got: {runtime_dep_names}"
        )

    def test_lock_owlbear_knowledge_metadata_requires_dist_includes_strictyaml(self) -> None:
        """uv.lock:owlbear-knowledge.metadata.requires-dist must have a strictyaml entry without an extras marker."""
        lock = _load_lock()
        pkg = _find_lock_package(lock, _PACKAGE_NAME)
        requires_dist: list[dict] = pkg["metadata"]["requires-dist"]
        # Find unconditional strictyaml entries (no extras marker)
        runtime_entries = [
            r for r in requires_dist
            if r["name"] == "strictyaml" and "marker" not in r
        ]
        assert len(runtime_entries) >= 1, (
            "strictyaml must appear in owlbear-knowledge metadata.requires-dist without a marker"
        )

    def test_lock_owlbear_knowledge_metadata_strictyaml_version_spec(self) -> None:
        """uv.lock strictyaml entry for owlbear-knowledge must carry specifier >=1.7."""
        lock = _load_lock()
        pkg = _find_lock_package(lock, _PACKAGE_NAME)
        requires_dist: list[dict] = pkg["metadata"]["requires-dist"]
        runtime_entries = [
            r for r in requires_dist
            if r["name"] == "strictyaml" and "marker" not in r
        ]
        assert runtime_entries, "strictyaml runtime entry missing from lock metadata"
        assert runtime_entries[0].get("specifier") == ">=1.7", (
            f"Expected specifier '>=1.7', got {runtime_entries[0].get('specifier')!r}"
        )

    # -- AC 3: import strictyaml in package context (declared as runtime dep) --

    def test_installed_package_metadata_declares_strictyaml_runtime_dep(self) -> None:
        """importlib.metadata.requires('owlbear-knowledge') must include strictyaml as a runtime dep."""
        reqs = importlib.metadata.requires(_PACKAGE_NAME) or []
        # Runtime deps: lines without 'extra ==' conditional
        runtime_reqs = [r for r in reqs if "extra ==" not in r]
        assert any("strictyaml" in r for r in runtime_reqs), (
            f"strictyaml not in owlbear-knowledge runtime requirements; "
            f"runtime requires: {runtime_reqs}"
        )

    def test_installed_package_metadata_strictyaml_version_constraint(self) -> None:
        """The strictyaml requirement in package metadata must carry >=1.7 constraint."""
        reqs = importlib.metadata.requires(_PACKAGE_NAME) or []
        strictyaml_reqs = [r for r in reqs if "strictyaml" in r and "extra ==" not in r]
        assert len(strictyaml_reqs) == 1, (
            f"Expected exactly 1 runtime strictyaml requirement, got: {strictyaml_reqs}"
        )
        assert ">=1.7" in strictyaml_reqs[0], (
            f"Version constraint >=1.7 missing from: {strictyaml_reqs[0]!r}"
        )
