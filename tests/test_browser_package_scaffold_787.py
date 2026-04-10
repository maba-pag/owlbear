"""Failing tests for task #787: owlbear_browser package scaffold and CDP launcher.

Covers the AC item from #787 not already addressed by the #755 RED-phase tests:
  AC#1:  serve/browser/pyproject.toml — playwright>=1.40 dependency present and versioned

All tests intentionally fail on current HEAD — serve/browser/pyproject.toml has
``dependencies = []`` (playwright not yet added).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
BROWSER_PYPROJECT = ROOT / "serve" / "browser" / "pyproject.toml"
_MIN_PLAYWRIGHT_VERSION = (1, 40)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_browser_deps() -> list[str]:
    """Parse serve/browser/pyproject.toml and return the project.dependencies list."""
    data = tomllib.loads(BROWSER_PYPROJECT.read_text(encoding="utf-8"))
    return data["project"].get("dependencies", [])


def _find_playwright_dep(deps: list[str]) -> str | None:
    """Return the playwright dep string if present, otherwise None."""
    for dep in deps:
        if re.match(r"^playwright", dep, re.IGNORECASE):
            return dep
    return None


# ---------------------------------------------------------------------------
# TestFromAC_BrowserPackageScaffold  (AC#1)
# ---------------------------------------------------------------------------


class TestFromAC_BrowserPackageScaffold:  # noqa: N801
    """serve/browser/pyproject.toml must declare playwright>=1.40 as a dependency."""

    def test_playwright_dep_present_in_project_dependencies(self) -> None:
        """playwright must appear in serve/browser/pyproject.toml project.dependencies."""
        deps = _get_browser_deps()
        assert _find_playwright_dep(deps) is not None, (
            f"'playwright' not found in serve/browser/pyproject.toml dependencies: {deps}"
        )

    def test_playwright_dep_specifies_lower_bound_operator(self) -> None:
        """playwright dep must use a minimum-version operator (>= or ~=), not a bare name."""
        deps = _get_browser_deps()
        dep = _find_playwright_dep(deps)
        assert dep is not None, "playwright not found in dependencies — cannot verify version operator"
        assert ">=" in dep or "~=" in dep, (
            f"playwright dep must use >= or ~= version operator; got: {dep!r}"
        )

    def test_playwright_min_version_is_at_least_1_40(self) -> None:
        """playwright minimum version must be 1.40 or higher (Playwright CDP API compatibility)."""
        deps = _get_browser_deps()
        dep = _find_playwright_dep(deps)
        assert dep is not None, "playwright not found in dependencies — cannot verify version"
        m = re.search(r"[>~]=\s*(\d+)\.(\d+)", dep)
        assert m is not None, (
            f"Could not parse a '>=X.Y' or '~=X.Y' version from playwright dep: {dep!r}"
        )
        major, minor = int(m.group(1)), int(m.group(2))
        assert (major, minor) >= _MIN_PLAYWRIGHT_VERSION, (
            f"playwright minimum version must be >= {_MIN_PLAYWRIGHT_VERSION}; "
            f"got ({major}, {minor}) from: {dep!r}"
        )

    def test_playwright_dep_not_pinned_to_exact_version(self) -> None:
        """playwright must not be pinned with == — library deps require a version range."""
        deps = _get_browser_deps()
        dep = _find_playwright_dep(deps)
        assert dep is not None, "playwright not found in dependencies — cannot verify pin"
        # '==' should not appear (exact pin is fragile for a library dep).
        # Note: '>=' contains '=' so we check for '==' specifically.
        assert "==" not in dep, (
            f"playwright must not use exact-version pin (==); got: {dep!r}"
        )
