"""RED-phase build compatibility tests for #1364.

These tests intentionally fail against the audited broken state and become green
once #1365 resolves the PDS v4 type-contract mismatches.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import json

import pytest

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"
_SRC = _WEB / "src"


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


@pytest.fixture(scope="module")
def app_source_text() -> str:
    """Return merged non-test TS/TSX source text for suppression scanning."""
    fragments: list[str] = []
    for path in _SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "__tests__" in path.parts:
            continue
        fragments.append(path.read_text(encoding="utf-8"))
    return "\n".join(fragments)


@pytest.fixture(scope="module")
def tsconfig_data() -> dict[str, object]:
    """Load cockpit web tsconfig for anti-suppression assertions."""
    return json.loads((_WEB / "tsconfig.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def package_json_data() -> dict[str, object]:
    """Load cockpit web package.json for build-gate contract assertions."""
    return json.loads((_WEB / "package.json").read_text(encoding="utf-8"))


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


class TestAc2NoBroadTypeSuppressionGuards:
    """AC2: prove no broad type-suppression shortcuts are used."""

    @pytest.mark.parametrize(
        ("directive", "reason"),
        [
            ("@ts-ignore", "Suppresses TypeScript errors instead of fixing PDS v4 compatibility."),
            ("@ts-nocheck", "Disables type-checking for entire files and can hide audited failures."),
            ("@ts-expect-error", "Can mask audited contract failures instead of fixing component usage."),
        ],
    )
    def test_app_source_does_not_use_typescript_suppression_directives(
        self,
        directive: str,
        reason: str,
        app_source_text: str,
    ) -> None:
        """Reject TypeScript directive suppressions in non-test cockpit source."""
        assert directive not in app_source_text, f"Detected {directive} in app source. {reason}"

    def test_tsconfig_does_not_disable_typecheck(self, tsconfig_data: dict[str, object]) -> None:
        """Reject tsconfig noCheck-based bypasses for build compatibility."""
        compiler_options = tsconfig_data.get("compilerOptions", {})
        assert isinstance(compiler_options, dict)
        assert compiler_options.get("strict") is True, "tsconfig must keep strict mode enabled."
        assert compiler_options.get("noCheck") is not True, "tsconfig must not disable type-checking via noCheck."

    def test_package_json_build_script_keeps_tsc_build(
        self,
        package_json_data: dict[str, object],
    ) -> None:
        """Require the canonical build gate to keep TypeScript project build checks."""
        scripts = package_json_data.get("scripts", {})
        assert isinstance(scripts, dict)
        build_script = scripts.get("build")
        assert isinstance(build_script, str), "package.json scripts.build must be a string."
        assert "tsc -b" in build_script, "package.json scripts.build must include 'tsc -b'."
