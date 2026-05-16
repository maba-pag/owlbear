"""Structural RED-phase tests for #1227: Frontend polling refactor.

AC coverage:
  AC2 (td:2): Shared polling utility usePollingFetch extracted
  AC3 (td:1): useBoard, useScanPolling, usePendingDRs consume usePollingFetch
  AC1 (structural): Shell derives health from tasks poll (imports useBoard, not just usePolling)

All tests FAIL until the builder implements the polling refactor.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / "serve" / "cockpit" / "web" / "src" / "hooks"
SHELL = ROOT / "serve" / "cockpit" / "web" / "src" / "Shell.tsx"


# ---------------------------------------------------------------------------
# AC2: usePollingFetch utility extracted
# ---------------------------------------------------------------------------


class TestFromAC_UsePollingFetchExists:
    """AC2: Shared polling utility must exist at hooks/usePollingFetch.ts."""

    def test_usepollingfetch_file_exists(self) -> None:
        """usePollingFetch.ts must be created at the contract path."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), (
            f"File not found: {hook_file}. "
            "Builder must create serve/cockpit/web/src/hooks/usePollingFetch.ts "
            "with the shared polling utility."
        )

    def test_usepollingfetch_exports_named_hook(self) -> None:
        """usePollingFetch.ts must export a named function 'usePollingFetch'."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), "usePollingFetch.ts missing — run test_usepollingfetch_file_exists first."
        content = hook_file.read_text()
        assert "export function usePollingFetch" in content or "export const usePollingFetch" in content, (
            "usePollingFetch.ts must export 'usePollingFetch' as a named function."
        )

    def test_usepollingfetch_accepts_onsuccess_callback(self) -> None:
        """usePollingFetch must accept an onSuccess callback (health tracking)."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), "usePollingFetch.ts missing."
        content = hook_file.read_text()
        assert "onSuccess" in content, "usePollingFetch must accept 'onSuccess' callback for health tracking (AC2)."

    def test_usepollingfetch_accepts_onerror_callback(self) -> None:
        """usePollingFetch must accept an onError callback (health degradation)."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), "usePollingFetch.ts missing."
        content = hook_file.read_text()
        assert "onError" in content, "usePollingFetch must accept 'onError' callback for health degradation (AC2)."

    def test_usepollingfetch_uses_abortcontroller(self) -> None:
        """usePollingFetch must use AbortController for cleanup (AC2)."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), "usePollingFetch.ts missing."
        content = hook_file.read_text()
        assert "AbortController" in content, (
            "usePollingFetch must use AbortController for request cleanup on unmount (AC2)."
        )

    def test_usepollingfetch_has_inflight_guard(self) -> None:
        """usePollingFetch must include an inFlight guard ref (AC2)."""
        hook_file = HOOKS / "usePollingFetch.ts"
        assert hook_file.exists(), "usePollingFetch.ts missing."
        content = hook_file.read_text()
        assert "inFlight" in content or "inFlightRef" in content, (
            "usePollingFetch must have an inFlight guard to prevent concurrent polls (AC2)."
        )


# ---------------------------------------------------------------------------
# AC3: Consumer hooks use the shared utility
# ---------------------------------------------------------------------------


class TestFromAC_HooksConsumeSharedUtility:
    """AC3: useBoard, useScanPolling, usePendingDRs must import usePollingFetch."""

    def test_useboard_imports_usepollingfetch(self) -> None:
        """useBoard.ts must import usePollingFetch from the shared utility."""
        hook_file = HOOKS / "useBoard.ts"
        assert hook_file.exists(), "useBoard.ts missing."
        content = hook_file.read_text()
        assert "usePollingFetch" in content, (
            "useBoard.ts must import and use usePollingFetch (AC3). Currently useBoard manages its own polling loop."
        )

    def test_usscanpolling_imports_usepollingfetch(self) -> None:
        """useScanPolling.ts must import usePollingFetch from the shared utility."""
        hook_file = HOOKS / "useScanPolling.ts"
        assert hook_file.exists(), "useScanPolling.ts missing."
        content = hook_file.read_text()
        assert "usePollingFetch" in content, (
            "useScanPolling.ts must import and use usePollingFetch (AC3). "
            "Currently useScanPolling manages its own polling loop."
        )

    def test_usependingdrs_imports_usepollingfetch(self) -> None:
        """usePendingDRs.ts must import usePollingFetch from the shared utility."""
        hook_file = HOOKS / "usePendingDRs.ts"
        assert hook_file.exists(), "usePendingDRs.ts missing."
        content = hook_file.read_text()
        assert "usePollingFetch" in content, (
            "usePendingDRs.ts must import and use usePollingFetch (AC3). "
            "Currently usePendingDRs manages its own polling loop."
        )


# ---------------------------------------------------------------------------
# AC1 (structural): Shell derives health from tasks poll — imports useBoard
# ---------------------------------------------------------------------------


class TestFromAC_ShellHealthFromTasksPoll:
    """AC1 structural: Shell must import useBoard to derive health from tasks poll."""

    def test_shell_imports_useboard_for_health(self) -> None:
        """Shell.tsx must import useBoard (tasks-poll health source)."""
        assert SHELL.exists(), "Shell.tsx missing."
        content = SHELL.read_text()
        assert "useBoard" in content, (
            "Shell.tsx must import useBoard to derive connection health from the tasks "
            "poll (AC1). Currently Shell uses usePolling('/health') instead."
        )

    def test_shell_does_not_use_polling_slash_health_as_health_source(self) -> None:
        """Shell.tsx must NOT call usePolling('/health') as the health source."""
        assert SHELL.exists(), "Shell.tsx missing."
        content = SHELL.read_text()
        # After refactoring, /health polling is removed from Shell.
        # The usePolling hook may still exist in the codebase but should
        # not be used for the traffic-light health in Shell.
        assert "usePolling('/health')" not in content, (
            "Shell.tsx still calls usePolling('/health') for health. "
            "After AC1 refactor, health must come from the tasks poll via useBoard (AC1)."
        )

    def test_kanbanboard_tsx_does_not_own_tasks_poll(self) -> None:
        """KanbanBoard.tsx must NOT call useBoard() internally after state lifting."""
        kb_file = ROOT / "serve" / "cockpit" / "web" / "src" / "KanbanBoard.tsx"
        assert kb_file.exists(), "KanbanBoard.tsx missing."
        content = kb_file.read_text()
        # After state lifting, KanbanBoard receives board+tasks via props.
        # The hook call `useBoard()` should not appear inside the component body.
        # We look for the invocation pattern (with parentheses), not just the import.
        assert "= useBoard()" not in content, (
            "KanbanBoard.tsx still calls useBoard() internally. "
            "After AC4 state-lifting, KanbanBoard must receive board+tasks via props "
            "from Shell — not own the tasks poll."
        )


# ---------------------------------------------------------------------------
# AC4 (retry, cycle 2): LegacyKanbanBoard fallback must be removed
# ---------------------------------------------------------------------------


class TestFromAC_KanbanBoardLegacyRemoval:
    """AC4 (refined): LegacyKanbanBoard backwards-compat fallback must not exist.

    The first-cycle test used ``= useBoard()`` (whitespace-sensitive) and missed
    the live ``boardState=useBoard()`` invocation inside LegacyKanbanBoard.
    These tests use regex and literal substring checks that are whitespace-agnostic.
    """

    def test_legacy_kanbanboard_function_removed(self) -> None:
        """KanbanBoard.tsx must not define a LegacyKanbanBoard function."""
        import re

        kb_file = ROOT / "serve" / "cockpit" / "web" / "src" / "KanbanBoard.tsx"
        assert kb_file.exists(), "KanbanBoard.tsx missing."
        content = kb_file.read_text()
        assert not re.search(r"\bLegacyKanbanBoard\b", content), (
            "KanbanBoard.tsx still defines/references LegacyKanbanBoard. "
            "AC4 (refined) requires removal of the backwards-compat fallback so "
            "KanbanBoard has no useBoard() call on any code path."
        )

    def test_kanbanboard_tsx_no_useboard_invocation_whitespace_agnostic(self) -> None:
        """KanbanBoard.tsx must have no useBoard() call in any form (whitespace-agnostic).

        The first-cycle check ``assert "= useBoard()" not in content`` missed
        ``const boardState=useBoard()`` (no spaces around ``=``).
        This test uses a regex that matches regardless of surrounding whitespace.
        """
        import re

        kb_file = ROOT / "serve" / "cockpit" / "web" / "src" / "KanbanBoard.tsx"
        assert kb_file.exists(), "KanbanBoard.tsx missing."
        content = kb_file.read_text()
        # Match any form: `= useBoard()`, `=useBoard()`, `boardState=useBoard()`, etc.
        # Excludes the re-export line `export { useBoard } from './hooks/useBoard'`
        # and import line, which contain 'useBoard' but not as a call invocation.
        invocation = re.search(r"\buseBoard\s*\(\s*\)", content)
        assert invocation is None, (
            f"KanbanBoard.tsx still invokes useBoard() at: "
            f"{content[max(0, invocation.start() - 40) : invocation.end() + 40]!r}. "
            "After AC4 state-lifting and LegacyKanbanBoard removal, KanbanBoard "
            "must not call useBoard() on any code path."
        )


# ---------------------------------------------------------------------------
# AC6 (new, cycle 2): Durable suites aligned to new polling architecture
# ---------------------------------------------------------------------------


class TestFromAC_DurableSuiteAlignment:
    """AC6 (new): Durable suites must be updated to assert the new architecture.

    Shell_966.test.tsx: must not assert the removed ``usePolling('/health')`` wiring.
    KanbanBoard.test.tsx: must not render ``<KanbanBoard />`` without board/tasks props
    after LegacyKanbanBoard removal.
    """

    TESTS_DIR = ROOT / "serve" / "cockpit" / "web" / "src" / "__tests__"

    def test_shell_966_no_health_polling_assertion(self) -> None:
        """Shell_966.test.tsx must not assert the removed /health endpoint wiring.

        The durable suite currently contains
        ``expect(vi.mocked(usePolling)).toHaveBeenCalledWith('/health')``
        which encodes the old contract that AC1 explicitly removed.  The builder
        must replace it with an assertion against the new useBoard health source.
        """
        suite = self.TESTS_DIR / "Shell_966.test.tsx"
        assert suite.exists(), "Shell_966.test.tsx missing."
        content = suite.read_text()
        assert "toHaveBeenCalledWith('/health')" not in content, (
            "Shell_966.test.tsx still asserts usePolling('/health') wiring. "
            "AC6 requires this durable suite to be updated so it asserts the new "
            "health-from-useBoard contract instead of the removed /health endpoint."
        )

    def test_kanbanboard_test_tsx_no_bare_render_without_props(self) -> None:
        """KanbanBoard.test.tsx must not render <KanbanBoard /> without board/tasks props.

        After LegacyKanbanBoard is removed, a bare ``<KanbanBoard />`` render
        receives no board state and would fail at runtime.  The durable suite
        must be updated to provide board, tasks, loading, error, and refetchTasks
        props so it exercises the real component contract.
        """
        import re

        suite = self.TESTS_DIR / "KanbanBoard.test.tsx"
        assert suite.exists(), "KanbanBoard.test.tsx missing."
        content = suite.read_text()
        bare_render = re.search(r"<KanbanBoard\s*/>", content)
        assert bare_render is None, (
            "KanbanBoard.test.tsx renders <KanbanBoard /> without required props. "
            "AC6 requires this suite to provide board, tasks, loading, error, and "
            "refetchTasks props after LegacyKanbanBoard removal."
        )

    # ── Cycle-3 gaps: additional durable suites identified by reviewer ──────

    def test_useboard_test_imports_from_hooks_not_kanbanboard(self) -> None:
        """useBoard.test.ts (#965) must import useBoard from hooks/useBoard, not KanbanBoard.

        KanbanBoard.tsx no longer re-exports useBoard after the state-lifting refactor.
        The import ``import { useBoard } from '../KanbanBoard'`` in useBoard.test.ts will
        fail at runtime — the builder must update it to ``../hooks/useBoard``.
        """
        suite = self.TESTS_DIR / "useBoard.test.ts"
        assert suite.exists(), "useBoard.test.ts missing."
        content = suite.read_text()
        assert "from '../KanbanBoard'" not in content, (
            "useBoard.test.ts (#965) still imports useBoard from '../KanbanBoard'. "
            "KanbanBoard.tsx no longer exports useBoard after the refactor. "
            "AC6 (cycle 3) requires updating the import to '../hooks/useBoard'."
        )

    def test_kanbanboard_1242_no_bare_render_without_props(self) -> None:
        """KanbanBoard_1242.test.tsx must not render <KanbanBoard /> without required props.

        After LegacyKanbanBoard removal, bare ``<KanbanBoard />`` renders show
        a loading spinner (loading defaults to true) instead of the task cards
        the test expects.  Builder must pass board, tasks, loading={false},
        error, and refetchTasks as explicit props (AC6 cycle 3 scope).
        """
        import re

        suite = self.TESTS_DIR / "KanbanBoard_1242.test.tsx"
        assert suite.exists(), "KanbanBoard_1242.test.tsx missing."
        content = suite.read_text()
        bare_render = re.search(r"<KanbanBoard\s*/>", content)
        assert bare_render is None, (
            "KanbanBoard_1242.test.tsx renders <KanbanBoard /> without required props. "
            "After LegacyKanbanBoard removal this shows only a loading spinner — "
            "tests see no task cards and fail. "
            "AC6 (cycle 3) requires explicit board/tasks/loading={false}/error/refetchTasks props."
        )

    def test_kanbanboard_959_no_bare_render_without_props(self) -> None:
        """KanbanBoard_959.test.tsx must not render <KanbanBoard /> without required props.

        The performance test renders 700 task cards via renderBoard() which uses
        a bare ``<KanbanBoard />``.  After state-lifting, the component no longer
        polls, so no tasks ever appear — the test waits forever and then fails.
        Builder must pass the fixture tasks via props (AC6 cycle 3 scope).
        """
        import re

        suite = self.TESTS_DIR / "KanbanBoard_959.test.tsx"
        assert suite.exists(), "KanbanBoard_959.test.tsx missing."
        content = suite.read_text()
        bare_render = re.search(r"<KanbanBoard\s*/>", content)
        assert bare_render is None, (
            "KanbanBoard_959.test.tsx renders <KanbanBoard /> without required props. "
            "After state-lifting the component never polls — task cards never appear. "
            "AC6 (cycle 3) requires explicit props with the 700-task fixture."
        )

    def test_kanbanboard_933_no_bare_render_without_props(self) -> None:
        """KanbanBoard_933.test.tsx must not render <KanbanBoard /> without required props.

        Same root cause as 959/1242: the renderBoard() helper wraps a bare
        ``<KanbanBoard />`` without board/tasks props.  After state-lifting
        the component shows a loading spinner; the error-path tests never see
        task cards or error states and fail.
        Builder must pass explicit props (AC6 cycle 3 scope).
        """
        import re

        suite = self.TESTS_DIR / "KanbanBoard_933.test.tsx"
        assert suite.exists(), "KanbanBoard_933.test.tsx missing."
        content = suite.read_text()
        bare_render = re.search(r"<KanbanBoard\s*/>", content)
        assert bare_render is None, (
            "KanbanBoard_933.test.tsx renders <KanbanBoard /> without required props. "
            "After state-lifting the component shows only a loading spinner — "
            "error-path tests never see the expected error UI. "
            "AC6 (cycle 3) requires explicit board/tasks/loading={false}/error/refetchTasks props."
        )

    def test_useboard_967_interface_asserts_health_field(self) -> None:
        """useBoard_967.test.ts must assert 'health' in the hook return interface.

        The hook now returns a 'health' field (HealthState) derived from the
        tasks poll via useConnectionHealth.  The durable interface test in
        useBoard_967.test.ts must include ``toHaveProperty('health')`` alongside
        the other seven fields (AC6 cycle 3).
        """
        suite = self.TESTS_DIR / "useBoard_967.test.ts"
        assert suite.exists(), "useBoard_967.test.ts missing."
        content = suite.read_text()
        assert "toHaveProperty('health')" in content or 'toHaveProperty("health")' in content, (
            "useBoard_967.test.ts does not assert toHaveProperty('health') in its "
            "interface test.  useBoard now returns a 'health' field — AC6 (cycle 3) "
            "requires the durable interface assertion to include it."
        )
