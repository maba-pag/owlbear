"""RED-phase build compatibility tests for #1364.

These tests intentionally fail against the audited broken state and become green
once #1365 resolves the PDS v4 type-contract mismatches.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"


@pytest.fixture(scope="module")
def build_result() -> subprocess.CompletedProcess[str]:
    """Run the cockpit web production build once for all assertions."""
    return subprocess.run(
        ["npm", "run", "build"],
        cwd=_WEB,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture(scope="module")
def build_output(build_result: subprocess.CompletedProcess[str]) -> str:
    """Return merged stdout/stderr from the build invocation."""
    return build_result.stdout + build_result.stderr


class TestFromAC_CockpitPdsV4BuildCompatibility:
    """AC1/AC4: build must pass cleanly as a delivery gate."""

    def test_npm_build_exits_zero(self, build_result: subprocess.CompletedProcess[str], build_output: str) -> None:
        """AC1/AC4: `npm run build` must complete successfully."""
        assert build_result.returncode == 0, (
            f"npm run build failed (exit {build_result.returncode}).\n"
            "Expected clean build for sync-to-main delivery gate.\n\n"
            f"Build output tail:\n{build_output[-3000:]}"
        )


class TestFromAC_PdsV4TypeContracts:
    """AC2: audited PDS v4 type failures must not appear in build output."""

    @pytest.mark.parametrize(
        ("fragment", "reason"),
        [
            (
                "Type '\"tertiary\"' is not assignable to type '\"primary\" | \"secondary\" | undefined'",
                "PButton tertiary variant is invalid for current PDS v4 button typings.",
            ),
            (
                "Property 'onInput' does not exist on type",
                "PDS wrappers reject unsupported onInput props in select/textarea usage.",
            ),
            (
                "Property 'name' is missing in type",
                "PDS form controls require name and should not fail TS2741.",
            ),
            (
                "Cannot find namespace 'JSX'",
                "JSX namespace typing regressions in React 19/TS config must be resolved.",
            ),
        ],
    )
    def test_known_pds_v4_type_failures_absent(self, fragment: str, reason: str, build_output: str) -> None:
        """AC2: build output must not contain known audited PDS v4 type errors."""
        assert fragment not in build_output, f"Detected known PDS v4 incompatibility: {reason}"


class TestFromAC_PendingDrResolveModalBodyContract:
    """AC3: PendingDR/ResolveModal body typing mismatch must be absent."""

    def test_pending_dr_body_type_mismatch_absent(self, build_output: str) -> None:
        """AC3: PendingDR passed to ResolveModal must satisfy required body field."""
        fragment = "Property 'body' is missing in type 'PendingDR' but required in type 'PendingDRWithBody'"
        assert fragment not in build_output, (
            "Detected PendingDR/ResolveModal body mismatch in build output. "
            "Resolve by aligning DR types or supplying required body in the selected DR flow."
        )
