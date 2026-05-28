from __future__ import annotations

"""Consolidation tests for the cockpit visual redesign (#1629).

Full-surface quality gate across all 4 batches of the visual redesign.
Verifies the three delivery-gate commands, inline-style budget, and
dual-theme accessibility compliance.

Durable file: remains after task #1629 is archived (consolidation-test tag).
"""

import subprocess
from pathlib import Path

import pytest

_WEB = Path(__file__).parent.parent / "web"
_TSX_SRC = _WEB / "src"


# ─────────────────────────────────────────────────────────────────────────────
# AC-1: Vitest, Playwright e2e:all, and production build complete with zero failures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.xdist_group("npm_subprocess")
class TestCockpitVisualRedesignSuiteGates:
    """AC-1: Vitest unit tests, full Playwright e2e suite, and production build pass with zero failures.

    All three delivery gates from AC-1 are verified here as durable subprocess proofs.
    Prerequisites: ``npx playwright install chromium`` run once in serve/cockpit/web/.
    """

    @pytest.mark.timeout(300)
    def test_vitest_passes(self) -> None:
        """AC-1: ``npm test`` (Vitest unit suite) exits 0 with zero test failures."""
        result = subprocess.run(
            ["npm", "test"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=240,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Vitest unit suite failed (exit {result.returncode}).\n"
            "Fix all failing unit tests before marking this consolidation task done.\n\n"
            f"Vitest output:\n{combined[-4000:]}"
        )

    @pytest.mark.timeout(180)
    def test_production_build_passes(self) -> None:
        """AC-1: ``npm run build`` (tsc -b && vite build) exits 0."""
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Production build failed (exit {result.returncode}).\n"
            "Fix all TypeScript/build errors before marking this consolidation task done.\n\n"
            f"Build output:\n{combined[-4000:]}"
        )

    @pytest.mark.timeout(420)
    def test_playwright_e2e_all_passes(self) -> None:
        """AC-1: ``npm run test:e2e:all`` (full Playwright suite, all specs) exits 0.

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
            "Fix all failing e2e specs before marking this consolidation task done.\n\n"
            f"Playwright output:\n{combined[-4000:]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# AC-2: Inline-style budget — at most 4 style={…} attributes, each justified
# ─────────────────────────────────────────────────────────────────────────────
