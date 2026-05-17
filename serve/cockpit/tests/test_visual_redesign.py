from __future__ import annotations

"""Consolidation tests for the cockpit visual redesign (#1629).

Full-surface quality gate across all 4 batches of the visual redesign.
Verifies the three delivery-gate commands, inline-style budget, and
dual-theme accessibility compliance.

Durable file: remains after task #1629 is archived (consolidation-test tag).
"""

import re
import subprocess
from pathlib import Path

import pytest

_WEB = Path(__file__).parent.parent / "web"
_TSX_SRC = _WEB / "src"


# ─────────────────────────────────────────────────────────────────────────────
# AC-1: Vitest, Playwright e2e:all, and production build complete with zero failures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.slow
class TestCockpitVisualRedesignSuiteGates:
    """AC-1: Full Playwright e2e suite (npm run test:e2e:all) passes with zero failures.

    Vitest (npm test) and production build (npm run build) are currently green and
    are regression-guarded by the builder's code-review gate. This class verifies
    the Playwright e2e suite — the one delivery gate that currently FAILS due to the
    RepairPanel <span onClick> violation in accessibility-sweep.spec.ts.

    Prerequisites: ``npx playwright install chromium`` run once in serve/cockpit/web/.
    """

    @pytest.mark.timeout(420)
    def test_playwright_e2e_all_passes(self) -> None:
        """AC-1: ``npm run test:e2e:all`` (full Playwright suite, all specs) exits 0.

        Fails until the builder fixes:
        - RepairPanel <span onClick> interactive-supports-focus violation
          (already flagged in accessibility-sweep.spec.ts and dual-theme spec).
        - Any additional violations exposed by the new accessibility-dual-theme spec.

        Prerequisites: ``npx playwright install chromium`` run once.
        """
        result = subprocess.run(
            ["npm", "run", "test:e2e:all"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=400,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Playwright test:e2e:all failed (exit {result.returncode}).\n"
            "Fix all e2e spec failures (RepairPanel violation + dual-theme violations) "
            "before marking this consolidation task done.\n\n"
            f"Playwright output:\n{combined[-4000:]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# AC-2: Inline-style budget — at most 4 style={…} attributes, each justified
# ─────────────────────────────────────────────────────────────────────────────


class TestCockpitVisualRedesignInlineStyleBudget:
    """AC-2: At most 4 JSX inline-style attributes in serve/cockpit/web/src/**/*.tsx.

    Each remaining style={…} attribute must have a
    ``// inline-justified: <reason>`` comment on a preceding line explaining
    why Tailwind or a CSS class cannot replace it.

    Builder must:
    1. Convert convertible inline styles to Tailwind/CSS classes.
    2. Add justification comments to the 4 runtime-positioned exceptions
       (context menu, DRStatusIndicator popover, HealthBadge popover,
       RepairPanel OVERLAY_STYLE usages).
    """

    def _collect_style_attrs(self) -> list[tuple[str, int, str]]:
        """Return (filepath, 1-based line number, stripped line text) for every style={ hit."""
        hits: list[tuple[str, int, str]] = []
        for path in sorted(_TSX_SRC.rglob("*.tsx")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if re.search(r"style=\{", line):
                    hits.append((str(path), i + 1, line.strip()))
        return hits

    def test_inline_style_count_at_most_four(self) -> None:
        """Total style={…} occurrences across all TSX source files must be ≤ 4.

        Current count is 14 (11 ``style={{`` + 3 ``style={OVERLAY_STYLE}``).
        Builder must convert 10+ occurrences to Tailwind/CSS, retaining only
        runtime-positioned elements that cannot be expressed statically.
        """
        occurrences = self._collect_style_attrs()
        assert len(occurrences) <= 4, (
            f"Expected ≤ 4 inline style attributes, found {len(occurrences)}. "
            "Convert excess occurrences to Tailwind utilities or CSS classes. "
            "Only runtime-positioned elements (fixed popover coordinates, dynamic "
            "grid columns) may remain.\n" + "\n".join(f"  {f}:{ln}: {text}" for f, ln, text in occurrences)
        )

    def test_each_inline_style_has_justification_comment(self) -> None:
        """Each remaining style={…} must have '// inline-justified: <reason>' on a preceding line.

        The comment must appear within 3 lines before the style= attribute so it
        is visible to reviewers without scrolling.
        """
        missing: list[tuple[str, int, str]] = []
        for path in sorted(_TSX_SRC.rglob("*.tsx")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if re.search(r"style=\{", line):
                    context = "\n".join(lines[max(0, i - 3) : i + 1])
                    if "// inline-justified:" not in context:
                        missing.append((str(path), i + 1, line.strip()))
        assert missing == [], (
            f"{len(missing)} inline style(s) lack a '// inline-justified: <reason>' comment "
            "within 3 lines before the attribute:\n" + "\n".join(f"  {f}:{ln}: {text}" for f, ln, text in missing)
        )


# ─────────────────────────────────────────────────────────────────────────────
# AC-3: Dual-theme AxeBuilder scans — zero violations under both color schemes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.slow
class TestCockpitVisualRedesignDualTheme:
    """AC-3: Zero AxeBuilder violations under both .scheme-light and .scheme-dark.

    Delegates to the Playwright spec ``e2e/accessibility-dual-theme.spec.ts``
    which parametrises board, sidecar, and modal surfaces across both themes.

    Prerequisites: ``npx playwright install chromium`` run once in serve/cockpit/web/.
    """

    @pytest.mark.timeout(420)
    def test_dual_theme_axe_spec_passes(self) -> None:
        """accessibility-dual-theme.spec.ts exits 0 with zero violations in both themes.

        Fails until the builder:
        - Fixes the RepairPanel <span onClick> interactive-supports-focus violation.
        - Resolves any dark-theme-specific axe violations exposed by the new sweep.
        """
        result = subprocess.run(
            ["npx", "playwright", "test", "e2e/accessibility-dual-theme.spec.ts"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=400,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Dual-theme accessibility spec failed (exit {result.returncode}).\n"
            "Builder must fix all AxeBuilder violations reported under both "
            ".scheme-light and .scheme-dark themes.\n\n"
            f"Playwright output:\n{combined[-4000:]}"
        )
