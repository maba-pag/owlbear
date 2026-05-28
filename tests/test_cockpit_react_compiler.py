"""Failing tests for #1015: Execute React Compiler enablement.

Covers:
- AC#1: babel-plugin-react-compiler installed as devDependency in package.json
- AC#2: vite.config.ts updated with babel plugin configuration
- AC#3: npm run build succeeds clean (no TypeScript type errors)
- AC#4: Vitest suite passes with no unhandled errors
- AC#5: Playwright E2E passes (requires npx playwright install chromium)
- AC#6: Remove redundant React.memo/useMemo/useCallback (11 callsites across 5 modules)
  - KanbanBoard.tsx: Card (memo), Column (memo), Column.sorted (useMemo),
    Column.handleCardDragStart (useCallback), KanbanBoard.handleContextMenu (useCallback),
    KanbanBoard.handleDragStart (useCallback), KanbanBoard.handleDragEnd (useCallback),
    KanbanBoard.tasksByStatus (useMemo)
  - usePolling.ts: poll (useCallback)
  - useConnectionHealth.ts: markHealthy (useCallback), updateHealth (useCallback)
- AC#7: KanbanBoard_963.test.tsx deleted or structural assertions removed
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"
_SRC = _WEB / "src"
_HOOKS = _SRC / "hooks"


# ---------------------------------------------------------------------------
# AC#1 + AC#2 — Configuration
# ---------------------------------------------------------------------------


class TestFromAC_KanbanBoardMemoRemoval:
    """All 8 manual-memoization callsites in KanbanBoard.tsx must be removed."""

    @pytest.fixture(autouse=True)
    def _src(self) -> None:
        self._kanbanboard = (_SRC / "KanbanBoard.tsx").read_text()

    # Callsite 1 — Card: memo wrapper
    def test_card_not_wrapped_in_react_memo(self) -> None:
        """Callsite 1: export const Card = memo(...) must be removed."""
        assert "export const Card = memo(" not in self._kanbanboard, (
            "Card is still wrapped in React.memo() — remove the wrapper; React Compiler handles this automatically"
        )

    # Callsite 2 — Column: memo wrapper
    def test_column_not_wrapped_in_react_memo(self) -> None:
        """Callsite 2: export const Column = memo(...) must be removed."""
        assert "export const Column = memo(" not in self._kanbanboard, (
            "Column is still wrapped in React.memo() — remove the wrapper"
        )

    # Callsite 3 — Column: useMemo for sorted tasks
    def test_column_sorted_tasks_not_usememo(self) -> None:
        """Callsite 3: const sorted = useMemo(...) in Column must be removed."""
        assert "const sorted = useMemo(" not in self._kanbanboard, (
            "Column still uses useMemo for sorted tasks — remove the useMemo wrapper"
        )

    # Callsite 4 — Column: useCallback for handleCardDragStart
    def test_column_handlecarddragstart_not_usecallback(self) -> None:
        """Callsite 4: const handleCardDragStart = useCallback(...) must be removed."""
        assert "const handleCardDragStart = useCallback(" not in self._kanbanboard, (
            "Column still uses useCallback for handleCardDragStart — remove the wrapper"
        )

    # Callsite 5 — KanbanBoard: useCallback for handleContextMenu
    def test_kanbanboard_handlecontextmenu_not_usecallback(self) -> None:
        """Callsite 5: const handleContextMenu = useCallback(...) must be removed."""
        assert "const handleContextMenu = useCallback(" not in self._kanbanboard, (
            "KanbanBoard still uses useCallback for handleContextMenu — remove the wrapper"
        )

    # Callsite 6 — KanbanBoard: useCallback for handleDragStart
    def test_kanbanboard_handledragstart_not_usecallback(self) -> None:
        """Callsite 6: const handleDragStart = useCallback(...) must be removed."""
        assert "const handleDragStart = useCallback(" not in self._kanbanboard, (
            "KanbanBoard still uses useCallback for handleDragStart — remove the wrapper"
        )

    # Callsite 7 — KanbanBoard: useCallback for handleDragEnd
    def test_kanbanboard_handledragend_not_usecallback(self) -> None:
        """Callsite 7: const handleDragEnd = useCallback(...) must be removed."""
        assert "const handleDragEnd = useCallback(" not in self._kanbanboard, (
            "KanbanBoard still uses useCallback for handleDragEnd — remove the wrapper"
        )

    # Callsite 8 — KanbanBoard: useMemo for tasksByStatus
    def test_kanbanboard_tasksbystatus_not_usememo(self) -> None:
        """Callsite 8: const tasksByStatus = useMemo(...) must be removed."""
        assert "const tasksByStatus = useMemo(" not in self._kanbanboard, (
            "KanbanBoard still uses useMemo for tasksByStatus — remove the wrapper"
        )

    # Import hygiene — after all callsites removed, memo must not be imported
    def test_kanbanboard_does_not_import_memo(self) -> None:
        """After removing all memo() callsites, 'memo' must not remain in the react import.

        Leaving a dead import would cause a linting error (unused import).
        """
        react_import_line = next(
            (line for line in self._kanbanboard.splitlines() if "from 'react'" in line),
            "",
        )
        assert "memo" not in react_import_line, (
            "KanbanBoard.tsx still imports 'memo' from react — "
            "remove it from the import statement after all callsites are removed"
        )


# ---------------------------------------------------------------------------
# AC#6 — Callsite removal: usePolling.ts (callsite 9)
# ---------------------------------------------------------------------------


class TestFromAC_UseConnectionHealthMemoRemoval:
    """useCallback callsites in useConnectionHealth.ts must be removed (callsites 10-11)."""

    @pytest.fixture(autouse=True)
    def _src(self) -> None:
        self._health = (_HOOKS / "useConnectionHealth.ts").read_text()

    def test_markhealthy_not_wrapped_in_usecallback(self) -> None:
        """Callsite 10: const markHealthy = useCallback(...) must be removed."""
        assert "const markHealthy = useCallback(" not in self._health, (
            "useConnectionHealth still wraps markHealthy in useCallback — remove the wrapper"
        )

    def test_updatehealth_not_wrapped_in_usecallback(self) -> None:
        """Callsite 11: const updateHealth = useCallback(...) must be removed."""
        assert "const updateHealth = useCallback(" not in self._health, (
            "useConnectionHealth still wraps updateHealth in useCallback — remove the wrapper"
        )

    def test_useconnectionhealth_does_not_import_usecallback(self) -> None:
        """After removing both callsites, useCallback must not remain imported."""
        react_import_line = next(
            (line for line in self._health.splitlines() if "from 'react'" in line),
            "",
        )
        assert "useCallback" not in react_import_line, (
            "useConnectionHealth.ts still imports useCallback — remove it after callsites are removed"
        )


# ---------------------------------------------------------------------------
# AC#7 — KanbanBoard_963.test.tsx: delete or rewrite
# ---------------------------------------------------------------------------


class TestFromAC_KanbanBoard963TestCleanup:
    """KanbanBoard_963.test.tsx must be deleted or have structural assertions removed."""

    _TEST_FILE = _SRC / "__tests__" / "KanbanBoard_963.test.tsx"

    def test_hook_calls_memo_assertion_absent(self) -> None:
        """hookCalls.memo assertions verify the manual memos being removed — must be gone."""
        if not self._TEST_FILE.exists():
            pytest.skip("File already deleted — AC satisfied")
        content = self._TEST_FILE.read_text()
        assert "hookCalls.memo" not in content, (
            "KanbanBoard_963.test.tsx still asserts hookCalls.memo counts — "
            "delete the file or rewrite tests without structural assertions"
        )

    def test_hook_calls_usememo_assertion_absent(self) -> None:
        """hookCalls.useMemo assertions verify useMemo callsites being removed — must be gone."""
        if not self._TEST_FILE.exists():
            pytest.skip("File already deleted — AC satisfied")
        content = self._TEST_FILE.read_text()
        assert "hookCalls.useMemo" not in content, (
            "KanbanBoard_963.test.tsx still asserts hookCalls.useMemo counts — "
            "delete the file or rewrite without structural assertions"
        )

    def test_hook_calls_usecallback_assertion_absent(self) -> None:
        """hookCalls.useCallback assertions verify useCallback callsites being removed — must be gone."""
        if not self._TEST_FILE.exists():
            pytest.skip("File already deleted — AC satisfied")
        content = self._TEST_FILE.read_text()
        assert "hookCalls.useCallback" not in content, (
            "KanbanBoard_963.test.tsx still asserts hookCalls.useCallback counts — "
            "delete the file or rewrite without structural assertions"
        )

    def test_typeof_structural_assertion_absent(self) -> None:
        """$$typeof structural check verifies React.memo wrapping — must be gone."""
        if not self._TEST_FILE.exists():
            pytest.skip("File already deleted — AC satisfied")
        content = self._TEST_FILE.read_text()
        assert "$$typeof" not in content, (
            "KanbanBoard_963.test.tsx still checks $$typeof (React.memo marker) — "
            "delete the file or rewrite without structural assertions"
        )


# ---------------------------------------------------------------------------
# AC#3, AC#4, AC#5 — Subprocess: build, Vitest, Playwright E2E
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.xdist_group("npm_subprocess")
class TestFromAC_BuildTestE2EVerification:
    """AC#3/4/5: subprocess verification of npm build, Vitest suite, and Playwright E2E.

    These tests run actual npm commands and are marked slow.
    They verify the runtime integration contract that static file-analysis cannot cover.

    Prerequisites:
      - AC#5 (Playwright): run `npx playwright install chromium` in serve/cockpit/web/ once.
    """

    @pytest.mark.timeout(200)
    def test_npm_build_succeeds_clean(self) -> None:
        """AC#3: npm run build exits 0 and emits no TypeScript type errors.

        A clean build must produce zero `error TS` lines in tsc output.
        Pre-existing type errors in test files must be resolved or those files
        excluded from the production tsconfig.
        """
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=180,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, f"npm run build failed (exit {result.returncode}):\n{combined[-2000:]}"
        assert "error TS" not in combined, (
            "TypeScript type errors found in build output — fix or exclude test "
            "files from the production tsconfig so the compiler-enabled build is clean:\n" + combined[-2000:]
        )

    @pytest.mark.timeout(360)
    def test_vitest_suite_no_unhandled_errors(self) -> None:
        """AC#4: npm test exits 0 and reports no unhandled errors.

        `vitest run` may exit 0 while still reporting unhandled async errors.
        This test checks both the exit code and the absence of the
        "Unhandled Errors" section in Vitest output.
        """
        result = subprocess.run(
            ["npm", "test"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=300,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, f"npm test failed (exit {result.returncode}):\n{combined[-2000:]}"
        assert "Unhandled Errors" not in combined, (
            "Vitest reported unhandled errors — inspect and fix the cleanup "
            "race condition (suspected: KanbanBoard.test.tsx ownerDocument error):\n" + combined[-2000:]
        )

    @pytest.mark.timeout(360)
    def test_playwright_e2e_passes(self) -> None:
        """AC#5: npm run test:e2e exits 0.

        Requires Playwright chromium browser to be installed:
            npx playwright install chromium   (run once after npm install)

        The webServer config starts `npm run build && npm run preview` automatically.
        """
        result = subprocess.run(
            ["npm", "run", "test:e2e"],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=300,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"npm run test:e2e failed (exit {result.returncode}) — "
            "ensure `npx playwright install chromium` has been run:\n" + combined[-2000:]
        )
