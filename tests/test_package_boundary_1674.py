"""Retry gap-fill for #1674: assert ALLOWED_IMPORTS exactly matches manifests.

Reviewer finding: the existing TestFromAC_AllowedImportsSchema tests only verify
schema shape and key coverage.  Extra entries in an allowed set would leave the
suite green if no source file happened to import them.  These tests close the
gap by parsing each package's pyproject.toml and asserting exact set equality
with the corresponding ALLOWED_IMPORTS entry.

AC lines targeted:
  AC1 — ALLOWED_IMPORTS["owlbear_memory"] == set()
  AC2 — ALLOWED_IMPORTS["owlbear_mcp_memory"] == {"owlbear_memory"}
  AC3 — ALLOWED_IMPORTS["owlbear_cockpit"] == {"owlbear_kanban", "owlbear_memory"}
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from tests.test_package_boundary import ALLOWED_IMPORTS

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_OWLBEAR_DEP_RE = re.compile(r"^owlbear-([a-z][a-z0-9-]*)(\[.*?\])?")


def _owlbear_deps_from_manifest(manifest_path: Path) -> set[str]:
    """Return the set of owlbear_* namespace names declared in a pyproject.toml."""
    with manifest_path.open("rb") as fh:
        data = tomllib.load(fh)
    deps: list[str] = data.get("project", {}).get("dependencies", [])
    result: set[str] = set()
    for dep in deps:
        m = _OWLBEAR_DEP_RE.match(dep.strip())
        if m:
            # Convert owlbear-foo-bar → owlbear_foo_bar
            result.add("owlbear_" + m.group(1).replace("-", "_"))
    return result


_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Manifest alignment tests — AC1, AC2, AC3
# ---------------------------------------------------------------------------


class TestFromAC_ManifestAlignment:
    """ALLOWED_IMPORTS exactly matches pyproject.toml workspace deps.

    Asserts that each affected entry is the exact set derived from the
    package manifest — no more, no less.  Extra allowed entries that no
    source file currently imports would otherwise go undetected.
    """

    def test_owlbear_memory_allowed_imports_matches_manifest(self) -> None:
        """AC1: owlbear_memory has no owlbear workspace deps → allowed set is empty."""
        manifest = _REPO_ROOT / "serve" / "memory" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        assert ALLOWED_IMPORTS["owlbear_memory"] == expected, (
            f"ALLOWED_IMPORTS['owlbear_memory'] == {ALLOWED_IMPORTS['owlbear_memory']!r} "
            f"but manifest declares {expected!r}"
        )

    def test_owlbear_mcp_memory_allowed_imports_matches_manifest(self) -> None:
        """AC2: owlbear_mcp_memory declares owlbear-memory → allowed set == {"owlbear_memory"}."""
        manifest = _REPO_ROOT / "serve" / "mcp-memory" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        assert ALLOWED_IMPORTS["owlbear_mcp_memory"] == expected, (
            f"ALLOWED_IMPORTS['owlbear_mcp_memory'] == {ALLOWED_IMPORTS['owlbear_mcp_memory']!r} "
            f"but manifest declares {expected!r}"
        )

    def test_owlbear_cockpit_allowed_imports_matches_manifest(self) -> None:
        """AC3: owlbear_cockpit declares owlbear-kanban + owlbear-memory → exact two-element set."""
        manifest = _REPO_ROOT / "serve" / "cockpit" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        assert ALLOWED_IMPORTS["owlbear_cockpit"] == expected, (
            f"ALLOWED_IMPORTS['owlbear_cockpit'] == {ALLOWED_IMPORTS['owlbear_cockpit']!r} "
            f"but manifest declares {expected!r}"
        )

    def test_extra_entry_in_owlbear_memory_would_fail(self) -> None:
        """AC1 regression guard: superset allowed set is not equal to manifest deps."""
        manifest = _REPO_ROOT / "serve" / "memory" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        superset = expected | {"owlbear_kanban"}
        assert superset != expected, "Sanity check: a set with extra entries must differ from the manifest-derived set"

    def test_extra_entry_in_owlbear_mcp_memory_would_fail(self) -> None:
        """AC2 regression guard: superset allowed set is not equal to manifest deps."""
        manifest = _REPO_ROOT / "serve" / "mcp-memory" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        superset = expected | {"owlbear_kanban"}
        assert superset != expected, "Sanity check: a set with extra entries must differ from the manifest-derived set"

    def test_extra_entry_in_owlbear_cockpit_would_fail(self) -> None:
        """AC3 regression guard: superset allowed set is not equal to manifest deps."""
        manifest = _REPO_ROOT / "serve" / "cockpit" / "pyproject.toml"
        expected = _owlbear_deps_from_manifest(manifest)
        superset = expected | {"owlbear_tools"}
        assert superset != expected, "Sanity check: a set with extra entries must differ from the manifest-derived set"
