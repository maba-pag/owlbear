"""RED-phase tests for #759 AC4 — lxml explicit dependency in serve/browser/pyproject.toml.

Binding AC:
  AC4 - `lxml` must be listed as an explicit dependency in `serve/browser/pyproject.toml`
        with constraint `lxml>=4.9`. cleaner.py imports lxml directly; it is currently
        only a transitive dep via trafilatura. If trafilatura dropped lxml the import
        would silently break.

All TestFromAC_* tests MUST FAIL at RED phase:
  - serve/browser/pyproject.toml `project.dependencies` contains no lxml entry.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_BROWSER_PYPROJECT = Path(__file__).parent.parent / "serve" / "browser" / "pyproject.toml"


# ---------------------------------------------------------------------------
# AC4: lxml>=4.9 must appear as an explicit dependency
# ---------------------------------------------------------------------------


class TestFromAC_LxmlExplicitDependency:
    """AC4: lxml>=4.9 must be an explicit entry in serve/browser/pyproject.toml dependencies."""

    def test_lxml_present_in_browser_dependencies(self) -> None:
        """lxml appears in the project.dependencies list of serve/browser/pyproject.toml."""
        with _BROWSER_PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        deps: list[str] = data["project"]["dependencies"]
        lxml_entries = [d for d in deps if d.lower().startswith("lxml")]
        assert lxml_entries, f"lxml is not listed in serve/browser/pyproject.toml dependencies; current deps: {deps}"

    def test_lxml_version_constraint_includes_gte_4_9(self) -> None:
        """lxml dependency specifies a minimum version constraint of >=4.9.

        A bare `lxml` entry with no version would still allow install of an
        incompatible version; `lxml>=4.9` is the minimum required by cleaner.py.
        """
        with _BROWSER_PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        deps: list[str] = data["project"]["dependencies"]
        lxml_entries = [d for d in deps if d.lower().startswith("lxml")]
        assert lxml_entries, "lxml not found in dependencies — cannot check version constraint"
        lxml_dep = lxml_entries[0]
        assert ">=4.9" in lxml_dep, f"lxml constraint does not include '>=4.9'; found: {lxml_dep!r}"

    def test_lxml_dep_has_no_strict_upper_pin(self) -> None:
        """lxml dependency does not pin an exact version (==) that would block updates.

        The spec requires >=4.9 — a floor, not a ceiling. An exact pin like
        lxml==4.9.0 would prevent upgrading to lxml 5.x and break CI when
        newer lxml drops support for old CPython.
        """
        with _BROWSER_PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        deps: list[str] = data["project"]["dependencies"]
        lxml_entries = [d for d in deps if d.lower().startswith("lxml")]
        assert lxml_entries, "lxml not found in dependencies — cannot check pin policy"
        lxml_dep = lxml_entries[0]
        # A strict exact-version pin must not be the only constraint
        assert "==" not in lxml_dep, f"lxml is pinned to an exact version; use >=4.9 instead: {lxml_dep!r}"
