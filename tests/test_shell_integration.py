"""Durable structural guard for Shell health badge integration.

Promoted from archived task #1162 during test curation.
"""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).parent.parent
SHELL_PATH = ROOT / "serve/cockpit/web/src/Shell.tsx"
TEST_PATH = ROOT / "serve/cockpit/web/src/__tests__/Shell_1162.test.tsx"

# Promoted from archived task #1162.


class TestFromAC_ShellHealthBadgeStructure:
    """Structural guards — AC: Shell wiring and vitest test file placement."""

    def test_shell_imports_health_badge(self) -> None:
        content = SHELL_PATH.read_text()
        assert "HealthBadge" in content, (
            "Shell.tsx must import and render HealthBadge. AC1 requires data-testid='health-badge' inside status-bar."
        )

    def test_shell_imports_use_scan_polling(self) -> None:
        content = SHELL_PATH.read_text()
        assert "useScanPolling" in content, (
            "Shell.tsx must import and call useScanPolling(). "
            "AC2 requires Shell to pass normalised items to HealthBadge."
        )

    def test_shell_references_is_loading(self) -> None:
        content = SHELL_PATH.read_text()
        assert "isLoading" in content, (
            "Shell.tsx must conditionally render HealthBadge only when isLoading is false. "
            "AC4 requires badge to be absent before first poll completes."
        )

    def test_vitest_test_file_exists(self) -> None:
        assert TEST_PATH.exists(), (
            f"Vitest test file not found at {TEST_PATH}. "
            "Builder must move .owlbear/scratch/Shell_1162.test.tsx to "
            "serve/cockpit/web/src/__tests__/Shell_1162.test.tsx."
        )

    def test_vitest_test_file_contains_testfromac_class(self) -> None:
        assert TEST_PATH.exists(), "Test file missing — run test_vitest_test_file_exists first."
        content = TEST_PATH.read_text()
        assert "TestFromAC_HealthBadgeShellIntegration" in content, (
            "Vitest test file must contain the TestFromAC_HealthBadgeShellIntegration describe block."
        )
