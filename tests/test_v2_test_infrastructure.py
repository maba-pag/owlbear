"""Failing tests for task #35: Create v2 test infrastructure.

Tests the structural and configuration requirements for v2 pytest/ruff/coverage setup.
All tests are contract-level: they verify the configuration and file-system state
described in the AC, not any specific implementation approach.

AC coverage:
  AC1  — [tool.pytest.ini_options]: testpaths=[tests,packages], addopts=importlib
  AC2  — Root conftest.py: project_root fixture, marker registrations, no YAGNI
  AC3  — Per-package tests/__init__.py for all 5 packages (3 new)
  AC4  — Dev dependencies: pytest-asyncio>=0.25
  AC5  — [tool.ruff]: target-version=py312, select=ALL, ignores, src, per-file-ignores
  AC6  — [tool.ruff.format]: quote-style=double; [tool.ruff.lint.pydocstyle]: convention=google
  AC7  — [tool.coverage.run]: source_pkgs for all 5 installed packages
  AC8  — pytest discovers tests in both tests/ and packages/*/tests/
  AC9  — ruff check exits 0 (clean) across packages/ and tests/
  AC10 — At least one trivial passing test per package (5 total)
  AC11 — CI commands (test, lint, coverage) documented in README.md
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import ClassVar

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).parent.parent

_INSTALLED_PKG_NAMES = [
    "owlbear",
    "owlbear_knowledge",
    "owlbear_mcp_kanban",
    "owlbear_mcp_knowledge",
    "owlbear_mcp_project",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pyproject() -> dict:
    """Load and return the root pyproject.toml as a dict."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def _pytest_ini_options() -> dict:
    """Return [tool.pytest.ini_options] section."""
    return _pyproject().get("tool", {}).get("pytest", {}).get("ini_options", {})


def _dev_deps() -> list[str]:
    """Return the root [dependency-groups] dev list as strings."""
    raw = _pyproject().get("dependency-groups", {}).get("dev", [])
    return [str(d) for d in raw]


def _ruff() -> dict:
    """Return [tool.ruff] section."""
    return _pyproject().get("tool", {}).get("ruff", {})


def _ruff_lint() -> dict:
    """Return [tool.ruff.lint] section (nested under [tool.ruff])."""
    return _ruff().get("lint", {})


def _ruff_format() -> dict:
    """Return [tool.ruff.format] section."""
    return _ruff().get("format", {})


def _coverage_run() -> dict:
    """Return [tool.coverage.run] section."""
    return _pyproject().get("tool", {}).get("coverage", {}).get("run", {})


# ---------------------------------------------------------------------------
# AC1: [tool.pytest.ini_options]
# ---------------------------------------------------------------------------


class TestFromAC_PytestIniOptions:
    """AC1: testpaths must include 'packages'; addopts must include --import-mode=importlib."""

    def test_testpaths_includes_serve(self) -> None:
        """testpaths must list 'serve' alongside 'tests' (renamed from packages/ in five-tier restructure)."""
        opts = _pytest_ini_options()
        testpaths = opts.get("testpaths", [])
        assert "serve" in testpaths, f"'serve' missing from testpaths; got {testpaths!r}"

    def test_addopts_has_import_mode_importlib(self) -> None:
        """addopts must include --import-mode=importlib."""
        opts = _pytest_ini_options()
        addopts = opts.get("addopts", "")
        assert "--import-mode=importlib" in addopts, (
            f"--import-mode=importlib not found in addopts={addopts!r}"
        )


# ---------------------------------------------------------------------------
# AC2: Root conftest.py
# ---------------------------------------------------------------------------


class TestFromAC_RootConftest:
    """AC2: conftest.py at repo root with project_root fixture and marker registrations only."""

    def test_root_conftest_exists(self) -> None:
        """conftest.py must exist at repo root."""
        assert (ROOT / "conftest.py").exists(), "conftest.py not found at repo root"

    def test_conftest_has_project_root_fixture(self) -> None:
        """conftest.py must define a project_root fixture returning a Path."""
        path = ROOT / "conftest.py"
        assert path.exists(), "conftest.py not found"
        src = path.read_text(encoding="utf-8")
        assert "project_root" in src, "project_root fixture not defined in conftest.py"
        assert "Path" in src, "project_root fixture must return a Path"

    def test_conftest_registers_markers(self) -> None:
        """conftest.py must register pytest markers (api, slow)."""
        path = ROOT / "conftest.py"
        assert path.exists(), "conftest.py not found"
        src = path.read_text(encoding="utf-8")
        assert "api" in src, "'api' marker not registered in conftest.py"
        assert "slow" in src, "'slow' marker not registered in conftest.py"

    def test_conftest_no_yagni_fixtures(self) -> None:
        """conftest.py must not contain tmp_path_factory or MagicMock helpers (YAGNI)."""
        path = ROOT / "conftest.py"
        assert path.exists(), "conftest.py not found"
        src = path.read_text(encoding="utf-8")
        assert "tmp_path_factory" not in src, (
            "tmp_path_factory in conftest is YAGNI — not allowed at repo root"
        )
        assert "MagicMock" not in src, (
            "MagicMock in conftest is YAGNI — mock in individual test files"
        )


# ---------------------------------------------------------------------------
# AC3: Per-package tests/__init__.py for new packages
# ---------------------------------------------------------------------------


class TestFromAC_PerPackageTestDirs:
    """AC3: orchestrator, knowledge, mcp-kanban must have tests/ directories with __init__.py (under serve/)."""

    def test_orchestrator_tests_dir_exists(self) -> None:
        assert (ROOT / "serve" / "orchestrator" / "tests").is_dir(), (
            "serve/orchestrator/tests/ directory missing"
        )

    def test_orchestrator_tests_init_exists(self) -> None:
        assert (ROOT / "serve" / "orchestrator" / "tests" / "__init__.py").exists(), (
            "serve/orchestrator/tests/__init__.py missing"
        )

    def test_knowledge_tests_dir_exists(self) -> None:
        assert (ROOT / "serve" / "knowledge" / "tests").is_dir(), (
            "serve/knowledge/tests/ directory missing"
        )

    def test_knowledge_tests_init_exists(self) -> None:
        assert (ROOT / "serve" / "knowledge" / "tests" / "__init__.py").exists(), (
            "serve/knowledge/tests/__init__.py missing"
        )

    def test_mcp_kanban_tests_dir_exists(self) -> None:
        assert (ROOT / "serve" / "mcp-kanban" / "tests").is_dir(), (
            "serve/mcp-kanban/tests/ directory missing"
        )

    def test_mcp_kanban_tests_init_exists(self) -> None:
        assert (ROOT / "serve" / "mcp-kanban" / "tests" / "__init__.py").exists(), (
            "serve/mcp-kanban/tests/__init__.py missing"
        )


# ---------------------------------------------------------------------------
# AC4: Dev dependencies
# ---------------------------------------------------------------------------


class TestFromAC_DevDependencies:
    """AC4: Root pyproject.toml must include pytest-asyncio>=0.25 as a dev dependency."""

    def test_pytest_asyncio_in_dev_deps(self) -> None:
        """pytest-asyncio must be listed in [dependency-groups] dev."""
        deps = _dev_deps()
        match = next((d for d in deps if "pytest-asyncio" in d), None)
        assert match is not None, f"pytest-asyncio not found in dev deps; current deps: {deps}"

    def test_pytest_asyncio_version_at_least_0_25(self) -> None:
        """pytest-asyncio version constraint must be >=0.25."""
        deps = _dev_deps()
        dep_str = next((d for d in deps if "pytest-asyncio" in d), "")
        version_match = re.search(r">=([\d.]+)", dep_str)
        assert version_match, f"pytest-asyncio must have a '>=' version constraint; got {dep_str!r}"
        parts = [int(x) for x in version_match.group(1).split(".")]
        # Pad to at least (major, minor)
        while len(parts) < 2:  # noqa: PERF203
            parts.append(0)
        assert tuple(parts[:2]) >= (0, 25), (
            f"pytest-asyncio version must be >=0.25, got constraint in {dep_str!r}"
        )


# ---------------------------------------------------------------------------
# AC5: [tool.ruff] configuration
# ---------------------------------------------------------------------------


class TestFromAC_RuffConfig:
    """AC5: [tool.ruff] config: target-version=py312, select=ALL, ignores, src, per-file-ignores."""

    def test_ruff_section_exists(self) -> None:
        """[tool.ruff] section must be present in root pyproject.toml."""
        assert _ruff(), "[tool.ruff] section missing from root pyproject.toml"

    def test_ruff_target_version_py312(self) -> None:
        """target-version must be py312."""
        tv = _ruff().get("target-version")
        assert tv == "py312", f"[tool.ruff] target-version must be 'py312', got {tv!r}"

    def test_ruff_lint_select_all(self) -> None:
        """[tool.ruff.lint] select must include 'ALL'."""
        select = _ruff_lint().get("select", [])
        assert "ALL" in select, f"[tool.ruff.lint] select must include 'ALL'; got {select!r}"

    def test_ruff_lint_ignore_includes_required_rules(self) -> None:
        """ruff ignore must include v1-compatible rules: D1xx, COM812, ISC001, S101."""
        ignore = _ruff_lint().get("ignore", [])
        required_prefixes = ("D1", "COM812", "ISC001", "S101")
        for prefix in required_prefixes:
            assert any(r.startswith(prefix) for r in ignore), (
                f"Required ignore prefix '{prefix}' missing from ruff ignore={ignore!r}"
            )

    def test_ruff_src_references_serve(self) -> None:
        """[tool.ruff] src must reference serve/ for first-party import detection (renamed from packages/)."""
        src = _ruff().get("src", [])
        assert src, "[tool.ruff] src not set; needed for first-party import detection"
        src_str = " ".join(str(s) for s in src)
        assert "serve" in src_str, f"[tool.ruff] src must reference serve/; got src={src!r}"

    def test_ruff_per_file_ignores_covers_tests(self) -> None:
        """per-file-ignores must include a pattern for tests/**/*.py."""
        pfi = _ruff_lint().get("per-file-ignores", {})
        assert pfi, "[tool.ruff.lint] per-file-ignores not configured"
        has_tests_pattern = any("tests" in k for k in pfi)
        assert has_tests_pattern, (
            f"per-file-ignores must have a 'tests/**' pattern; keys found: {list(pfi)!r}"
        )

    def test_ruff_per_file_ignores_covers_serve_tests(self) -> None:
        """per-file-ignores must include a pattern matching serve/*/tests/ (renamed from packages/)."""
        pfi = _ruff_lint().get("per-file-ignores", {})
        assert pfi, "[tool.ruff.lint] per-file-ignores not configured"
        # Accept any key mentioning both "serve" and "tests"
        has_serve_tests = any("serve" in k and "tests" in k for k in pfi)
        assert has_serve_tests, (
            f"per-file-ignores must cover serve/*/tests/**; keys found: {list(pfi)!r}"
        )


# ---------------------------------------------------------------------------
# AC6: [tool.ruff.format] and pydocstyle convention
# ---------------------------------------------------------------------------


class TestFromAC_RuffFormatConfig:
    """AC6: quote-style=double in [tool.ruff.format]; convention=google in pydocstyle."""

    def test_ruff_format_section_exists(self) -> None:
        """[tool.ruff.format] section must exist."""
        assert _ruff_format(), "[tool.ruff.format] section missing from root pyproject.toml"

    def test_ruff_format_quote_style_double(self) -> None:
        """[tool.ruff.format] quote-style must be 'double'."""
        qs = _ruff_format().get("quote-style")
        assert qs == "double", f"[tool.ruff.format] quote-style must be 'double', got {qs!r}"

    def test_ruff_pydocstyle_convention_google(self) -> None:
        """[tool.ruff.lint.pydocstyle] convention must be 'google'."""
        convention = _ruff_lint().get("pydocstyle", {}).get("convention")
        assert convention == "google", (
            f"[tool.ruff.lint.pydocstyle] convention must be 'google', got {convention!r}"
        )


# ---------------------------------------------------------------------------
# AC7: [tool.coverage.run] configuration
# ---------------------------------------------------------------------------


class TestFromAC_CoverageConfig:
    """AC7: [tool.coverage.run] source_pkgs must list all 5 installed package names."""

    def test_coverage_run_section_exists(self) -> None:
        """[tool.coverage.run] section must exist in root pyproject.toml."""
        assert _coverage_run(), "[tool.coverage.run] section missing from root pyproject.toml"

    def test_coverage_run_source_pkgs_all_five(self) -> None:
        """source_pkgs must list all 5 installed package names."""
        source_pkgs = _coverage_run().get("source_pkgs", [])
        for pkg in _INSTALLED_PKG_NAMES:
            assert pkg in source_pkgs, (
                f"'{pkg}' missing from [tool.coverage.run] source_pkgs={source_pkgs!r}"
            )


# ---------------------------------------------------------------------------
# AC8: pytest discovers tests in tests/ and packages/*/tests/
# ---------------------------------------------------------------------------


class TestFromAC_PytestDiscovery:
    """AC8: pytest must collect from both tests/ and serve/*/tests/ with exit 0."""

    @pytest.fixture(scope="class")
    def _collection_result(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "pytest", "tests/", "serve/", "--co", "-q", "--tb=short",
             "-o", "addopts=--import-mode=importlib -m 'not e2e'"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_pytest_collection_exits_zero(self, _collection_result: subprocess.CompletedProcess[str]) -> None:
        """pytest --co across tests/ and serve/ must exit 0."""
        result = _collection_result
        assert result.returncode == 0, (
            f"pytest collection failed (exit {result.returncode}):\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_pytest_collection_includes_all_five_packages(self, _collection_result: subprocess.CompletedProcess[str]) -> None:
        """pytest collection output must reference tests from all 5 serve/*/tests/ dirs."""
        result = _collection_result
        combined = (result.stdout + result.stderr).replace("\\", "/")
        for pkg in ["orchestrator", "knowledge", "mcp-kanban", "mcp-knowledge", "mcp-project"]:
            assert f"serve/{pkg}" in combined, (
                f"pytest did not collect any tests from serve/{pkg}/tests/.\n"
                f"Collection output:\n{result.stdout}"
            )


# ---------------------------------------------------------------------------
# AC9: ruff check exits 0 across packages/ and tests/
# ---------------------------------------------------------------------------


class TestFromAC_RuffLinting:
    """AC9: uv run ruff check serve/ tests/ must exit 0."""

    def test_ruff_check_clean(self) -> None:
        """ruff check must exit 0 when fully configured (select=ALL + ignores in place)."""
        # Guard: ruff lint must be configured with select=ALL before this integration test runs.
        # This assertion fails (CORRECTLY) until the builder adds the [tool.ruff.lint] config.
        assert "ALL" in _ruff_lint().get("select", []), (
            "[tool.ruff.lint] select=ALL must be configured before ruff clean-check can pass"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "serve/", "tests/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"ruff check failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# AC10: At least one trivial passing test per package
# ---------------------------------------------------------------------------


class TestFromAC_TrivialPassingTests:
    """AC10: Each of the 5 packages must have at least one trivial passing test."""

    _PACKAGES: ClassVar[list[str]] = ["orchestrator", "knowledge", "mcp-kanban", "mcp-project"]

    @pytest.fixture(scope="class")
    def _run_result(self) -> subprocess.CompletedProcess[str]:
        test_dirs = [f"serve/{pkg}/tests/" for pkg in self._PACKAGES]
        return subprocess.run(
            ["uv", "run", "pytest", *test_dirs, "-v", "--tb=no", "--no-header",
             "-o", "addopts=--import-mode=importlib"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @pytest.mark.parametrize("pkg_dir", _PACKAGES)
    def test_package_has_passing_test(self, pkg_dir: str, _run_result: subprocess.CompletedProcess[str]) -> None:
        combined = (_run_result.stdout + _run_result.stderr).replace("\\", "/")
        msg = (
            f"No passing tests found for serve/{pkg_dir}/tests/.\n"
            f"stdout:\n{_run_result.stdout}\nstderr:\n{_run_result.stderr}"
        )
        assert f"serve/{pkg_dir}" in combined, msg
        assert "PASSED" in combined, msg


# ---------------------------------------------------------------------------
# AC11: CI commands documented in README.md
# ---------------------------------------------------------------------------


class TestFromAC_CIDocumentation:
    """AC11: README.md must document test, lint, and coverage commands."""

    def _readme(self) -> str:
        return (ROOT / "README.md").read_text(encoding="utf-8")

    def test_readme_pytest_command_covers_serve(self) -> None:
        """README must document a pytest command that covers serve/ (renamed from packages/)."""
        readme = self._readme()
        pytest_lines = [
            line for line in readme.splitlines() if "pytest" in line and "uv run" in line
        ]
        has_serve = any("serve" in line for line in pytest_lines)
        assert has_serve, (
            "README.md must document 'uv run pytest ... serve' command.\n"
            f"Existing pytest lines: {pytest_lines}"
        )

    def test_readme_has_coverage_command(self) -> None:
        """README must document a coverage command."""
        readme = self._readme()
        has_cov = "--cov" in readme or "coverage run" in readme or "uv run coverage" in readme
        assert has_cov, (
            "README.md must document a coverage command (e.g., uv run pytest --cov or coverage run)"
        )

    def test_readme_ruff_check_covers_serve(self) -> None:
        """README must document a ruff check command covering serve/ (renamed from packages/)."""
        readme = self._readme()
        ruff_lines = [line for line in readme.splitlines() if "ruff check" in line]
        assert ruff_lines, "README.md must document a 'ruff check' command"
        # The command must cover serve/ (not just src/)
        has_serve = any("serve" in line for line in ruff_lines)
        assert has_serve, f"ruff check command must cover serve/; found: {ruff_lines}"
