"""RED-phase vitest suite tests for #1365.

AC6: Existing vitest suites pass after PDS v4 alignment.

These tests intentionally fail against the current broken state — the cockpit
web vitest suite reports 20 failures across 4 files due to PDS v4 runtime
incompatibilities (tertiary variant removed, EventSourceProvider context gaps)
and will become green once #1365 resolves all PDS v4 component-usage blockers.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"

# Strip ANSI escape sequences from terminal output.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(scope="module")
def vitest_result() -> subprocess.CompletedProcess[str]:
    """Run the cockpit web vitest suite once (--run mode) for all assertions."""
    return subprocess.run(
        ["npm", "test", "--", "--run"],
        cwd=_WEB,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture(scope="module")
def vitest_output(vitest_result: subprocess.CompletedProcess[str]) -> str:
    """Return ANSI-stripped merged stdout/stderr from the vitest invocation."""
    raw = vitest_result.stdout + vitest_result.stderr
    return _ANSI_RE.sub("", raw)


@pytest.fixture(scope="module")
def vitest_failing_files(vitest_output: str) -> set[str]:
    """Return the set of test file basenames reported as FAIL by vitest.

    Extracts stems like 'PdsMigration_1230.test' from lines such as:
      ' FAIL  src/__tests__/PdsMigration_1230.test.tsx > ...'
    Keeps comparison data small so pytest assertion rewriting stays fast.
    """
    failing: set[str] = set()
    for line in vitest_output.splitlines():
        if " FAIL " not in line:
            continue
        parts = line.split(" FAIL ", 1)
        if len(parts) < 2:
            continue
        # Strip before splitting so leading whitespace doesn't produce empty tokens.
        path_fragment = parts[1].strip().split(" ")[0]
        stem = Path(path_fragment).stem  # e.g. "PdsMigration_1230.test"
        if stem:
            failing.add(stem)
    return failing


class TestFromAC_ExistingVitestSuites:
    """AC6: Existing vitest suites pass after PDS v4 alignment.

    The vitest suite currently reports 20 failures across 4 test files:
      - ActivityTab_1156.test.tsx     (1 failure)
      - PdsMigration_1230.test.tsx    (6 failures — PDS v4 tertiary-variant runtime)
      - Shell_1227.test.tsx           (9 failures)
      - Shell_966.test.tsx            (4 failures)

    All four must be resolved by the builder. The tertiary-variant runtime
    failures in PdsMigration_1230 are directly caused by PDS v4 removing the
    'tertiary' variant; fixing the TypeScript type errors and aligning runtime
    component usage must close these gaps. Shell and ActivityTab failures arising
    from missing EventSourceProvider context must also be resolved as part of
    aligning the cockpit web source with PDS v4 conventions.
    """

    def test_vitest_suite_exits_zero(
        self,
        vitest_result: subprocess.CompletedProcess[str],
    ) -> None:
        """AC6: `npm test -- --run` must exit 0 after PDS v4 alignment.

        Currently exits 1 (20 failing tests). Will pass once all PDS v4
        runtime and type-contract gaps are resolved.
        """
        exit_code = vitest_result.returncode
        assert exit_code == 0, (
            f"vitest exited {exit_code} — "
            "cockpit web vitest suite has test failures after PDS v4 alignment."
        )

    def test_pds_migration_suite_passes(
        self,
        vitest_failing_files: set[str],
    ) -> None:
        """AC6: PdsMigration_1230 test file must not report FAIL.

        Currently fails because PDS v4 runtime raises TypeError when components
        pass variant='tertiary' to PButton (getVariantColors returns undefined).
        Fixing the variant usage in source must also resolve the runtime failures.
        """
        assert "PdsMigration_1230.test" not in vitest_failing_files, (
            "PdsMigration_1230.test.tsx still reports failures in vitest output. "
            "Resolve by aligning PButton variant usage with PDS v4 API in all "
            "affected components (ArchivalModal, ConfirmDialog, DRStatusIndicator, "
            "DetailTab, FilterPanel, HealthBadge, RepairPanel, ResolveModal, Shell)."
        )

    def test_shell_966_suite_passes(
        self,
        vitest_failing_files: set[str],
    ) -> None:
        """AC6: Shell_966 traffic-light test file must not report FAIL.

        Currently fails with EventSourceProvider context errors introduced
        during PDS v4 component alignment work.
        """
        assert "Shell_966.test" not in vitest_failing_files, (
            "Shell_966.test.tsx still reports failures in vitest output. "
            "Ensure Shell.tsx renders correctly within the test provider setup "
            "after PDS v4 EventSourceProvider integration changes."
        )

    def test_shell_1227_suite_passes(
        self,
        vitest_failing_files: set[str],
    ) -> None:
        """AC6: Shell_1227 polling-refactor test file must not report FAIL.

        Currently fails with EventSourceProvider context errors. Must pass
        after PDS v4 alignment closes the provider context gaps.
        """
        assert "Shell_1227.test" not in vitest_failing_files, (
            "Shell_1227.test.tsx still reports failures in vitest output. "
            "Ensure Shell.tsx EventSourceProvider integration is compatible with "
            "the test setup after PDS v4 alignment."
        )

    def test_activity_tab_1156_suite_passes(
        self,
        vitest_failing_files: set[str],
    ) -> None:
        """AC6: ActivityTab_1156 test file must not report FAIL.

        Currently reports 1 failure. Must pass after PDS v4 alignment work.
        """
        assert "ActivityTab_1156.test" not in vitest_failing_files, (
            "ActivityTab_1156.test.tsx still reports failures in vitest output. "
            "Ensure ActivityTab renders without errors after PDS v4 alignment."
        )
